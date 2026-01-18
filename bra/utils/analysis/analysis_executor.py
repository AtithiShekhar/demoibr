"""
utils/analysis_executor.py
Parallel execution manager for drug-diagnosis analyses
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict
from utils.analysis.analysis_worker import analyze_drug_diagnosis


def execute_parallel_analysis(
    tasks: List[Tuple[str, str]], 
    patient: dict, 
    email: str,
    full_patient_data: dict = None
) -> Tuple[List[dict], float]:
    """
    Execute all drug-diagnosis analyses in parallel
    
    Args:
        tasks: List of (drug, diagnosis) tuples to analyze
        patient: Patient information dictionary
        email: Email for PubMed API
        
    Returns:
        Tuple of (results list, elapsed time)
    """
    start_time = time.time()
    
    # Determine optimal number of threads
    max_workers = min(len(tasks), os.cpu_count() * 2 if os.cpu_count() else 4, 10)
    
    print(f"Using {max_workers} parallel threads for processing...\n")
    
    # Execute analyses in parallel
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(
                analyze_drug_diagnosis, 
                drug, 
                diagnosis, 
                patient, 
                email, 
                idx + 1,
                full_patient_data
            ): (drug, diagnosis)
            for idx, (drug, diagnosis) in enumerate(tasks)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_task):
            drug, diagnosis = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Exception occurred for {drug} - {diagnosis}: {e}")
                results.append({
                    'success': False,
                    'drug': drug,
                    'diagnosis': diagnosis,
                    'error': str(e)
                })
    
    elapsed_time = time.time() - start_time
    return results, elapsed_time


def print_analysis_summary(
    results: List[dict], 
    elapsed_time: float, 
    prescription: list, 
    diagnoses: list
):
    """
    Print summary statistics of analysis results
    
    Args:
        results: List of analysis result dictionaries
        elapsed_time: Total time elapsed
        prescription: List of prescriptions
        diagnoses: List of diagnoses
    """
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"Total prescriptions: {len(prescription)}")
    print(f"Total diagnoses: {len(diagnoses)}")
    print(f"Total analyses performed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    print(f"Average time per analysis: {elapsed_time/len(results):.2f} seconds")
    print(f"Results saved in: ./results/ directory")
    print(f"{'='*80}\n")
    
    # Print summary of scores
    if successful > 0:
        print(f"SCORE SUMMARY:")
        print(f"{'='*80}")
        for result in results:
            if result['success']:
                print(f"{result['drug']} for {result['diagnosis']}: Score = {result['total_score']}")
        print(f"{'='*80}\n")


def create_task_list(prescription: list, diagnoses: list) -> List[Tuple[str, str]]:
    """
    Create list of all drug-diagnosis combinations
    
    Args:
        prescription: List of drugs
        diagnoses: List of diagnoses
        
    Returns:
        List of (drug, diagnosis) tuples
    """
    tasks = []
    for drug in prescription:
        for diagnosis in diagnoses:
            tasks.append((drug, diagnosis))
    return tasks