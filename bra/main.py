"""
main.py
Main orchestrator that analyzes all prescriptions against all diagnosis conditions
"""

from utils.file_loader import load_input
from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from contraindication.app import start as contra_start
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
    """
    return [d.strip() for d in diagnosis_str.split(',')]


def main():
    """Main function orchestrating all components for all drug-condition combinations"""

    # Load input data
    data = load_input()
    if not data:
        return

    patient = data.get("patient", {})
    prescription = data.get("prescription", [])

    diagnosis_str = patient.get("diagnosis", "")
    condition = patient.get("condition", "")
    diagnoses = parse_diagnoses(diagnosis_str)

    if condition and condition not in diagnoses:
        diagnoses.append(condition)

    email = data.get("PubMed", {}).get("email", "your_email@example.com")

    print(f"\n{'='*80}")
    print(f"PATIENT ANALYSIS")
    print(f"{'='*80}")
    print(f"Age: {patient.get('age')}")
    print(f"Gender: {patient.get('gender')}")
    print(f"Diagnoses: {', '.join(diagnoses)}")
    print(f"Prescriptions: {', '.join(prescription)}")
    print(f"Date: {patient.get('date_of_assessment')}")
    print(f"{'='*80}\n")

    os.makedirs("results", exist_ok=True)

    for drug in prescription:
        for diagnosis in diagnoses:
            print(f"\n{'='*80}")
            print(f"ANALYZING: {drug} for {diagnosis}")
            print(f"{'='*80}")

            result_file = f"results/{drug}_{diagnosis.replace(' ', '_').replace('/', '_')}_result.json"
            scoring = ScoringSystem(result_file)

            # ============================================================
            # 1. REGULATORY INDICATION (CDSCO + USFDA)
            # ============================================================
            print("\n=== REGULATORY INDICATION ===")
            regulatory_result = bedrock_start(drug, diagnosis, scoring)
            print(regulatory_result['output'])

            # ============================================================
            # 2. USFDA MARKET EXPERIENCE (MME)
            # ============================================================
            print("\n=== USFDA MARKET EXPERIENCE ===")
            fda_result = fda_start(drug, scoring)
            print(fda_result['output'])

            # ============================================================
            # 3. PUBMED EVIDENCE
            # ============================================================
            print("\n=== PUBMED EVIDENCE ===")
            pubmed_result = pubmed_start(drug, diagnosis, email, scoring)
            print(pubmed_result['output'])

            # ============================================================
            # 4. FDA CONTRAINDICATION ANALYSIS
            # ============================================================
            print("\n=== FDA CONTRAINDICATION CHECK ===")
            # Use the start() pattern we established in contraindication/app.py
            contra_res = contra_start(drug, data, scoring)
            
            print(contra_res['output'])
            if contra_res.get('ibr_text'):
                print(f"iBR: {contra_res['ibr_text']}")

            # ============================================================
            # 5. CALCULATE TOTAL WEIGHTED SCORE
            # ============================================================
            total_weighted_score = 0
            score_breakdown = {}

            # Component mapping for total score calculation
            # 1. Regulatory Indication
            if regulatory_result.get('benefit_score'):
                w = regulatory_result['benefit_score']['weighted_score']
                total_weighted_score += w
                score_breakdown['benefit_factor'] = regulatory_result['benefit_score']

            # 2. Market Experience
            if fda_result.get('mme_score'):
                w = fda_result['mme_score']['weighted_score']
                total_weighted_score += w
                score_breakdown['market_experience'] = fda_result['mme_score']

            # 3. PubMed Evidence
            if pubmed_result.get('evidence_score'):
                w = pubmed_result['evidence_score']['weighted_score']
                total_weighted_score += w
                score_breakdown['pubmed_evidence'] = pubmed_result['evidence_score']

            # 4. Contraindication (New)
            if contra_res.get('contra_score'):
                w = contra_res['contra_score']['weighted_score']
                total_weighted_score += w
                score_breakdown['contraindication_risk'] = contra_res['contra_score']

            # Save the updated results
            output_file = scoring.save_to_json()

            # print(f"\n{'='*80}")
            # print(f"SCORING SUMMARY:")
            # print(f"{'='*80}")
            # print(f"Total Weighted Score: {total_weighted_score}")

            for component, scores in score_breakdown.items():
                print(
                    f"  {component}: {scores['weighted_score']} "
                    f"(Weight: {scores['weight']}, Score: {scores['score']})"
                )

            print(f"\nResults saved to: {output_file}")
            print(f"{'='*80}\n")

    print(f"Results saved in: ./results/ directory")
    print(f"{'='*80}\n")
    return True


if __name__ == "__main__":
    main()