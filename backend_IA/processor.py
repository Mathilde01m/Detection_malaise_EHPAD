import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import json
import redis
import time
import requests # NOUVEAU: Pour appeler le LLM
from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion
from models.ai_engine import ai 

REDIS_HOST = "redis-cache"
OLLAMA_URL = "http://ollama:11434/api/generate" # L'URL de ton conteneur LLM
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

def generate_medical_report(res_id, alert_text, vitals):
    """Fait appel au LLM local pour rédiger une transmission infirmière."""
    prompt = f"Agis comme un médecin de garde. Rédige une transmission infirmière ultra-courte (2 phrases max) pour une urgence concernant le résident {res_id}. Motif : {alert_text}. Constantes actuelles : FC {vitals['hr']} bpm, SpO2 {vitals['spo2']}%. Sois clinique et direct."
    
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "mistral", # On utilise le modèle Mistral (très bon en français)
            "prompt": prompt,
            "stream": False
        }, timeout=15) # Timeout de 15s au cas où le modèle met du temps
        return response.json()['response']
    except Exception as e:
        return f"Échec de la génération IA: {e}"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        res_id = data['resident_id']
        
        r.lpush(f"history:{res_id}", json.dumps(data['vitals']))
        r.ltrim(f"history:{res_id}", 0, 9)
        
        history_raw = r.lrange(f"history:{res_id}", 0, -1)
        history = [json.loads(h) for h in history_raw][::-1] 
        
        lvl = 0
        msg_alert = ""

        if 'accel' in data and ai.predict_fall(data['accel']) == 1:
            lvl, msg_alert = 5, "CHUTE DETECTEE"
        elif len(history) == 10 and ai.predict_vitals_risk(history) == 1:
            lvl, msg_alert = 4, "RISQUE MALAISE IMMINENT"
        elif 'ambient' in data and ai.predict_ambient_anomaly(data['ambient']) == 1:
            lvl, msg_alert = 3, "COMPORTEMENT ANORMAL"
        elif data['vitals']['spo2'] < 90:
            lvl, msg_alert = 2, "SpO2 BASSE"

        if lvl > 0:
            alert = {"res_id": res_id, "level": lvl, "text": msg_alert}
            
            # ===== INTERVENTION DU LLM =====
            # On ne génère un rapport que pour les urgences vitales (4 ou 5) pour ne pas saturer le CPU
            if lvl >= 4:
                print(f"[*] Demande de rapport LLM pour {res_id}...")
                report = generate_medical_report(res_id, msg_alert, data['vitals'])
                alert["llm_report"] = report # On ajoute le texte généré au JSON
            
            client.publish("ehpad/alerts", json.dumps(alert))

    except Exception as e:
        pass

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        res_id = data['resident_id']
        
        # Sauvegarde pour le LSTM (10 dernières secondes)
        r.lpush(f"history:{res_id}", json.dumps(data['vitals']))
        r.ltrim(f"history:{res_id}", 0, 9)
        
        history_raw = r.lrange(f"history:{res_id}", 0, -1)
        # On inverse pour avoir l'ordre chronologique
        history = [json.loads(h) for h in history_raw][::-1] 
        
        # ==========================================
        # MULTI-EVALUATION IA
        # ==========================================
        lvl = 0
        msg_alert = ""

        # 1. Random Forest : Détection Chute (Priorité Absolue)
        if 'accel' in data and ai.predict_fall(data['accel']) == 1:
            lvl, msg_alert = 5, "CHUTE DETECTEE (IA RF)"
            
        # 2. LSTM : Risque vital
        elif len(history) == 10 and ai.predict_vitals_risk(history) == 1:
            lvl, msg_alert = 4, "RISQUE MALAISE IMMINENT (IA LSTM)"
            
        # 3. Isolation Forest : Comportement anormal
        elif 'ambient' in data and ai.predict_ambient_anomaly(data['ambient']) == 1:
            lvl, msg_alert = 3, "COMPORTEMENT ANORMAL (IA IF)"
            
        # Seuils basiques de sécurité
        elif data['vitals']['spo2'] < 90:
            lvl, msg_alert = 2, "SpO2 BASSE"

        # Envoi de l'alerte si l'IA a trouvé quelque chose
        if lvl > 0:
            alert = {"res_id": res_id, "level": lvl, "text": msg_alert}
            client.publish("ehpad/alerts", json.dumps(alert))

    except Exception as e:
        print(f"Erreur processing: {e}")

client = mqtt_client.Client(CallbackAPIVersion.VERSION1, "Backend_IA")
client.on_message = on_message

while True:
    try:
        client.connect("mqtt-broker", 1883)
        break
    except:
        time.sleep(5)

client.subscribe("ehpad/room/#")
print("[*] IA Processor prêt et en écoute...")
client.loop_forever()