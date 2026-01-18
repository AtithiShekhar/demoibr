
# ================================
# utils/analysis/analysis_executor.py
# ================================

from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.analysis.analysis_worker import analyze_drug_diagnosis
import time


def execute_parallel_analysis(tasks, patient, email, duplication_result, max_workers=4):
    results = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for thread_id, (drug, diagnosis) in enumerate(tasks, start=1):
            futures.append(
                executor.submit(
                    analyze_drug_diagnosis,
                    drug,
                    diagnosis,
                    patient,
                    email,
                    thread_id,
                    duplication_result
                )
            )

        for future in as_completed(futures):
            results.append(future.result())

    return results, time.time() - start

