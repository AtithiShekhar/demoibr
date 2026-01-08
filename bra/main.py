"""
main.py
Main orchestrator that analyzes all prescriptions against all diagnosis conditions
"""

from utils.file_loader import load_input
from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from scoring.benefit_factor import (
    ScoringSystem,
    get_benefit_factor_data,
    get_market_experience_data,
    get_pubmed_evidence_data
)
import json
import os


def parse_diagnoses(diagnosis_str: str) -> list:
    """
    Parse comma-separated diagnosis string into list
    
    Args:
        diagnosis_str: Comma-separated diagnosis string
        
    Returns:
        List of individual diagnoses
    """
    return [d.strip() for d in diagnosis_str.split(',')]


def main():
    """Main function orchestrating all components for all drug-condition combinations"""
    
    # Load input data
    data = load_input()
    if not data: 
        return

    # Extract patient and prescription data
    patient = data.get("patient", {})
    prescription = data.get("prescription", [])
    
    # Parse diagnoses
    diagnosis_str = patient.get("diagnosis", "")
    condition = patient.get("condition", "")
    diagnoses = parse_diagnoses(diagnosis_str)
    
    # Add main condition if not in diagnoses
    if condition and condition not in diagnoses:
        diagnoses.append(condition)
    
    # Get email for PubMed
    email = data.get("PubMed", {}).get("email", "your_email@example.com")
    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Analyze each drug against each diagnosis
    for drug in prescription:
        for diagnosis in diagnoses:
            print(f"\n{'='*80}")
            print(f"ANALYZING: {drug} for {diagnosis}")
            print(f"{'='*80}")
            
            # Initialize scoring system for this drug-diagnosis combination
            result_file = f"results/{drug}_{diagnosis.replace(' ', '_')}_result.json"
            scoring = ScoringSystem(result_file)
            
            # ============================================================
            # 1. REGULATORY INDICATION (CDSCO + USFDA)
            # ============================================================
            print("\n=== REGULATORY INDICATION ===")
            regulatory_result = bedrock_start(drug, diagnosis, scoring)
            print(regulatory_result['output'])
            
            # Add benefit factor score
            get_benefit_factor_data(
                regulatory_result['cdsco_approved'],
                regulatory_result['usfda_approved'],
                scoring
            )
            
            # ============================================================
            # 2. USFDA MARKET EXPERIENCE (MME)
            # ============================================================
            print("\n=== USFDA MARKET EXPERIENCE ===")
            fda_result = fda_start(drug, scoring)
            print(fda_result['output'])
            
            # Add market experience score if data found
            if fda_result['found']:
                get_market_experience_data(fda_result['years'], scoring)
            
            # ============================================================
            # 3. PUBMED EVIDENCE (RCTs and Meta-analyses)
            # ============================================================
            print("\n=== PUBMED EVIDENCE ===")
            pubmed_result = pubmed_start(drug, diagnosis, email, scoring)
            print(pubmed_result['output'])
            
            # Add PubMed evidence score
            get_pubmed_evidence_data(pubmed_result['rct_count'], scoring)
            
            # ============================================================
            # 4. SAVE RESULTS
            # ============================================================
            # Add raw analysis data to scoring system
            scoring.add_analysis("raw_data", {
                "drug": drug,
                "diagnosis": diagnosis,
                "patient_info": patient,
                "regulatory": regulatory_result,
                "market_experience": fda_result if fda_result['found'] else None,
                "pubmed_evidence": {
                    "rct_count": pubmed_result['rct_count'],
                    "top_conclusions": pubmed_result['conclusions']
                }
            })
            
            output_file = scoring.save_to_json()
            print(f"\n{'='*80}")
            print(f"Results saved to: {output_file}")
            print(f"{'='*80}\n")
    
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"Total prescriptions analyzed: {len(prescription)}")
    print(f"Total diagnoses evaluated: {len(diagnoses)}")
    print(f"Total analyses performed: {len(prescription) * len(diagnoses)}")
    print(f"Results saved in: ./results/ directory")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()