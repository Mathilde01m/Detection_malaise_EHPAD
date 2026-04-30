import random
from simulateur.models import Resident


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def generate_normal_variation(resident: Resident) -> dict:
    pathologie = resident.pathologie.lower()

    heart_rate_variation = random.randint(-3, 3)
    spo2_variation = random.randint(-1, 1)
    systolic_variation = random.randint(-5, 5)
    diastolic_variation = random.randint(-3, 3)
    temperature_variation = random.uniform(-0.1, 0.1)
    glucose_variation = random.randint(-5, 5)

    if "bpco" in pathologie or "respiratoire" in pathologie or "asthme" in pathologie:
        spo2_variation = random.randint(-2, 1)

    if "diabète" in pathologie or "diabete" in pathologie:
        glucose_variation = random.randint(-15, 20)

    if (
        "cardiaque" in pathologie
        or "hypertension" in pathologie
        or "arythmie" in pathologie
        or "infarctus" in pathologie
        or "hypotension" in pathologie
    ):
        heart_rate_variation = random.randint(-8, 8)
        systolic_variation = random.randint(-10, 12)

    heart_rate = clamp(resident.heart_rate + heart_rate_variation, 45, 150)
    spo2 = clamp(resident.spo2 + spo2_variation, 80, 100)
    systolic_bp = clamp(resident.systolic_bp + systolic_variation, 80, 190)
    diastolic_bp = clamp(resident.diastolic_bp + diastolic_variation, 45, 110)
    temperature = round(clamp(resident.temperature + temperature_variation, 35.5, 39.5), 1)
    glucose = clamp(resident.glucose + glucose_variation, 45, 300)

    movement_level = generate_movement_level(resident)

    return {
        "resident_id": resident.resident_id,
        "age": resident.age,
        "pathologie": resident.pathologie,
        "mobilite": resident.mobilite,
        "risque_principal": resident.risque_principal,

        "heart_rate": int(heart_rate),
        "spo2": int(spo2),
        "systolic_bp": int(systolic_bp),
        "diastolic_bp": int(diastolic_bp),
        "temperature": temperature,
        "glucose": int(glucose),
        "movement_level": movement_level,

        "fall_detected": False,
        "fall_type": None,
        "fall_location": None,
        "fall_cause": None,
        "fall_related_to_malaise": False,

        "door_event": None,
        "ai_risk_score": 0,
        "predicted_by_ai": False,
        "event_type": "normal",
        "alert_level": 0,
    }


def generate_movement_level(resident: Resident) -> int:
    mobility = resident.mobilite.lower()

    if mobility == "autonome":
        return random.randint(40, 100)

    if mobility in ["marche", "canne"]:
        return random.randint(25, 80)

    if mobility == "marchette":
        return random.randint(15, 60)

    if mobility == "fauteuil":
        return random.randint(5, 35)

    if mobility in ["lit", "lit/fauteuil"]:
        return random.randint(0, 20)

    return random.randint(10, 60)