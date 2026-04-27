from dataclasses import dataclass


@dataclass
class RoomMapping:
    resident_id: str
    room: str
    zone: str
    floor: int