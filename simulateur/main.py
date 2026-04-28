import time
import json
from datetime import datetime

import paho.mqtt.client as mqtt

from simulateur.resident_loader import load_residents
from simulateur.vitals_generator import generate_normal_variation
from simulateur.scenario import apply_scenario


CSV_PATH = "data/données_résidents_ephad.csv"

MQTT_BROKER_HOST = "mqtt-broker"
MQTT_BROKER_PORT = 1883
MQTT_QOS = 1


def build_topic(resident_id: str) -> str:
    return f"ehpad/residents/{resident_id}/vitals"


def add_timestamp(vitals: dict) -> dict:
    vitals["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return vitals


def main():
    residents = load_residents(CSV_PATH)

    client = mqtt.Client()
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_start()

    print(f"{len(residents)} résidents chargés depuis {CSV_PATH}")
    print(f"Connexion MQTT : {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")

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
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nArrêt du simulateur...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()