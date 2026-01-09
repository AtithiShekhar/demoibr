"""
approvalstatus/app.py
Regulatory approval checker combining CDSCO (Bedrock) and USFDA (OpenFDA)
"""

import json
import boto3
import requests
import re
from typing import Tuple

# ===============================
# CONFIGURATION
# ===============================
REGION = "ap-south-1"
KNOWLEDGE_BASE_ID = "R1JBPOUITW"
MODEL_ARN = "arn:aws:bedrock:ap-south-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"


class BedrockDrugChecker:
    """Check CDSCO approval using AWS Bedrock Knowledge Base"""
    
    def __init__(self):
        self.kb_client = boto3.client("bedrock-agent-runtime", region_name=REGION)
        self.runtime = boto3.client("bedrock-runtime", region_name=REGION)
        self.usfda_checker = USFDAChecker()

    def retrieve_docs(self, drug: str, condition: str) -> str:
        """Retrieve documents from Knowledge Base for CDSCO"""
        query = f"Indications for {drug}. Is {condition} an indication?"
        try:
            response = self.kb_client.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5,
                        "filter": {"equals": {"key": "drug_name", "value": drug.lower().strip()}}
                    }
                }
            )
            results = response.get("retrievalResults", [])
            return "\n\n".join([r["content"]["text"] for r in results])
        except Exception:
            return ""

    def generate_answer(self, drug: str, condition: str, context: str) -> Tuple[bool, bool]:
        """
        Generate approval status for both CDSCO and USFDA
        
        Returns:
            Tuple of (cdsco_approved, usfda_approved)
        """
        # Check CDSCO approval
        cdsco_approved = False
        if context.strip():
            prompt = f"""Based on the following medical information about {drug}, determine if {condition} is a described indication.
Context: {context}
Answer ONLY with "Yes" or "No"."""

            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 10,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
                })
                response = self.runtime.invoke_model(modelId=MODEL_ARN, body=body)
                answer = json.loads(response.get("body").read())["content"][0]["text"].lower()
                cdsco_approved = "yes" in answer
            except Exception:
                cdsco_approved = False
        
        # Check USFDA approval
        usfda_approved = self.usfda_checker.check_indication(drug, condition)
        
        return cdsco_approved, usfda_approved


class USFDAChecker:
    """Check USFDA approval using OpenFDA API"""
    
    LABEL_URL = "https://api.fda.gov/drug/label.json"
    
    def __init__(self):
        self.session = requests.Session()
    
    def search_drug_label(self, drug_name: str) -> dict:
        """Search FDA drug labels"""
        try:
            params = {
                'search': f'openfda.brand_name:"{drug_name}" openfda.generic_name:"{drug_name}"',
                'limit': 100
            }
            response = self.session.get(self.LABEL_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}
    
    def clean_text(self, text: str) -> str:
        """Clean HTML tags and whitespace"""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_indications(self, results: dict) -> list:
        """Extract indication texts from FDA labels"""
        if not results or 'results' not in results:
            return []
        
        indications = []
        for result in results['results']:
            fields = ['indications_and_usage', 'purpose', 'use', 'when_using']
            for field in fields:
                if field in result:
                    text = result[field]
                    if isinstance(text, list):
                        for t in text:
                            cleaned = self.clean_text(t)
                            if cleaned:
                                indications.append(cleaned)
                    else:
                        cleaned = self.clean_text(text)
                        if cleaned:
                            indications.append(cleaned)
        return indications
    
    def fuzzy_match(self, indication: str, text: str) -> bool:
        """Check if indication is mentioned in text"""
        indication_lower = indication.lower()
        text_lower = text.lower()
        
        if indication_lower in text_lower:
            return True
        
        words = indication_lower.split()
        if len(words) > 1:
            if all(word in text_lower for word in words):
                return True
        
        return False
    
    def check_indication(self, drug: str, condition: str) -> bool:
        """Check if drug is approved for condition in USFDA"""
        results = self.search_drug_label(drug)
        indications = self.extract_indications(results)
        
        if not indications:
            return False
        
        for ind_text in indications:
            if self.fuzzy_match(condition, ind_text):
                return True
        
        return False


def format_bedrock_output(cdsco_approved: bool, usfda_approved: bool, drug: str, condition: str) -> str:
    """
    Format regulatory approval output
    
    Args:
        cdsco_approved: Whether approved by CDSCO
        usfda_approved: Whether approved by USFDA
        drug: Generic name of medicine
        condition: Indication/condition
        
    Returns:
        Formatted output string
    """
    # Both approved
    if cdsco_approved and usfda_approved:
        return (f"{drug} is approved for use in {condition} as per the CDSCO "
               f"(Indian health regulatory body) and also as per USFDA's USPI "
               f"(United States Prescriber information).")
    
    # Only CDSCO approved
    elif cdsco_approved and not usfda_approved:
        return (f"{drug} is approved for use in {condition} as per the CDSCO "
               f"(Indian health regulatory body) but not as per USFDA's USPI "
               f"(United States Prescriber information).")
    
    # Only USFDA approved
    elif not cdsco_approved and usfda_approved:
        return (f"{drug} is approved for use in {condition} as per USFDA's USPI "
               f"(United States Prescriber information) but not as per the CDSCO "
               f"(Indian health regulatory body).")
    
    # Neither approved (off-label)
    else:
        return (f"{drug} is not approved for use in {condition} as per the CDSCO "
               f"(Indian health regulatory body) and also as per USFDA's USPI "
               f"(United States Prescriber information). Please review the iBR score "
               f"and consider alternative medications that are approved by regulatory "
               f"bodies for treating {condition}.")
def start(drug: str, condition: str, scoring_system=None) -> dict:
    """
    Main entry point for regulatory approval checking (CDSCO + USFDA)

    Args:
        drug: Generic name of medicine
        condition: Indication / disease
        scoring_system: Optional scoring system to add results to

    Returns:
        Dictionary with approval status, formatted output, and benefit factor score
    """
    checker = BedrockDrugChecker()

    # -------------------------------
    # Regulatory approval check
    # -------------------------------
    context = checker.retrieve_docs(drug, condition)

    cdsco_approved, usfda_approved = checker.generate_answer(
        drug=drug,
        condition=condition,
        context=context
    )

    output_text = format_bedrock_output(
        cdsco_approved=cdsco_approved,
        usfda_approved=usfda_approved,
        drug=drug,
        condition=condition
    )

    # -------------------------------
    # Benefit factor scoring
    # -------------------------------
    if scoring_system:
        from scoring.benefit_factor import get_benefit_factor_data

        evidence_score = get_benefit_factor_data(
            cdsco_approved=cdsco_approved,
            usfda_approved=usfda_approved,
            scoring_system=scoring_system
        )
    else:
        evidence_score = None

    return {
        "drug": drug,
        "condition": condition,
        "cdsco_approved": cdsco_approved,
        "usfda_approved": usfda_approved,
        "output": output_text,
        "evidence_score": evidence_score
    }