
# ================================
# main.py
# ================================

from duplication.checker import start as duplication_start
from utils.analysis.analysis_executor import execute_parallel_analysis
from utils.file_loader import load_input, parse_diagnoses
import os


def main(verbose=True):
    data = load_input()

    patient = data.get("patient", {})
    prescription = data.get("prescription", [])
    email = data.get("PubMed", {}).get("email")

    diagnoses = parse_diagnoses(patient.get("diagnosis", ""))

    # --- RUN DUPLICATION ONCE ---
    duplication_result = None
    if isinstance(prescription, list) and len(prescription) > 1:
        duplication_result = duplication_start(data)

    os.makedirs("results", exist_ok=True)

    tasks = [(drug, dx) for drug in prescription for dx in diagnoses]

    results, elapsed = execute_parallel_analysis(
        tasks,
        patient,
        email,
        duplication_result
    )

    if verbose:
        print(f"Completed {len(results)} analyses in {elapsed:.2f}s")

    return True
