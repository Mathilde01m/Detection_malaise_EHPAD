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

# Connexion à Redis
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

def generate_medical_report(res_id, alert_text, hr, spo2):
    # Nouveau prompt beaucoup plus précis pour orienter l'IA sur la cause de la chute
    prompt = f"""
    Agis comme un médecin urgentiste. Le résident {res_id} a déclenché une alerte : '{alert_text}'.
    Ses constantes actuelles sont : Fréquence Cardiaque {hr} bpm, SpO2 {spo2}%.
    Si l'alerte est une chute, analyse si les constantes vitales expliquent la chute (malaise vagal, hypoxie) ou si c'est probablement une chute mécanique (glissade).
    Rédige une transmission infirmière ultra-courte (2 phrases maximum). Sois direct et clinique.
    """
    
    try:
        print(f"[*] 🧠 Mistral réfléchit pour {res_id} (cela peut prendre jusqu'à 60s)...")
        
        # ⚠️ LE CORRECTIF EST ICI : timeout=60 au lieu de 15
        response = requests.post(
            OLLAMA_URL, 
            json={"model": "mistral", "prompt": prompt, "stream": False}, 
            timeout=60 
        )
        
        data = response.json()
        if 'response' in data:
            return data['response']
        else:
            return "Erreur : L'IA n'a pas renvoyé de texte."
            
    except requests.exceptions.Timeout:
        return "L'IA Mistral met trop de temps à générer le rapport (Timeout). Patientez."
    except Exception as e:
        return f"Erreur de connexion à l'IA : {str(e)}"

def evaluate_resident_state(res_id):
    current_state = r.hgetall(f"state:{res_id}")
    history_raw = r.lrange(f"history:{res_id}", 0, -1)
    history = [json.loads(h) for h in history_raw][::-1]
    
    hr = float(current_state.get('hr', 70))
    spo2 = float(current_state.get('spo2', 98))
    event_type = current_state.get('event_type', 'normal')
    env_alert_level = int(current_state.get('alert_level', 0))

    if hr < 30 or hr > 160 or spo2 < 85:
        return 5, "DANGER VITAL - Constantes critiques", hr, spo2
    if env_alert_level == 4 or "fall" in event_type:
        return 4, "URGENCE - Chute détectée", hr, spo2
    if len(history) == 10 and ai.predict_vitals_risk(history) == 1:
        return 3, "ALERTE IA - Risque de malaise imminent", hr, spo2
    if spo2 < 93:
        return 3, f"ALERTE - SpO2 basse ({spo2}%)", hr, spo2
    if env_alert_level == 2 or "wandering" in event_type:
        return 2, "ATTENTION - Comportement anormal", hr, spo2
    if env_alert_level == 1 or "prolonged" in event_type:
        return 1, "INFORMATION - Immobilité prolongée détectée", hr, spo2

    return 0, "", hr, spo2

def escalation_monitor():
    TIMEOUTS = {2: 10, 3: 5, 4: 3}
    while True:
        try:
            active_alerts = r.hgetall("active_alerts")
            now = time.time()
            for res_id, alert_data_str in active_alerts.items():
                alert_data = json.loads(alert_data_str)
                lvl = alert_data["level"]
                start_time = alert_data["time"]
                if lvl >= 5 or lvl not in TIMEOUTS:
                    continue
                if now - start_time >= TIMEOUTS[lvl]:
                    new_lvl = lvl + 1
                    msg_alert = f"ESCALADE AUTO (Niv {lvl} -> {new_lvl}) : {alert_data['text']}"
                    print(f"[ESCALADE] L'alerte de {res_id} passe au niveau {new_lvl} !")
                    alert_data["level"] = new_lvl
                    alert_data["time"] = now
                    alert_data["text"] = msg_alert
                    r.hset("active_alerts", res_id, json.dumps(alert_data))
                    alert_payload = {
                        "res_id": res_id,
                        "level": new_lvl,
                        "text": msg_alert,
                        "timestamp": alert_data["timestamp"]
                    }
                    client.publish("ehpad/alerts", json.dumps(alert_payload))
        except Exception as e:
            pass
        time.sleep(1)

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        data = json.loads(msg.payload)

        if topic.startswith("ehpad/alerts/ack"):
            res_id = data.get("res_id")
            if res_id:
                r.hdel("active_alerts", res_id)
                print(f"[ACK] Alerte acquittée pour {res_id}. Chronomètre stoppé.")
            return

        parts = topic.split('/')
        if len(parts) < 4:
            return

        res_id = parts[2]
        msg_type = parts[3]

        if msg_type == "vitals":
            r.hset(f"state:{res_id}", "hr", data.get('heart_rate', 0))
            r.hset(f"state:{res_id}", "spo2", data.get('spo2', 0))
            r.lpush(f"history:{res_id}", json.dumps(data))
            r.ltrim(f"history:{res_id}", 0, 9)
        elif msg_type == "environment":
            r.hset(f"state:{res_id}", "event_type", data.get('event_type', 'normal'))
            r.hset(f"state:{res_id}", "alert_level", data.get('alert_level', 0))

        lvl, msg_alert, hr, spo2 = evaluate_resident_state(res_id)

        if lvl > 0:
            last_alert = r.hget(f"last_alert_time:{res_id}", "time")
            now = time.time()
            if not last_alert or (now - float(last_alert) > 10):
                alert_payload = {
                    "res_id": res_id,
                    "level": lvl,
                    "text": msg_alert,
                    "timestamp": data.get("timestamp", "")
                }
                if lvl >= 4:
                    print(f"[*] Demande de rapport LLM Mistral pour {res_id}...")
                    alert_payload["llm_report"] = generate_medical_report(res_id, msg_alert, hr, spo2)
                client.publish("ehpad/alerts", json.dumps(alert_payload))
                r.hset(f"last_alert_time:{res_id}", "time", now)
                if lvl in [2, 3, 4]:
                    r.hset("active_alerts", res_id, json.dumps({
                        "level": lvl,
                        "time": now,
                        "text": msg_alert,
                        "timestamp": alert_payload["timestamp"]
                    }))
                print(f"[NIVEAU {lvl}] Alerte publiée pour {res_id} : {msg_alert}")

    except Exception as e:
        print(f"Erreur processing: {e}")

# Initialisation
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

print("[*] IA Processor prêt, Escalade activée, et en écoute...")
client.loop_forever()