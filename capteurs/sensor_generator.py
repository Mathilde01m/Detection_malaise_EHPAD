import random
from datetime import datetime
from capteurs.environment_models import RoomMapping


NORMAL_CYCLE_DURATION = 240


def generate_environment_data(room: RoomMapping, tick: int) -> dict:
    presence = generate_coherent_presence(tick)

    data = {
        "resident_id": room.resident_id,
        "room": room.room,
        "zone": room.zone,
        "floor": room.floor,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **presence,
        "event_type": "environment_normal",
        "alert_level": 0,
    }

    return apply_environment_scenarios(data, tick)


def generate_coherent_presence(tick: int) -> dict:
    """
    Génère un état cohérent :
    - un résident ne peut pas être au lit, dans le couloir,
      dans la salle de bain et en zone commune en même temps ;
    - les transitions sont plus lentes ;
    - quelques petits bruits réalistes sont conservés.
    """

    cycle = tick % NORMAL_CYCLE_DURATION

    if 0 <= cycle < 80:
        location = "bed"
    elif 80 <= cycle < 120:
        location = "room"
    elif 120 <= cycle < 150:
        location = "bathroom"
    elif 150 <= cycle < 180:
        location = "corridor"
    elif 180 <= cycle < 220:
        location = "common_area"
    else:
        location = "room"

    bed_sensor = location == "bed"
    room_motion = location == "room"
    bathroom_motion = location == "bathroom"
    corridor_motion = location == "corridor"
    common_area_presence = location == "common_area"

    door_sensor = "closed"
    if location in ["corridor", "common_area"]:
        door_sensor = random.choice(["opened", "closed", "closed"])

    return {
        "bed_sensor": bed_sensor,
        "room_motion": add_noise(room_motion, probability=0.05),
        "corridor_motion": add_noise(corridor_motion, probability=0.03),
        "door_sensor": door_sensor,
        "bathroom_motion": add_noise(bathroom_motion, probability=0.03),
        "common_area_presence": add_noise(common_area_presence, probability=0.03),
    }


def add_noise(value: bool, probability: float = 0.03) -> bool:
    """
    Petit bruit capteur réaliste.
    Exemple : un capteur peut manquer un mouvement ou détecter brièvement à tort.
    """
    if random.random() < probability:
        return not value
    return value


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
    """
    Fugue progressive :
    - d'abord errance en chambre / couloir ;
    - puis tentative de sortie.
    Les durées sont volontairement plus longues.
    """

    if 120 <= tick < 240:
        data.update({
            "bed_sensor": False,
            "room_motion": False,
            "bathroom_motion": False,
            "common_area_presence": False,
            "corridor_motion": True,
            "door_sensor": "opened",
            "event_type": "wandering_in_corridor",
            "alert_level": 2,
        })

    elif 240 <= tick < 360:
        data.update({
            "bed_sensor": False,
            "room_motion": False,
            "bathroom_motion": False,
            "common_area_presence": False,
            "corridor_motion": True,
            "door_sensor": "main_exit_opened",
            "event_type": "exit_attempt",
            "alert_level": 3,
        })

    return data


def prolonged_bed_immobility_scenario(data: dict, tick: int) -> dict:
    """
    Immobilité au lit :
    - présence au lit prolongée ;
    - escalade lente vers immobilité anormale.
    """

    if 120 <= tick < 300:
        data.update({
            "bed_sensor": True,
            "room_motion": False,
            "corridor_motion": False,
            "door_sensor": "closed",
            "bathroom_motion": False,
            "common_area_presence": False,
            "event_type": "prolonged_bed_presence",
            "alert_level": 1,
        })

    elif tick >= 300:
        data.update({
            "bed_sensor": True,
            "room_motion": False,
            "corridor_motion": False,
            "door_sensor": "closed",
            "bathroom_motion": False,
            "common_area_presence": False,
            "event_type": "abnormal_prolonged_immobility",
            "alert_level": 2,
        })

    return data


def fall_in_room_scenario(data: dict, tick: int) -> dict:
    """
    Chute en chambre :
    l'événement reste actif assez longtemps pour être détecté/acquitté.
    """

    if 180 <= tick < 300:
        data.update({
            "bed_sensor": False,
            "room_motion": False,
            "corridor_motion": False,
            "door_sensor": "closed",
            "bathroom_motion": False,
            "common_area_presence": False,
            "event_type": "fall_detected_in_room",
            "alert_level": 4,
        })

    return data


def fall_in_corridor_scenario(data: dict, tick: int) -> dict:
    """
    Chute dans le couloir :
    l'événement dure plusieurs ticks au lieu d'un seul.
    """

    if 150 <= tick < 270:
        data.update({
            "bed_sensor": False,
            "room_motion": False,
            "corridor_motion": False,
            "door_sensor": "opened",
            "bathroom_motion": False,
            "common_area_presence": False,
            "event_type": "fall_detected_in_corridor",
            "alert_level": 4,
        })

    return data