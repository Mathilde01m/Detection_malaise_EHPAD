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

# Configurations
REDIS_HOST = "redis-cache"
MQTT_BROKER = "mqtt-broker"
OLLAMA_URL = "http://ollama:11434/api/generate"

# Délais
ACK_SUPPRESSION_SECONDS = 180      # 3 minutes stable après action médecin
VITALS_STEP_SECONDS = 40           # gradation toutes les 30-45 secondes
ALERT_COOLDOWN_SECONDS = 45        # évite le spam d'alertes

# Connexion Redis
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)


def classify_vitals(hr, spo2):
    if hr < 30 or hr > 160 or spo2 < 85:
        return "critical"
    if hr < 45 or hr > 135 or spo2 < 90:
        return "high"
    if hr < 55 or hr > 120 or spo2 < 93:
        return "moderate"
    return "stable"


def classify_fall_cause(hr, spo2):
    if classify_vitals(hr, spo2) == "stable":
        return "mechanical"
    return "malaise"


def generate_medical_report(res_id, alert_text, hr, spo2):
    fall_cause = classify_fall_cause(hr, spo2)

    if "chute" in alert_text.lower() or "fall" in alert_text.lower():
        if fall_cause == "mechanical":
            cause_instruction = (
                "Les constantes vitales sont stables. "
                "Indique clairement que la chute semble non liée à un malaise "
                "et probablement mécanique."
            )
        else:
            cause_instruction = (
                "Les constantes vitales sont anormales. "
                "Indique clairement qu'une chute liée à un malaise est suspectée."
            )
    else:
        cause_instruction = (
            "Analyse les constantes vitales et donne une conduite à tenir courte."
        )

    prompt = f"""
    Agis comme un médecin urgentiste.
    Résident : {res_id}
    Alerte : {alert_text}
    Fréquence cardiaque : {hr} bpm
    SpO2 : {spo2}%

    {cause_instruction}

    Rédige une transmission infirmière ultra-courte en 2 phrases maximum.
    Sois direct, clinique et exploitable.
    """

    try:
        print(f"[*] 🧠 Mistral réfléchit pour {res_id}...")
        response = requests.post(
            OLLAMA_URL,
            json={"model": "mistral", "prompt": prompt, "stream": False},
            timeout=60
        )

        data = response.json()
        return data.get("response", "Erreur : l'IA n'a pas renvoyé de texte.")

    except requests.exceptions.Timeout:
        return "L'IA Mistral met trop de temps à générer le rapport."
    except Exception as e:
        return f"Erreur de connexion à l'IA : {str(e)}"


def evaluate_resident_state(res_id):
    current_state = r.hgetall(f"state:{res_id}")
    history_raw = r.lrange(f"history:{res_id}", 0, -1)
    history = [json.loads(h) for h in history_raw][::-1]

    hr = float(current_state.get("hr", 70))
    spo2 = float(current_state.get("spo2", 98))
    event_type = current_state.get("event_type", "normal")
    env_alert_level = int(current_state.get("alert_level", 0))

    now = time.time()

    # Après action médecin : le résident reste stable 3 minutes
    if r.exists(f"ack_suppressed:{res_id}"):
        return 0, "", hr, spo2

    # Chute détectée par capteur : passage direct en risque maximal
    if env_alert_level == 4 or "fall" in event_type:
        cause = classify_fall_cause(hr, spo2)

        if cause == "mechanical":
            return (
                5,
                "RISQUE MAXIMAL - Chute détectée non liée à un malaise, constantes vitales stables",
                hr,
                spo2
            )

        return (
            5,
            "RISQUE MAXIMAL - Chute détectée avec suspicion de malaise, constantes vitales anormales",
            hr,
            spo2
        )

    # Comportements environnementaux non vitaux
    if env_alert_level == 2 or "wandering" in event_type:
        return 2, "ATTENTION - Comportement anormal détecté", hr, spo2

    if env_alert_level == 1 or "prolonged" in event_type:
        return 1, "INFORMATION - Immobilité prolongée détectée", hr, spo2

    # Gradation progressive des constantes vitales
    vitals_state = classify_vitals(hr, spo2)

    if vitals_state == "stable":
        r.delete(f"vitals_abnormal_since:{res_id}")
        return 0, "", hr, spo2

    abnormal_since = r.get(f"vitals_abnormal_since:{res_id}")

    if not abnormal_since:
        r.set(f"vitals_abnormal_since:{res_id}", now)
        return 2, "ATTENTION - Début d'anomalie des constantes vitales", hr, spo2

    elapsed = now - float(abnormal_since)

    if elapsed < VITALS_STEP_SECONDS:
        return 2, "ATTENTION - Constantes vitales à surveiller", hr, spo2

    if elapsed < VITALS_STEP_SECONDS * 2:
        return 3, "ALERTE - Dégradation persistante des constantes vitales", hr, spo2

    if elapsed < VITALS_STEP_SECONDS * 3:
        return 4, "URGENCE - Constantes vitales fortement dégradées", hr, spo2

    return 5, "DANGER VITAL - Constantes critiques persistantes", hr, spo2


