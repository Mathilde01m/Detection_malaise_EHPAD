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

<<<<<<< HEAD
# Délais
ACK_SUPPRESSION_SECONDS = 180
VITALS_STEP_SECONDS = 40
ALERT_COOLDOWN_SECONDS = 45

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


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["true", "1", "yes", "oui"]
    return False


def classify_fall_from_context(event_type, fall_type, fall_related_to_malaise, hr, spo2):
    vitals_state = classify_vitals(hr, spo2)

    event_type = (event_type or "").lower()
    fall_type = (fall_type or "").lower()

    if fall_related_to_malaise:
        if fall_type == "malaise_cardiaque" or "cardiac" in event_type:
            return "cardiac_malaise"
        if fall_type == "syncope_hypotension" or "syncope" in event_type:
            return "syncope_hypotension"
        return "malaise"

    if fall_type == "mechanical" or event_type == "mechanical_fall":
        return "mechanical"

    if fall_type == "balance_disorder" or "parkinson" in event_type:
        return "parkinson_balance"

    if "fall" in event_type:
        if vitals_state == "stable":
            return "mechanical"
        return "malaise"

    return "none"


def build_fall_alert_text(fall_context, fall_location, fall_cause):
    location_text = f" en {fall_location}" if fall_location else ""
    cause_text = f" ({fall_cause})" if fall_cause else ""

    if fall_context == "mechanical":
        return f"RISQUE MAXIMAL - Chute mécanique détectée{location_text}{cause_text}"

    if fall_context == "parkinson_balance":
        return f"RISQUE MAXIMAL - Chute liée à un trouble de l'équilibre / Parkinson détectée{location_text}{cause_text}"

    if fall_context == "cardiac_malaise":
        return f"DANGER VITAL - Chute après malaise cardiaque suspecté{location_text}{cause_text}"

    if fall_context == "syncope_hypotension":
        return f"DANGER VITAL - Chute après syncope ou hypotension suspectée{location_text}{cause_text}"

    if fall_context == "malaise":
        return f"DANGER VITAL - Chute avec suspicion de malaise{location_text}{cause_text}"

    return f"RISQUE MAXIMAL - Chute détectée{location_text}{cause_text}"


