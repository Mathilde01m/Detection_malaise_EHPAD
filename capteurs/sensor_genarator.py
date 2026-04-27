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
        data["event_type"] = "fall_detected_in_room"
        data["alert_level"] = 4

    return data


def fall_in_corridor_scenario(data: dict, tick: int) -> dict:
    if tick == 55:
        data["bed_sensor"] = False
        data["room_motion"] = False
        data["corridor_motion"] = False
        data["door_sensor"] = "opened"
        data["event_type"] = "fall_detected_in_corridor"
        data["alert_level"] = 4

    return data