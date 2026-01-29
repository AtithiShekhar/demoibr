import json
from adrs.app import start


def test_start():
    with open("./adrs/patient_input.json", "r") as f:
        patient_data = json.load(f)

    result = start(
        drug=None,
        patient_data=patient_data,
        scoring_system=None
    )

    print("\n=== START() OUTPUT ===")
    print(result)


if __name__ == "__main__":
    test_start()