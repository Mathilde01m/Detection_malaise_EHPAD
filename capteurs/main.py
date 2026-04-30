import time
import json
import paho.mqtt.client as mqtt


from capteurs.room_loader import load_rooms
from capteurs.sensor_generator import generate_environment_data


ROOMS_PATH = "data/rooms_mapping.csv"

# --- CORRECTIONS ICI ---
MQTT_BROKER_HOST = "mqtt-broker"  # Le nom du service Docker !
MQTT_BROKER_PORT = 1883
MQTT_QOS = 1  # QoS 1 pour garantir la livraison des messages (Fiabilité)
# -----------------------


def build_topic(resident_id: str) -> str:
    return f"ehpad/residents/{resident_id}/environment"


def main():
    rooms = load_rooms(ROOMS_PATH)

    client = mqtt.Client()
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_start()

    print(f"{len(rooms)} chambres chargées depuis {ROOMS_PATH}")
    print(f"Connexion MQTT : {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")

    tick = 0

    try:
        while True:
            print(f"\n--- Environment Tick {tick} ---")

            for room in rooms:
                environment_data = generate_environment_data(room, tick)

                topic = build_topic(environment_data["resident_id"])
                payload = json.dumps(environment_data, ensure_ascii=False)

                client.publish(topic, payload, qos=MQTT_QOS)

                print(f"Publié sur {topic} : {payload}")

            tick += 1
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nArrêt du simulateur de capteurs environnementaux...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()