import pandas as pd
from simulateur.models import Resident


def parse_blood_pressure(bp: str) -> tuple[int, int]:
    systolic, diastolic = bp.split("/")
    return int(systolic), int(diastolic)


def load_residents(csv_path: str) -> list[Resident]:
    df = pd.read_csv(csv_path)
    residents = []

    for _, row in df.iterrows():
        systolic, diastolic = parse_blood_pressure(row["tension_arterielle"])

        resident = Resident(
            resident_id=row["resident_id"],
            age=int(row["age"]),
            pathologie=row["pathologie"],
            mobilite=row["mobilite"],
            risque_principal=row["risque_principal"],
            heart_rate=int(row["frequence_cardiaque_bpm"]),
            spo2=int(row["spo2_%"]),
            systolic_bp=systolic,
            diastolic_bp=diastolic,
            temperature=float(row["temperature_c"]),
            glucose=int(row["glycemie_mg_dl"]),
        )

        residents.append(resident)

    return residents