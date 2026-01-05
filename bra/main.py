from utils.file_loader import load_input
from bedrock.query_handler import BedrockDrugChecker, format_bedrock_output
from fda.mme_checker import FDADrugChecker, format_fda_output
from pubmed.searcher import PubMedSearcher, format_pubmed_output

def main():
    data = load_input()
    if not data: return

    drug = data["Drug"]
    condition = data["Condition"]

    # 1. BEDROCK
    bedrock = BedrockDrugChecker()
    context = bedrock.retrieve_docs(drug, condition)
    is_approved = bedrock.generate_answer(drug, condition, context)
    print("\n=== REGULATORY INDICATION ===")
    print(format_bedrock_output(is_approved, drug, condition))

    # 2. FDA
    fda = FDADrugChecker()
    fda_data = fda.search(drug)
    print("\n=== USFDA MARKET EXPERIENCE ===")
    if fda_data:
        print(format_fda_output(fda_data["generic_name"], fda_data["approval_date"], fda_data["years"]))

    # 3. PUBMED (Updated to handle conclusions)
    email = data.get("PubMed", {}).get("email", "your_email@example.com")
    pubmed = PubMedSearcher(email=email)
    rct_count, top_conclusions = pubmed.search(drug, condition)

    print("\n=== PUBMED EVIDENCE ===")
    print(format_pubmed_output(drug, condition, rct_count, top_conclusions))

if __name__ == "__main__":
    main()