import pandas as pd
from capteurs.environment_models import RoomMapping


def load_rooms(csv_path: str) -> list[RoomMapping]:
    df = pd.read_csv(csv_path)
    rooms = []

    for _, row in df.iterrows():
        rooms.append(
            RoomMapping(
                resident_id=row["resident_id"],
                room=str(row["room"]),
                zone=row["zone"],
                floor=int(row["floor"]),
            )
        )

    return rooms