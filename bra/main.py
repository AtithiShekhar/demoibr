"""
main.py
Main entry point for Drug Indication Analysis System
Uses centralized scoring configuration
"""

from duplication.checker import start as duplication_start
from utils.analysis.analysis_executor import execute_parallel_analysis
from utils.file_loader import load_input, extract_analysis_tasks
from collections import defaultdict
import os
import json
from datetime import datetime


def main(verbose=True, input_file="input.json", output_summary=True):
    """
    Main analysis pipeline
    
    Args:
        verbose: Print detailed progress information
        input_file: Path to input JSON file
        output_summary: Generate and save summary report
        
    Returns:
        Boolean indicating success/failure
    """
    print(f"\n{'='*80}")
    print(f"DRUG INDICATION ANALYSIS SYSTEM")
    print(f"Using Centralized Scoring Configuration")
    print(f"{'='*80}\n")
    
    # ================================================
    # STEP 1: Load and Validate Input
    # ================================================
    if verbose:
        print(f"[STEP 1] Loading input from: {input_file}")
    
    data = load_input(input_file)
    if not data:
        print(f"❌ Failed to load input file: {input_file}")
        return False
    
    patient = data.get("patientInfo", {})
    email = data.get("PubMed", {}).get("email", "your_email@example.com")
    
    if verbose:
        print(f"✓ Patient: {patient.get('fullName', 'Unknown')}")
        print(f"✓ MRN: {patient.get('mrn', 'Unknown')}")
        print(f"✓ Diagnoses: {len(data.get('currentDiagnoses', []))}")

    # ================================================
    # STEP 2: Extract Analysis Tasks
    # ================================================
    if verbose:
        print(f"\n[STEP 2] Extracting analysis tasks...")
    
    tasks = extract_analysis_tasks(data)
    
    if not tasks:
        print("❌ No analysis tasks generated")
        return False
    
    if verbose:
        print(f"✓ Generated {len(tasks)} drug-diagnosis analysis tasks")
        for task in tasks:
            print(f"  • {task['drug']} → {task['diagnosis']}")

    # ================================================
    # STEP 3: Build Condition → Medicines Mapping
    # ================================================
    if verbose:
        print(f"\n[STEP 3] Building condition-medication mapping...")
    
    condition_meds = defaultdict(list)
    
    for diagnosis in data.get("currentDiagnoses", []):
        condition_name = diagnosis.get("diagnosisName")
        if not condition_name:
            continue
        
        for med in diagnosis.get("treatment", {}).get("medications", []):
            if med.get("name"):
                condition_meds[condition_name].append(med["name"])
    
    if verbose:
        for condition, meds in condition_meds.items():
            print(f"  • {condition}: {len(meds)} medication(s)")

    # ================================================
    # STEP 4: Therapeutic Duplication Analysis
    # ================================================
    if verbose:
        print(f"\n[STEP 4] Running therapeutic duplication analysis...")
    
    condition_duplication_results = {}
    duplication_count = 0
    
    for condition, meds in condition_meds.items():
        if len(meds) >= 2:
            duplication_count += 1
            if verbose:
                print(f"\n  Analyzing: {condition}")
                print(f"  Medications: {', '.join(meds)}")
            
            condition_duplication_results[condition] = duplication_start({
                "prescription": meds
            })
            
            if verbose:
                result = condition_duplication_results[condition]
                score = result.get('duplication_score', {})
                print(f"  Result: {score.get('duplication_category', 'Unknown')}")
                print(f"  Score: {score.get('weighted_score', 0)}")
        else:
            if verbose:
                print(f"  ⊘ Skipping {condition} (only {len(meds)} medication)")
    
    if verbose:
        print(f"\n✓ Completed {duplication_count} duplication checks")

    # ================================================
    # STEP 5: Create Results Directory
    # ================================================
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    
    if verbose:
        print(f"\n[STEP 5] Results directory: {results_dir}/")

    # ================================================
    # STEP 6: Execute Parallel Analysis
    # ================================================
    if verbose:
        print(f"\n[STEP 6] Starting parallel drug-diagnosis analysis...")
        print(f"{'='*80}")
    
    results, elapsed = execute_parallel_analysis(
        tasks=tasks,
        patient=patient,
        email=email,
        condition_duplication_results=condition_duplication_results,
        full_input_data=data  # Pass full input data for contraindication checking
    )

    # ================================================
    # STEP 7: Process Results
    # ================================================
    if verbose:
        print(f"\n{'='*80}")
        print(f"[STEP 7] Processing results...")
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    # Count alternatives found
    alternatives_count = sum(1 for r in successful if r.get('alternatives_found'))
    
    # Calculate total scores
    total_scores = {}
    for result in successful:
        drug = result.get('drug')
        diagnosis = result.get('diagnosis')
        score = result.get('total_score', 0)
        total_scores[f"{drug}_{diagnosis}"] = score

    # ================================================
    # STEP 8: Generate Summary Report
    # ================================================
    if output_summary:
        summary = generate_summary_report(
            patient=patient,
            tasks=tasks,
            results=results,
            successful=successful,
            failed=failed,
            duplication_count=duplication_count,
            alternatives_count=alternatives_count,
            elapsed=elapsed,
            total_scores=total_scores
        )
        
        # Save summary
        summary_file = f"{results_dir}/analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        if verbose:
            print(f"✓ Summary saved to: {summary_file}")

    # ================================================
    # STEP 9: Display Final Summary
    # ================================================
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"Patient: {patient.get('fullName', 'Unknown')} (MRN: {patient.get('mrn', 'Unknown')})")
    print(f"Total Analyses: {len(results)}")
    print(f"  ✓ Successful: {len(successful)}")
    if failed:
        print(f"  ✗ Failed: {len(failed)}")
    print(f"Execution Time: {elapsed:.2f}s")
    print(f"Duplication Checks: {duplication_count}")
    print(f"Alternatives Found: {alternatives_count}")
    print(f"{'='*80}")
    
    if successful:
        print(f"\nTop 5 Highest Risk Medications (by weighted score):")
        sorted_scores = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (key, score) in enumerate(sorted_scores[:5], 1):
            drug_diag = key.replace('_', ' → ', 1)
            print(f"  {i}. {drug_diag}: {score}")
    
    if failed:
        print(f"\n❌ Failed Analyses:")
        for fail in failed:
            print(f"  • {fail.get('drug')} → {fail.get('diagnosis')}: {fail.get('error', 'Unknown error')}")
    
    print(f"\n{'='*80}\n")
    
    return len(failed) == 0


