import time
import json

from simulateur.resident_loader import load_residents
from simulateur.vitals_generator import generate_normal_variation
from simulateur.scenario import apply_scenario


CSV_PATH = "data/données_résidents_ephad.csv"


def main():
    residents = load_residents(CSV_PATH)
    tick = 0

    print(f"{len(residents)} résidents chargés depuis {CSV_PATH}")

    while True:
        print(f"\n--- Tick {tick} ---")

        for resident in residents:
            vitals = generate_normal_variation(resident)
            vitals = apply_scenario(vitals, tick)

            print(json.dumps(vitals, ensure_ascii=False))

        tick += 1
        time.sleep(1)


if __name__ == "__main__":
    main()