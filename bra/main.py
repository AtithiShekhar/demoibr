"""
main.py
Main orchestrator - clean entry point for multithreaded drug-diagnosis analysis
Designed to work with Flask API server
"""

import os
import sys
from utils.file_loader import load_input, parse_diagnoses
from utils.analysis.analysis_executor import (
    create_task_list,
    execute_parallel_analysis,
    print_analysis_summary
)


def main(verbose: bool = True):
    """
    Main function - orchestrates all components with multithreading
    
    Args:
        verbose: If True, print detailed output. If False, minimal output for API mode.
        
    Returns:
        bool: True if successful, False otherwise
    """
    
    try:
        # Load input data
        data = load_input()
        if not data:
            if verbose:
                print("ERROR: Failed to load input data")
            return False
        
        # Extract patient and prescription data
        patient = data.get("patient", {})
        prescription = data.get("prescription", [])
        
        if not prescription:
            if verbose:
                print("ERROR: No prescriptions found in input data")
            return False
        
        diagnosis_str = patient.get("diagnosis", "")
        condition = patient.get("condition", "")
        email = data.get("PubMed", {}).get("email", "your_email@example.com")
        
        # Parse diagnoses
        diagnoses = parse_diagnoses(diagnosis_str)
        if condition and condition not in diagnoses:
            diagnoses.append(condition)
        
        if not diagnoses:
            if verbose:
                print("ERROR: No diagnoses found in input data")
            return False
        
        # Print initial summary
        if verbose:
            print(f"\n{'='*80}")
            print(f"PATIENT ANALYSIS - MULTITHREADED MODE")
            print(f"{'='*80}")
            print(f"Age: {patient.get('age')}")
            print(f"Gender: {patient.get('gender')}")
            print(f"Diagnoses: {', '.join(diagnoses)}")
            print(f"Prescriptions: {', '.join(prescription)}")
            print(f"Date: {patient.get('date_of_assessment')}")
            print(f"{'='*80}")
            print(f"Total analyses to perform: {len(prescription) * len(diagnoses)}")
            print(f"{'='*80}\n")
        
        # Create results directory
        os.makedirs("results", exist_ok=True)
        
        # Create task list
        tasks = create_task_list(prescription, diagnoses)
        
        # Execute parallel analysis
        results, elapsed_time = execute_parallel_analysis(tasks, patient, email)
        
        # Check if any analyses were successful
        successful = sum(1 for r in results if r.get('success', False))
        
        if successful == 0:
            if verbose:
                print("ERROR: All analyses failed")
            return False
        
        # Print summary
        if verbose:
            print_analysis_summary(results, elapsed_time, prescription, diagnoses)
        else:
            # Minimal output for API mode
            print(f"Analysis complete: {successful}/{len(results)} successful in {elapsed_time:.2f}s")
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"CRITICAL ERROR in main(): {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        return False


if __name__ == "__main__":
    # When run directly, use verbose mode
    success = main(verbose=True)
    sys.exit(0 if success else 1)