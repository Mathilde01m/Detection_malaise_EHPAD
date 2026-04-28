import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import json
import redis
import time
import requests
from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion
from models.ai_engine import ai 

# Configurations
REDIS_HOST = "redis-cache"
MQTT_BROKER = "mqtt-broker"
OLLAMA_URL = "http://ollama:11434/api/generate" # Nom du conteneur défini dans le docker-compose

# Connexion à Redis
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

def generate_medical_report(res_id, alert_text, hr, spo2):
    """Fait appel au LLM local (Ollama) pour rédiger une transmission infirmière."""
    prompt = f"Agis comme un médecin de garde. Rédige une transmission infirmière ultra-courte (2 phrases max) pour une urgence concernant le résident {res_id}. Motif : {alert_text}. Constantes actuelles : FC {hr} bpm, SpO2 {spo2}%. Sois clinique et direct."
    
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }, timeout=15)
        return response.json()['response']
    except Exception as e:
        return f"Échec de la génération IA : Le conteneur Ollama est-il prêt ? ({e})"

def evaluate_resident_state(res_id):
    """Évalue l'état global du résident et renvoie le niveau d'alerte de 1 à 5"""
    # 1. Récupération des données dans Redis
    current_state = r.hgetall(f"state:{res_id}")
    history_raw = r.lrange(f"history:{res_id}", 0, -1)
    history = [json.loads(h) for h in history_raw][::-1] 
    
    # Valeurs par défaut sécurisées
    hr = float(current_state.get('hr', 70))
    spo2 = float(current_state.get('spo2', 98))
    event_type = current_state.get('event_type', 'normal')
    env_alert_level = int(current_state.get('alert_level', 0))

    # --- ÉVALUATION M5 (5 NIVEAUX) ---
    
    # NIVEAU 5 : Danger vital (Constantes extrêmes ou arrêt)
    if hr < 30 or hr > 160 or spo2 < 85:
        return 5, "DANGER VITAL - Constantes critiques", hr, spo2

    # NIVEAU 4 : Urgence (Chute détectée par le scénario capteur)
    if env_alert_level == 4 or "fall" in event_type:
        return 4, "URGENCE - Chute détectée", hr, spo2

    # NIVEAU 3 : Alerte (Prédiction IA LSTM ou SpO2 très limite)
    if len(history) == 10 and ai.predict_vitals_risk(history) == 1:
        return 3, "ALERTE IA - Risque de malaise imminent", hr, spo2
    if spo2 < 93:
        return 3, f"ALERTE - SpO2 basse ({spo2}%)", hr, spo2

    # NIVEAU 2 : Attention (Comportement anormal / fugue)
    if env_alert_level == 2 or "wandering" in event_type:
        return 2, "ATTENTION - Comportement anormal", hr, spo2

    # NIVEAU 1 : Information (Immobilité prolongée)
    if env_alert_level == 1 or "prolonged" in event_type:
        return 1, "INFORMATION - Immobilité prolongée détectée", hr, spo2

    return 0, "", hr, spo2

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        data = json.loads(msg.payload)
        
        # Le topic est de la forme: ehpad/residents/R1/vitals ou .../environment
        parts = topic.split('/')
        if len(parts) < 4:
            return
            
        res_id = parts[2]
        msg_type = parts[3]
        
        # 1. MISE À JOUR DU CACHE REDIS
        if msg_type == "vitals":
            r.hset(f"state:{res_id}", "hr", data.get('hr', 0))
            r.hset(f"state:{res_id}", "spo2", data.get('spo2', 0))
            
            # Historique pour le réseau LSTM
            r.lpush(f"history:{res_id}", json.dumps(data))
            r.ltrim(f"history:{res_id}", 0, 9)
            
        elif msg_type == "environment":
            r.hset(f"state:{res_id}", "event_type", data.get('event_type', ''))
            r.hset(f"state:{res_id}", "alert_level", data.get('alert_level', 0))

        # 2. ÉVALUATION ET DÉCLENCHEMENT
        lvl, msg_alert, hr, spo2 = evaluate_resident_state(res_id)

        if lvl > 0:
            # Système Anti-Spam (On ne renvoie pas la même alerte toutes les secondes)
            last_alert = r.hget(f"last_alert_time:{res_id}", "time")
            now = time.time()
            
            if not last_alert or (now - float(last_alert) > 10): # Attente de 10s entre deux alertes
                
                alert_payload = {
                    "res_id": res_id, 
                    "level": lvl, 
                    "text": msg_alert,
                    "timestamp": data.get("timestamp", "")
                }
                
                # INTERVENTION DU LLM SEULEMENT POUR LES URGENCES MAJEURES (4 et 5)
                if lvl >= 4:
                    print(f"[*] Demande de rapport LLM Mistral pour {res_id}...")
                    alert_payload["llm_report"] = generate_medical_report(res_id, msg_alert, hr, spo2)
                
                # Envoi au Dashboard via MQTT
                client.publish("ehpad/alerts", json.dumps(alert_payload))
                r.hset(f"last_alert_time:{res_id}", "time", now)
                
                print(f"[NIVEAU {lvl}] Alerte publiée pour {res_id} : {msg_alert}")

    except Exception as e:
        print(f"Erreur processing: {e}")

# Initialisation MQTT
client = mqtt_client.Client(CallbackAPIVersion.VERSION1, "Backend_IA")
client.on_message = on_message

# Boucle de patience pour la connexion (Race Condition)
connected = False
while not connected:
    try:
        print("Tentative de connexion au broker MQTT...")
        client.connect(MQTT_BROKER, 1883)
        connected = True
    except Exception:
        time.sleep(3)

# On s'abonne à la fois aux vitaux et à l'environnement !
client.subscribe("ehpad/residents/#")
print("[*] IA Processor prêt et en écoute...")
client.loop_forever()