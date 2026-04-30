import time
import json
from datetime import datetime
 
import paho.mqtt.client as mqtt
 
from simulateur.resident_loader import load_residents
from simulateur.vitals_generator import generate_normal_variation
from simulateur.scenario import apply_scenario
 
CSV_PATH = "data/données_résidents_ephad.csv"
 
# --- CORRECTIONS ICI ---
MQTT_BROKER_HOST = "mqtt-broker"  # Le nom du service Docker !
MQTT_BROKER_PORT = 1883
MQTT_QOS = 0

TICK_DURATION_SECONDS = 0.1
STABLE_DURATION_TICKS = 30  # 5 minutes = 300 ticks de 1 seconde

doctor_message_sent_ticks = {}
doctor_treatment_ticks = {}


def build_topic(resident_id: str) -> str:
    return f"ehpad/residents/{resident_id}/vitals"
 
 
def add_timestamp(vitals: dict) -> dict:
    vitals["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return vitals
 
 
def main():
    residents = load_residents(CSV_PATH)
 
    client = mqtt.Client()
   
    # --- CORRECTIONS ICI : Boucle de reconnexion (Patience) ---
    connected = False
    while not connected:
        try:
            print(f"Tentative de connexion à {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            connected = True
            print("[Simulateur Vitaux] Connexion MQTT réussie !")
        except ConnectionRefusedError:
            print("[Simulateur Vitaux] Broker MQTT non prêt. Nouvelle tentative dans 2 secondes...")
            time.sleep(2)
        except Exception as e:
            print(f"[Simulateur Vitaux] Erreur réseau : {e}. Nouvelle tentative...")
            time.sleep(2)
    # ----------------------------------------------------------
 
    client.loop_start()
 
    print(f"{len(residents)} résidents chargés depuis {CSV_PATH}")
 
    tick = 0
 
    try:
        while True:
            print(f"\n--- Tick {tick} ---")
 
            for resident in residents:
                vitals = generate_normal_variation(resident)
                vitals = apply_scenario(vitals, tick)
                vitals = add_timestamp(vitals)
 
                topic = build_topic(vitals["resident_id"])
                payload = json.dumps(vitals, ensure_ascii=False)
 
                client.publish(topic, payload, qos=MQTT_QOS)
 
                print(f"Publié sur {topic} : {payload}")
 
            tick += 1
            time.sleep(10)
 
    except KeyboardInterrupt:
        print("\nArrêt du simulateur...")
        client.loop_stop()
        client.disconnect()
 
 
if __name__ == "__main__":
    main()
 