def escalation_monitor():
    """
    L'escalade principale est maintenant gérée par evaluate_resident_state()
    pour les constantes vitales. Ce monitor sert surtout de sécurité.
    """
    while True:
        try:
            active_alerts = r.hgetall("active_alerts")

            for res_id, alert_data_str in active_alerts.items():
                if r.exists(f"ack_suppressed:{res_id}"):
                    r.hdel("active_alerts", res_id)
                    continue

        except Exception as e:
            print(f"Erreur escalation_monitor: {e}")

        time.sleep(5)


def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        data = json.loads(msg.payload)

        # Acquittement médecin
        if topic.startswith("ehpad/alerts/ack"):
            res_id = data.get("res_id")

            if res_id:
                r.hdel("active_alerts", res_id)
                r.delete(f"last_alert_time:{res_id}")
                r.delete(f"vitals_abnormal_since:{res_id}")

                r.hset(f"state:{res_id}", "event_type", "normal")
                r.hset(f"state:{res_id}", "alert_level", 0)

                r.setex(
                    f"ack_suppressed:{res_id}",
                    ACK_SUPPRESSION_SECONDS,
                    str(time.time())
                )

                print(
                    f"[ACK] Action médecin réalisée pour {res_id}. "
                    f"Retour stable pendant {ACK_SUPPRESSION_SECONDS}s."
                )

            return

        parts = topic.split("/")
        if len(parts) < 4:
            return

        res_id = parts[2]
        msg_type = parts[3]

        if msg_type == "vitals":
            r.hset(f"state:{res_id}", "hr", data.get("heart_rate", 0))
            r.hset(f"state:{res_id}", "spo2", data.get("spo2", 0))
            r.lpush(f"history:{res_id}", json.dumps(data))
            r.ltrim(f"history:{res_id}", 0, 9)

        elif msg_type == "environment":
            r.hset(f"state:{res_id}", "event_type", data.get("event_type", "normal"))
            r.hset(f"state:{res_id}", "alert_level", data.get("alert_level", 0))

        lvl, msg_alert, hr, spo2 = evaluate_resident_state(res_id)

        if lvl <= 0:
            return

        now = time.time()
        last_alert = r.hget(f"last_alert_time:{res_id}", "time")

        if last_alert and now - float(last_alert) < ALERT_COOLDOWN_SECONDS:
            return

        alert_payload = {
            "res_id": res_id,
            "level": lvl,
            "text": msg_alert,
            "timestamp": data.get("timestamp", "")
        }

        if lvl >= 4:
            print(f"[*] Demande de rapport LLM Mistral pour {res_id}...")
            alert_payload["llm_report"] = generate_medical_report(
                res_id,
                msg_alert,
                hr,
                spo2
            )

        client.publish("ehpad/alerts", json.dumps(alert_payload))
        r.hset(f"last_alert_time:{res_id}", "time", now)

        if lvl in [2, 3, 4, 5]:
            r.hset("active_alerts", res_id, json.dumps({
                "level": lvl,
                "time": now,
                "text": msg_alert,
                "timestamp": alert_payload["timestamp"]
            }))

        print(f"[NIVEAU {lvl}] Alerte publiée pour {res_id} : {msg_alert}")

    except Exception as e:
        print(f"Erreur processing: {e}")


# Initialisation MQTT
client = mqtt_client.Client(CallbackAPIVersion.VERSION1, "Backend_IA")
client.on_message = on_message

connected = False
while not connected:
    try:
        print("Tentative de connexion au broker MQTT...")
        client.connect(MQTT_BROKER, 1883)
        connected = True
    except Exception:
        time.sleep(3)

client.subscribe("ehpad/residents/#")
client.subscribe("ehpad/alerts/ack")

escalation_thread = threading.Thread(target=escalation_monitor, daemon=True)
escalation_thread.start()

print("[*] IA Processor prêt : chute mécanique, gradation vitaux, ACK 3 min activés.")
client.loop_forever()