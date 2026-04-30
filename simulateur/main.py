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
MQTT_QOS = 0

TICK_DURATION_SECONDS = 10
STABLE_DURATION_TICKS = 30  # 5 minutes = 30 ticks de 10 secondes

doctor_message_sent_ticks = {}
doctor_treatment_ticks = {}


def build_topic(resident_id: str) -> str:
    return f"ehpad/residents/{resident_id}/vitals"


def add_timestamp(vitals: dict) -> dict:
    vitals["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return vitals


def should_notify_doctor(vitals: dict) -> bool:
    return vitals.get("alert_level", 0) >= 4


def mark_doctor_message_if_needed(vitals: dict, tick: int) -> dict:
    resident_id = vitals["resident_id"]

    if should_notify_doctor(vitals):
        if resident_id not in doctor_message_sent_ticks:
            doctor_message_sent_ticks[resident_id] = tick

    if resident_id in doctor_message_sent_ticks:
        vitals["doctor_message_sent_tick"] = doctor_message_sent_ticks[resident_id]

    if resident_id in doctor_treatment_ticks:
        vitals["doctor_treatment_tick"] = doctor_treatment_ticks[resident_id]

    return vitals


def auto_treat_patient_if_needed(vitals: dict, tick: int) -> dict:
    """
    Simulation simple :
    le médecin traite automatiquement le patient 1 tick après une alerte forte.
    Tu peux augmenter cette valeur si tu veux simuler un délai plus long.
    """

    resident_id = vitals["resident_id"]
    message_tick = doctor_message_sent_ticks.get(resident_id)

    if message_tick is None:
        return vitals

    if resident_id not in doctor_treatment_ticks and tick >= message_tick + 1:
        doctor_treatment_ticks[resident_id] = tick
        vitals["doctor_treatment_tick"] = tick
        vitals["treated_by_doctor"] = True
        vitals["event_type"] = "treated_by_doctor"
        vitals["alert_message"] = "Patient traité par le médecin"

    return vitals


def reset_medical_tracking_if_stable_period_finished(resident_id: str, tick: int):
    """
    Après 5 minutes de stabilité après traitement,
    on autorise à nouveau les scénarios à évoluer normalement.
    """

    treatment_tick = doctor_treatment_ticks.get(resident_id)

    if treatment_tick is None:
        return

    if tick - treatment_tick >= STABLE_DURATION_TICKS:
        doctor_message_sent_ticks.pop(resident_id, None)
        doctor_treatment_ticks.pop(resident_id, None)


def main():
    residents = load_residents(CSV_PATH)

    client = mqtt.Client()

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

    client.loop_start()

    print(f"{len(residents)} résidents chargés depuis {CSV_PATH}")

    tick = 0

    try:
        while True:
            print(f"\n--- Tick {tick} ---")

            for resident in residents:
                resident_id = resident["resident_id"]

                reset_medical_tracking_if_stable_period_finished(resident_id, tick)

                vitals = generate_normal_variation(resident)

                if resident_id in doctor_message_sent_ticks:
                    vitals["doctor_message_sent_tick"] = doctor_message_sent_ticks[resident_id]

                if resident_id in doctor_treatment_ticks:
                    vitals["doctor_treatment_tick"] = doctor_treatment_ticks[resident_id]

                vitals = apply_scenario(vitals, tick)

                vitals = mark_doctor_message_if_needed(vitals, tick)
                vitals = auto_treat_patient_if_needed(vitals, tick)

                vitals = add_timestamp(vitals)

                topic = build_topic(vitals["resident_id"])
                payload = json.dumps(vitals, ensure_ascii=False)

                client.publish(topic, payload, qos=MQTT_QOS)

                print(f"Publié sur {topic} : {payload}")

            tick += 1
            time.sleep(TICK_DURATION_SECONDS)

    except KeyboardInterrupt:
        print("\nArrêt du simulateur...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()