import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import json
import redis
import time
import requests
import threading
from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion
from models.ai_engine import ai

# ── Configuration ──────────────────────────────────────────────────────────────
REDIS_HOST  = "redis-cache"
MQTT_BROKER = "mqtt-broker"
MQTT_PORT   = 1883
OLLAMA_URL  = "http://ollama:11434/api/generate"

# ── Redis ──────────────────────────────────────────────────────────────────────
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

# ── Seuils de détection ────────────────────────────────────────────────────────
SEUILS = {
    "heart_rate": {"min": 40, "max": 120},
    "spo2":       {"min": 90, "max": 100},
    "temperature":{"min": 35.0, "max": 39.0},
}

# Compteurs d'alertes par résident pour l'escalade
alert_levels = {}

# ── Appel LLM Mistral / Ollama ─────────────────────────────────────────────────
def call_llm(resident_id, vitals, alert_text):
    prompt = (
        f"Tu es un assistant médical dans un EHPAD. "
        f"Le résident {resident_id} présente les constantes suivantes : "
        f"FC={vitals.get('heart_rate')} bpm, SpO2={vitals.get('spo2')}%, "
        f"Temp={vitals.get('temperature')}°C. "
        f"Alerte détectée : {alert_text}. "
        f"Donne en 2-3 phrases un résumé clinique concis et une recommandation d'action immédiate."
    )
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"[LLM] Erreur Ollama : {e}")
    return ""

# ── Calcul du niveau d'alerte ──────────────────────────────────────────────────
def compute_alert_level(resident_id, vitals):
    anomalies = []

    hr  = vitals.get("heart_rate")
    spo = vitals.get("spo2")
    tmp = vitals.get("temperature")

    if hr is not None:
        if hr < 40 or hr > 130:
            anomalies.append(f"FC critique ({hr} bpm)")
        elif hr < 50 or hr > 120:
            anomalies.append(f"FC anormale ({hr} bpm)")

    if spo is not None:
        if spo < 85:
            anomalies.append(f"SpO2 très basse ({spo}%)")
        elif spo < 90:
            anomalies.append(f"SpO2 basse ({spo}%)")

    if tmp is not None:
        if tmp < 35.0 or tmp > 40.0:
            anomalies.append(f"Température critique ({tmp}°C)")
        elif tmp < 36.0 or tmp > 38.5:
            anomalies.append(f"Température anormale ({tmp}°C)")

    if not anomalies:
        # Détection comportementale légère via IA
        score = ai.predict_vitals_anomaly([[
            hr or 70, spo or 98, tmp or 36.5
        ]])
        if score > 0.7:
            anomalies.append("Comportement anormal")

    n = len(anomalies)
    if n == 0:
        return 0, ""
    elif n == 1:
        level = 2
        text  = f"ATTENTION - {anomalies[0]}"
    elif n == 2:
        level = 3
        text  = f"ALERTE - {' + '.join(anomalies)}"
    else:
        level = 5
        text  = f"DANGER VITAL - Constantes critiques"

    # Escalade si alertes répétées
    prev = alert_levels.get(resident_id, 0)
    if level == prev and level < 5:
        level = min(level + 1, 5)
        print(f"[ESCALADE] L'alerte de {resident_id} passe au niveau {level} !")
    alert_levels[resident_id] = level

    return level, text

# ── Traitement d'un message MQTT vitals ───────────────────────────────────────
def process_vitals(resident_id, vitals):
    # Sauvegarde dans Redis
    key = f"vitals:{resident_id}"
    r.hset(key, mapping={k: str(v) for k, v in vitals.items()})
    r.expire(key, 300)

    level, text = compute_alert_level(resident_id, vitals)
    if level == 0:
        alert_levels.pop(resident_id, None)
        return

    alert_payload = {
        "res_id":  resident_id,
        "level":   level,
        "text":    text,
        "vitals":  vitals,
    }

    # Rapport LLM pour niveau ≥ 4
    if level >= 4:
        print(f"[*] Demande de rapport LLM Mistral pour {resident_id}...")
        report = call_llm(resident_id, vitals, text)
        if report:
            alert_payload["llm_report"] = report

    print(f"[NIVEAU {level}] Alerte publiée pour {resident_id} : {text}")
    mqtt.publish("ehpad/alerts", json.dumps(alert_payload))

# ── Callbacks MQTT ────────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Connecté au broker (code={reason_code})")
    client.subscribe("ehpad/residents/+/vitals")
    client.subscribe("ehpad/alerts/ack")
    print("[MQTT] Abonné aux topics vitals et acks")

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        return

    if "/vitals" in topic:
        parts = topic.split("/")
        if len(parts) >= 3:
            resident_id = parts[2]
            threading.Thread(
                target=process_vitals,
                args=(resident_id, data),
                daemon=True
            ).start()

    elif topic == "ehpad/alerts/ack":
        res_id = data.get("res_id")
        if res_id:
            alert_levels.pop(res_id, None)
            print(f"[ACK] Alerte acquittée pour {res_id}")

# ── Démarrage ─────────────────────────────────────────────────────────────────
mqtt = mqtt_client.Client(
    callback_api_version=CallbackAPIVersion.VERSION2,
    client_id="ehpad_processor"
)
mqtt.on_connect = on_connect
mqtt.on_message = on_message

print("[*] Connexion au broker MQTT...")
while True:
    try:
        mqtt.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        break
    except Exception as e:
        print(f"[!] MQTT non disponible, retry dans 5s : {e}")
        time.sleep(5)

print("[*] Processor IA démarré — en attente de données...")
mqtt.loop_forever()
