import random
from datetime import datetime
from capteurs.environment_models import RoomMapping


def generate_environment_data(room: RoomMapping, tick: int) -> dict:
    data = {
        "resident_id": room.resident_id,
        "room": room.room,
        "zone": room.zone,
        "floor": room.floor,
        "timestamp": datetime.utcnow().isoformat() + "Z",

        "bed_sensor": generate_bed_sensor(room, tick),
        "room_motion": generate_room_motion(room, tick),
        "corridor_motion": generate_corridor_motion(room, tick),
        "door_sensor": generate_door_sensor(room, tick),
        "bathroom_motion": generate_bathroom_motion(room, tick),
        "common_area_presence": generate_common_area_presence(room, tick),

        "fall_detected": False,
        "fall_type": None,
        "fall_location": None,
        "fall_cause": None,
        "fall_related_to_malaise": False,

        "event_type": "environment_normal",
        "alert_level": 0,
    }

    data = apply_environment_scenarios(data, tick)

    return data


def generate_bed_sensor(room: RoomMapping, tick: int) -> bool:
    hour_cycle = tick % 120

    if 0 <= hour_cycle < 30:
        return True

    if 30 <= hour_cycle < 90:
        return random.choice([False, False, False, True])

    return random.choice([True, False])


def generate_room_motion(room: RoomMapping, tick: int) -> bool:
    return random.choice([True, False, False])


def generate_corridor_motion(room: RoomMapping, tick: int) -> bool:
    return random.choice([False, False, False, True])


def generate_door_sensor(room: RoomMapping, tick: int) -> str:
    return random.choice(["closed", "closed", "closed", "opened"])


def generate_bathroom_motion(room: RoomMapping, tick: int) -> bool:
    return random.choice([False, False, False, True])


def generate_common_area_presence(room: RoomMapping, tick: int) -> bool:
    cycle = tick % 120

    if 45 <= cycle <= 65:
        return random.choice([True, True, False])

    return random.choice([False, False, True])


def apply_environment_scenarios(data: dict, tick: int) -> dict:
    resident_id = data["resident_id"]

    if resident_id == "R7":
        return alzheimer_fugue_scenario(data, tick)

    if resident_id == "R9":
        return prolonged_bed_immobility_scenario(data, tick)

    if resident_id == "R14":
        return fall_in_room_scenario(data, tick)

    if resident_id == "R11":
        return fall_in_corridor_scenario(data, tick)

    if resident_id == "R21":
        return fall_after_cardiac_malaise_environment(data, tick)

    if resident_id == "R25":
        return fall_after_syncope_environment(data, tick)

    return data


def alzheimer_fugue_scenario(data: dict, tick: int) -> dict:
    if 50 <= tick < 95:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = True
        data["door_sensor"] = "opened"
        data["event_type"] = "wandering_in_corridor"
        data["alert_level"] = 2

    elif tick >= 95:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = True
        data["door_sensor"] = "main_exit_opened"
        data["event_type"] = "exit_attempt"
        data["alert_level"] = 3

    return data


def prolonged_bed_immobility_scenario(data: dict, tick: int) -> dict:
    if tick >= 30:
        data["bed_sensor"] = True
        data["room_motion"] = False
        data["corridor_motion"] = False
        data["bathroom_motion"] = False
        data["common_area_presence"] = False
        data["event_type"] = "prolonged_bed_presence"
        data["alert_level"] = 1

    if tick >= 70:
        data["event_type"] = "abnormal_prolonged_immobility"
        data["alert_level"] = 2

    return data


def fall_in_room_scenario(data: dict, tick: int) -> dict:
    if tick == 75:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = False
        data["door_sensor"] = "closed"
        data["bathroom_motion"] = False
        data["common_area_presence"] = False

        data["fall_detected"] = True
        data["fall_type"] = "mechanical"
        data["fall_location"] = "room"
        data["fall_cause"] = "chute mécanique probable en chambre"
        data["fall_related_to_malaise"] = False

        data["event_type"] = "mechanical_fall"
        data["alert_level"] = 4

    return data


def fall_in_corridor_scenario(data: dict, tick: int) -> dict:
    if tick == 55:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = False
        data["door_sensor"] = "opened"
        data["bathroom_motion"] = False
        data["common_area_presence"] = False

        data["fall_detected"] = True
        data["fall_type"] = "balance_disorder"
        data["fall_location"] = "corridor"
        data["fall_cause"] = "trouble de l'équilibre lié à Parkinson"
        data["fall_related_to_malaise"] = False

        data["event_type"] = "parkinson_balance_fall"
        data["alert_level"] = 4

    return data


def fall_after_cardiac_malaise_environment(data: dict, tick: int) -> dict:
    if tick >= 90:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = False
        data["door_sensor"] = "closed"
        data["bathroom_motion"] = False
        data["common_area_presence"] = False

        data["fall_detected"] = True
        data["fall_type"] = "malaise_cardiaque"
        data["fall_location"] = "room"
        data["fall_cause"] = "malaise cardiaque probable"
        data["fall_related_to_malaise"] = True

        data["event_type"] = "fall_after_cardiac_malaise"
        data["alert_level"] = 4

    return data


def fall_after_syncope_environment(data: dict, tick: int) -> dict:
    if tick >= 90:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = False
        data["door_sensor"] = "closed"
        data["bathroom_motion"] = False
        data["common_area_presence"] = False

        data["fall_detected"] = True
        data["fall_type"] = "syncope_hypotension"
        data["fall_location"] = "room"
        data["fall_cause"] = "syncope ou hypotension probable"
        data["fall_related_to_malaise"] = True

        data["event_type"] = "fall_after_syncope"
        data["alert_level"] = 4

    return data