def generate_medical_report(
    res_id,
    alert_text,
    hr,
    spo2,
    event_type="normal",
    fall_type=None,
    fall_location=None,
    fall_cause=None,
    fall_related_to_malaise=False
):
    fall_context = classify_fall_from_context(
        event_type,
        fall_type,
        fall_related_to_malaise,
        hr,
        spo2
    )

    if fall_context == "mechanical":
        cause_instruction = (
            "Il s'agit d'une chute probablement mécanique. "
            "Les constantes ne suggèrent pas un malaise immédiat. "
            "Priorise sécurisation, recherche de traumatisme, douleur, plaie ou fracture."
        )

    elif fall_context == "parkinson_balance":
        cause_instruction = (
            "Il s'agit d'une chute probablement liée à un trouble de l'équilibre ou à Parkinson. "
            "Priorise évaluation traumatique, aide au relevage sécurisée, surveillance neurologique "
            "et prévention d'une récidive."
        )

    elif fall_context == "cardiac_malaise":
        cause_instruction = (
            "Il s'agit d'une chute après malaise cardiaque suspecté. "
            "Considère la situation comme une urgence vitale : constantes, ECG si disponible, "
            "surveillance rapprochée et appel médical urgent."
        )

    elif fall_context == "syncope_hypotension":
        cause_instruction = (
            "Il s'agit d'une chute après syncope ou hypotension suspectée. "
            "Priorise mise en sécurité, contrôle tensionnel, surveillance conscience, hydratation selon protocole "
            "et avis médical rapide."
        )

    elif fall_context == "malaise":
        cause_instruction = (
            "Il s'agit d'une chute possiblement liée à un malaise. "
            "Priorise évaluation des constantes, conscience, douleur, traumatisme et appel médical rapide."
        )

    else:
        cause_instruction = (
            "Analyse les constantes vitales et donne une conduite à tenir courte."
        )

    prompt = f"""
Agis comme un médecin urgentiste en EHPAD.

Résident : {res_id}
Alerte : {alert_text}

Constantes :
- Fréquence cardiaque : {hr} bpm
- SpO2 : {spo2} %

Contexte capteurs :
- event_type : {event_type}
- fall_type : {fall_type}
- fall_location : {fall_location}
- fall_cause : {fall_cause}
- fall_related_to_malaise : {fall_related_to_malaise}

Instruction médicale :
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

    hr = float(current_state.get("hr", 70))
    spo2 = float(current_state.get("spo2", 98))

    event_type = current_state.get("event_type", "normal")
    env_alert_level = int(current_state.get("alert_level", 0))

    fall_detected = normalize_bool(current_state.get("fall_detected", False))
    fall_type = current_state.get("fall_type")
    fall_location = current_state.get("fall_location")
    fall_cause = current_state.get("fall_cause")
    fall_related_to_malaise = normalize_bool(
        current_state.get("fall_related_to_malaise", False)
    )

    now = time.time()

    if r.exists(f"ack_suppressed:{res_id}"):
        return 0, "", hr, spo2

    fall_context = classify_fall_from_context(
        event_type,
        fall_type,
        fall_related_to_malaise,
        hr,
        spo2
    )

    if env_alert_level == 4 or fall_detected or "fall" in event_type.lower():
        return (
            5,
            build_fall_alert_text(fall_context, fall_location, fall_cause),
            hr,
            spo2
        )

    if env_alert_level == 2 or "wandering" in event_type:
        return 2, "ATTENTION - Comportement anormal détecté", hr, spo2

    if env_alert_level == 1 or "prolonged" in event_type:
        return 1, "INFORMATION - Immobilité prolongée détectée", hr, spo2

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


def save_environment_context(res_id, data):
    fields = [
        "event_type",
        "alert_level",
        "fall_detected",
        "fall_type",
        "fall_location",
        "fall_cause",
        "fall_related_to_malaise",
    ]

    for field in fields:
        if field in data and data[field] is not None:
            r.hset(f"state:{res_id}", field, data[field])

=======
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
>>>>>>> front2

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
<<<<<<< HEAD
        topic = msg.topic
        data = json.loads(msg.payload)

        if topic.startswith("ehpad/alerts/ack"):
            res_id = data.get("res_id")

            if res_id:
                r.hdel("active_alerts", res_id)
                r.delete(f"last_alert_time:{res_id}")
                r.delete(f"vitals_abnormal_since:{res_id}")

                reset_fields = {
                    "event_type": "normal",
                    "alert_level": 0,
                    "fall_detected": False,
                    "fall_type": "",
                    "fall_location": "",
                    "fall_cause": "",
                    "fall_related_to_malaise": False,
                }

                for key, value in reset_fields.items():
                    r.hset(f"state:{res_id}", key, value)

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
            save_environment_context(res_id, data)

        lvl, msg_alert, hr, spo2 = evaluate_resident_state(res_id)

        if lvl <= 0:
            return

        now = time.time()
        last_alert = r.hget(f"last_alert_time:{res_id}", "time")

        if last_alert and now - float(last_alert) < ALERT_COOLDOWN_SECONDS:
            return

        current_state = r.hgetall(f"state:{res_id}")

        alert_payload = {
            "res_id": res_id,
            "level": lvl,
            "text": msg_alert,
            "timestamp": data.get("timestamp", ""),
            "event_type": current_state.get("event_type", "normal"),
            "fall_type": current_state.get("fall_type"),
            "fall_location": current_state.get("fall_location"),
            "fall_cause": current_state.get("fall_cause"),
            "fall_related_to_malaise": normalize_bool(
                current_state.get("fall_related_to_malaise", False)
            ),
        }

        if lvl >= 4:
            print(f"[*] Demande de rapport LLM Mistral pour {res_id}...")
            alert_payload["llm_report"] = generate_medical_report(
                res_id,
                msg_alert,
                hr,
                spo2,
                event_type=alert_payload["event_type"],
                fall_type=alert_payload["fall_type"],
                fall_location=alert_payload["fall_location"],
                fall_cause=alert_payload["fall_cause"],
                fall_related_to_malaise=alert_payload["fall_related_to_malaise"],
            )

        client.publish("ehpad/alerts", json.dumps(alert_payload))
        r.hset(f"last_alert_time:{res_id}", "time", now)

        if lvl in [2, 3, 4, 5]:
            r.hset("active_alerts", res_id, json.dumps({
                "level": lvl,
                "time": now,
                "text": msg_alert,
                "timestamp": alert_payload["timestamp"],
                "event_type": alert_payload["event_type"],
                "fall_type": alert_payload["fall_type"],
                "fall_location": alert_payload["fall_location"],
                "fall_cause": alert_payload["fall_cause"],
                "fall_related_to_malaise": alert_payload["fall_related_to_malaise"],
            }))

        print(f"[NIVEAU {lvl}] Alerte publiée pour {res_id} : {msg_alert}")

    except Exception as e:
        print(f"Erreur processing: {e}")


client = mqtt_client.Client(CallbackAPIVersion.VERSION1, "Backend_IA")
client.on_message = on_message

connected = False
while not connected:
    try:
        print("Tentative de connexion au broker MQTT...")
        client.connect(MQTT_BROKER, 1883)
        connected = True
=======
        data = json.loads(msg.payload.decode())
>>>>>>> front2
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

<<<<<<< HEAD
print("[*] IA Processor prêt : types de chute, gradation vitaux, ACK 3 min activés.")
client.loop_forever()
=======
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
>>>>>>> front2
