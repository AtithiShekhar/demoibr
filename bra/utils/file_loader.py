
# ================================
# utils/file_loader.py
# ================================

import json
import os
import sys


def load_input(filename: str = "input.json", data: dict | None = None) -> dict:
    """
    Load input JSON from file OR directly from passed data
    Supports ONLY the new EMR schema
    """

    try:
        # Case 1: data passed directly (API / Queue)
        if data is not None:
            validate_input_schema(data)
            return data

        # Case 2: file-based (CLI usage)
        if not os.path.exists(filename):
            print(f"Error: Input file '{filename}' not found.")
            return None

        with open(filename, "r") as f:
            data = json.load(f)

        validate_input_schema(data)
        return data

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filename}: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def validate_input_schema(data: dict):
    """
    Validate EMR input schema
    """

    if "patientInfo" not in data or not isinstance(data["patientInfo"], dict):
        raise ValueError("Missing or invalid 'patientInfo'")

    if "currentDiagnoses" not in data or not isinstance(data["currentDiagnoses"], list):
        raise ValueError("Missing or invalid 'currentDiagnoses'")

    if not data["currentDiagnoses"]:
        raise ValueError("'currentDiagnoses' cannot be empty")


def extract_analysis_tasks(data: dict) -> list:
    """
    Create task dictionaries for ALL medicines
    Returns list of dicts: [{"drug": "X", "diagnosis": "Y"}, ...]
    """
    tasks = []

    for diagnosis in data.get("currentDiagnoses", []):
        diagnosis_name = diagnosis.get("diagnosisName")
        if not diagnosis_name:
            continue

        meds = diagnosis.get("treatment", {}).get("medications", [])
        for med in meds:
            drug_name = med.get("name")
            if drug_name:
                tasks.append({
                    "drug": drug_name,
                    "diagnosis": diagnosis_name
                })

    return tasks


def load_input_with_defaults(filename: str = "input.json") -> dict:
    """
    Load input and apply safe defaults
    """

    data = load_input(filename)
    if not data:
        sys.exit(1)

    if "PubMed" not in data:
        data["PubMed"] = {}

    if "email" not in data["PubMed"]:
        data["PubMed"]["email"] = "your_email@example.com"

    return data