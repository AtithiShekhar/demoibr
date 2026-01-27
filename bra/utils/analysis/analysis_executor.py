

# ================================
# utils/analysis/analysis_executor.py
# ================================

from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.analysis.analysis_worker import analyze_drug_diagnosis
import time


def execute_parallel_analysis(tasks, patient, email, condition_duplication_results, max_workers=4):
    """
    Execute parallel analysis for all drug-diagnosis tasks
    
    Args:
        tasks: List of task dictionaries with 'drug' and 'diagnosis'
        patient: Patient information dictionary
        email: Email for PubMed queries
        condition_duplication_results: Dict mapping diagnosis -> duplication result
        max_workers: Number of parallel workers
    
    Returns:
        Tuple of (results list, elapsed time)
    """
    results = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        for thread_id, task in enumerate(tasks, start=1):
            diagnosis = task["diagnosis"]
            drug = task["drug"]
            
            # Check if this diagnosis has a duplication result
            has_duplication = diagnosis in condition_duplication_results
            
            futures.append(
                executor.submit(
                    analyze_drug_diagnosis,
                    drug,
                    diagnosis,
                    patient,
                    email,
                    thread_id,
                    condition_duplication_results.get(diagnosis),
                    has_duplication
                )
            )

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error in future: {e}")
                results.append({
                    "success": False,
                    "error": str(e)
                })

    return results, time.time() - start