def generate_summary_report(
    patient, tasks, results, successful, failed, 
    duplication_count, alternatives_count, elapsed, total_scores
):
    """
    Generate comprehensive summary report
    
    Returns:
        Dictionary with summary data
    """
    return {
        "metadata": {
            "analysis_timestamp": datetime.now().isoformat(),
            "execution_time_seconds": round(elapsed, 2),
            "system_version": "2.0",
            "scoring_system": "Centralized Configuration"
        },
        "patient_info": {
            "name": patient.get('fullName', 'Unknown'),
            "mrn": patient.get('mrn', 'Unknown'),
            "age": patient.get('age'),
            "gender": patient.get('gender')
        },
        "analysis_summary": {
            "total_tasks": len(tasks),
            "successful": len(successful),
            "failed": len(failed),
            "duplication_checks_performed": duplication_count,
            "alternatives_searches_performed": alternatives_count
        },
        "risk_analysis": {
            "highest_risk_medication": max(total_scores.items(), key=lambda x: x[1])[0] if total_scores else None,
            "highest_risk_score": max(total_scores.values()) if total_scores else 0,
            "lowest_risk_medication": min(total_scores.items(), key=lambda x: x[1])[0] if total_scores else None,
            "lowest_risk_score": min(total_scores.values()) if total_scores else 0,
            "average_risk_score": round(sum(total_scores.values()) / len(total_scores), 2) if total_scores else 0
        },
        "detailed_results": [
            {
                "drug": r.get('drug'),
                "diagnosis": r.get('diagnosis'),
                "success": r.get('success'),
                "total_score": r.get('total_score', 0),
                "rct_count": r.get('rct_count', 0),
                "duplication_checked": r.get('duplication_checked', False),
                "alternatives_found": r.get('alternatives_found', False),
                "output_file": r.get('output_file'),
                "error": r.get('error')
            }
            for r in results
        ],
        "failed_analyses": [
            {
                "drug": f.get('drug'),
                "diagnosis": f.get('diagnosis'),
                "error": f.get('error')
            }
            for f in failed
        ] if failed else []
    }


def run_with_config(config_file="config.json"):
    """
    Run analysis with configuration file
    
    Args:
        config_file: Path to configuration JSON
        
    Example config.json:
    {
        "input_file": "input.json",
        "verbose": true,
        "output_summary": true,
        "email": "your_email@example.com"
    }
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        input_file = config.get('input_file', 'input.json')
        verbose = config.get('verbose', True)
        output_summary = config.get('output_summary', True)
        
        return main(
            verbose=verbose,
            input_file=input_file,
            output_summary=output_summary
        )
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_file}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in configuration file: {config_file}")
        return False


if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--config":
            # Run with config file
            config_file = sys.argv[2] if len(sys.argv) > 2 else "config.json"
            success = run_with_config(config_file)
        elif sys.argv[1] == "--quiet":
            # Run in quiet mode
            success = main(verbose=False)
        elif sys.argv[1] == "--help":
            print("""
Drug Indication Analysis System
================================

Usage:
  python main.py                    # Run with default settings
  python main.py --quiet            # Run without verbose output
  python main.py --config [file]    # Run with configuration file
  python main.py --help             # Show this help message

Configuration File Format (JSON):
{
    "input_file": "input.json",
    "verbose": true,
    "output_summary": true,
    "email": "your_email@example.com"
}

Scoring System:
  - Uses centralized scoring configuration
  - All scoring matrices defined in scoring/config.py
  - Consistent scoring across all analysis modules

For more information, see README.md
            """)
            sys.exit(0)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
            sys.exit(1)
    else:
        # Run with default settings
        success = main()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)