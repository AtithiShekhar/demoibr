"""
main.py
Main orchestrator that calls all components and calculates benefit scores
"""

from utils.file_loader import load_input
from approvalstatus.app import BedrockDrugChecker, format_bedrock_output
from mme.mme_checker import FDADrugChecker, format_fda_output
from pubmed.searcher import PubMedSearcher, format_pubmed_output
from scoring.benefit_factor import format_benefit_score, get_benefit_factor_data


def main():
    """Main function orchestrating all components"""
    
    # Load input data
    data = load_input()
    if not data: 
        return

    drug = data["Drug"]
    condition = data["Condition"]

    print(f"\n{'='*80}")
    print(f"ANALYZING: {drug} for {condition}")
    print(f"{'='*80}")

    # ============================================================
    # 1. REGULATORY INDICATION (CDSCO + USFDA)
    # ============================================================
    print("\n=== REGULATORY INDICATION ===")
    bedrock = BedrockDrugChecker()
    context = bedrock.retrieve_docs(drug, condition)
    cdsco_approved, usfda_approved = bedrock.generate_answer(drug, condition, context)
    print(format_bedrock_output(cdsco_approved, usfda_approved, drug, condition))

    # ============================================================
    # 2. BENEFIT FACTOR SCORE
    # ============================================================
    print("\n=== BENEFIT FACTOR SCORE ===")
    print(format_benefit_score(cdsco_approved, usfda_approved, format_type="table"))
    
    # Get benefit factor data for further calculations
    benefit_data = get_benefit_factor_data(cdsco_approved, usfda_approved)
    weighted_score = benefit_data['weighted_score']
    print(f"\nWeighted Score: {weighted_score:.2f}")

    # ============================================================
    # 3. USFDA MARKET EXPERIENCE (MME)
    # ============================================================
    print("\n=== USFDA MARKET EXPERIENCE ===")
    fda = FDADrugChecker()
    fda_data = fda.search(drug)
    if fda_data:
        print(format_fda_output(fda_data["generic_name"], fda_data["approval_date"], fda_data["years"]))
    else:
        print(f"No USFDA approval data found for {drug}.")

    # ============================================================
    # 4. PUBMED EVIDENCE (RCTs and Meta-analyses)
    # ============================================================
    print("\n=== PUBMED EVIDENCE ===")
    email = data.get("PubMed", {}).get("email", "your_email@example.com")
    pubmed = PubMedSearcher(email=email)
    rct_count, top_conclusions = pubmed.search(drug, condition)
    print(format_pubmed_output(drug, condition, rct_count, top_conclusions))

    # ============================================================
    # 5. SUMMARY
    # ============================================================
    print(f"\n{'='*80}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*80}")
    print(f"Drug: {drug}")
    print(f"Condition: {condition}")
    print(f"CDSCO Approved: {'Yes' if cdsco_approved else 'No'}")
    print(f"USFDA Approved: {'Yes' if usfda_approved else 'No'}")
    print(f"Benefit Weight: {benefit_data['weight']}")
    print(f"Benefit Score: {benefit_data['score']}")
    print(f"Weighted Benefit Score: {weighted_score:.2f}")
    if fda_data:
        print(f"Market Experience: {fda_data['years']} years")
    print(f"RCT Count: {rct_count}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()