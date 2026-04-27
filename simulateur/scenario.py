def apply_scenario(vitals: dict, tick: int) -> dict:
    resident_id = vitals["resident_id"]

    if resident_id == "R21":
        return cardiac_malaise(vitals, tick)
    if resident_id == "R32":
        return respiratory_distress(vitals, tick)
    if resident_id == "R26":
        return hypoglycemia(vitals, tick)
    if resident_id == "R25":
        return hypotension_syncope(vitals, tick)
    if resident_id == "R20":
        return hypertensive_crisis(vitals, tick)
    if resident_id == "R35":
        return severe_respiratory_distress(vitals, tick)
    if resident_id == "R14":
        return mechanical_fall(vitals, tick)
    if resident_id == "R11":
        return parkinson_fall(vitals, tick)
    if resident_id == "R7":
        return alzheimer_wandering(vitals, tick)
    if resident_id == "R9":
        return prolonged_immobility(vitals, tick)

    return vitals


def cardiac_malaise(vitals: dict, tick: int) -> dict:
    if 30 <= tick < 60:
        vitals["heart_rate"] += 10
        vitals["systolic_bp"] -= 8
        vitals["movement_level"] = max(0, vitals["movement_level"] - 10)
        vitals["ai_risk_score"] = 65
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "cardiac_malaise_risk"
        vitals["alert_level"] = 2

    elif 60 <= tick < 90:
        vitals["heart_rate"] += 25
        vitals["systolic_bp"] -= 20
        vitals["movement_level"] = max(0, vitals["movement_level"] - 25)
        vitals["ai_risk_score"] = 88
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "cardiac_malaise_predicted"
        vitals["alert_level"] = 3

    elif tick >= 90:
        vitals["fall_detected"] = True
        vitals["movement_level"] = 0
        vitals["ai_risk_score"] = 95
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "fall_after_cardiac_malaise"
        vitals["fall_related_to_malaise"] = True
        vitals["alert_level"] = 4

    return vitals


def respiratory_distress(vitals: dict, tick: int) -> dict:
    if 20 <= tick < 70:
        vitals["spo2"] -= 3
        vitals["heart_rate"] += 8
        vitals["ai_risk_score"] = 70
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "respiratory_risk"
        vitals["alert_level"] = 2

    elif tick >= 70:
        vitals["spo2"] -= 7
        vitals["heart_rate"] += 18
        vitals["movement_level"] = max(0, vitals["movement_level"] - 20)
        vitals["ai_risk_score"] = 90
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "respiratory_distress"
        vitals["alert_level"] = 4

    return vitals


def hypoglycemia(vitals: dict, tick: int) -> dict:
    if 40 <= tick < 80:
        vitals["glucose"] -= 25
        vitals["movement_level"] = max(0, vitals["movement_level"] - 15)
        vitals["ai_risk_score"] = 72
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "hypoglycemia_risk"
        vitals["alert_level"] = 2

    elif tick >= 80:
        vitals["glucose"] -= 45
        vitals["movement_level"] = 0
        vitals["ai_risk_score"] = 89
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "severe_hypoglycemia"
        vitals["alert_level"] = 3

    return vitals


def hypotension_syncope(vitals: dict, tick: int) -> dict:
    if 25 <= tick < 65:
        vitals["systolic_bp"] -= 15
        vitals["diastolic_bp"] -= 8
        vitals["heart_rate"] += 8
        vitals["movement_level"] = max(0, vitals["movement_level"] - 10)
        vitals["ai_risk_score"] = 68
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "syncope_risk"
        vitals["alert_level"] = 2

    elif 65 <= tick < 90:
        vitals["systolic_bp"] -= 30
        vitals["diastolic_bp"] -= 15
        vitals["heart_rate"] += 18
        vitals["movement_level"] = max(0, vitals["movement_level"] - 30)
        vitals["ai_risk_score"] = 86
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "syncope_predicted"
        vitals["alert_level"] = 3

    elif tick >= 90:
        vitals["fall_detected"] = True
        vitals["movement_level"] = 0
        vitals["systolic_bp"] -= 35
        vitals["ai_risk_score"] = 93
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "fall_after_syncope"
        vitals["fall_related_to_malaise"] = True
        vitals["alert_level"] = 4

    return vitals


def hypertensive_crisis(vitals: dict, tick: int) -> dict:
    if 35 <= tick < 80:
        vitals["systolic_bp"] += 25
        vitals["diastolic_bp"] += 12
        vitals["heart_rate"] += 10
        vitals["ai_risk_score"] = 74
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "hypertension_risk"
        vitals["alert_level"] = 2

    elif tick >= 80:
        vitals["systolic_bp"] += 45
        vitals["diastolic_bp"] += 20
        vitals["heart_rate"] += 18
        vitals["ai_risk_score"] = 91
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "hypertensive_crisis"
        vitals["alert_level"] = 4

    return vitals


def severe_respiratory_distress(vitals: dict, tick: int) -> dict:
    if 45 <= tick < 85:
        vitals["spo2"] -= 4
        vitals["heart_rate"] += 10
        vitals["movement_level"] = max(0, vitals["movement_level"] - 10)
        vitals["ai_risk_score"] = 76
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "severe_respiratory_risk"
        vitals["alert_level"] = 3

    elif tick >= 85:
        vitals["spo2"] -= 10
        vitals["heart_rate"] += 22
        vitals["movement_level"] = 0
        vitals["ai_risk_score"] = 96
        vitals["predicted_by_ai"] = True
        vitals["event_type"] = "severe_respiratory_distress"
        vitals["alert_level"] = 4

    return vitals


def mechanical_fall(vitals: dict, tick: int) -> dict:
    if tick == 75:
        vitals["fall_detected"] = True
        vitals["movement_level"] = 0
        vitals["ai_risk_score"] = 12
        vitals["predicted_by_ai"] = False
        vitals["event_type"] = "mechanical_fall"
        vitals["fall_related_to_malaise"] = False
        vitals["alert_level"] = 4

    return vitals


def parkinson_fall(vitals: dict, tick: int) -> dict:
    if tick == 55:
        vitals["fall_detected"] = True
        vitals["movement_level"] = 0
        vitals["ai_risk_score"] = 18
        vitals["predicted_by_ai"] = False
        vitals["event_type"] = "parkinson_balance_fall"
        vitals["fall_related_to_malaise"] = False
        vitals["alert_level"] = 4

    return vitals


def alzheimer_wandering(vitals: dict, tick: int) -> dict:
    if 50 <= tick < 95:
        vitals["movement_level"] = 95
        vitals["ai_risk_score"] = 25
        vitals["predicted_by_ai"] = False
        vitals["event_type"] = "wandering"
        vitals["alert_level"] = 2

    elif tick >= 95:
        vitals["movement_level"] = 100
        vitals["door_event"] = "main_exit_opened"
        vitals["ai_risk_score"] = 30
        vitals["predicted_by_ai"] = False
        vitals["event_type"] = "fugue_risk"
        vitals["alert_level"] = 3

    return vitals


def prolonged_immobility(vitals: dict, tick: int) -> dict:
    if 30 <= tick < 70:
        vitals["movement_level"] = 0
        vitals["event_type"] = "prolonged_immobility"
        vitals["alert_level"] = 1

    elif tick >= 70:
        vitals["movement_level"] = 0
        vitals["event_type"] = "long_prolonged_immobility"
        vitals["alert_level"] = 2

    return vitals