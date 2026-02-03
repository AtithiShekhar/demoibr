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

    def retrieve_contraindication_docs(self, drug: str) -> str:
        """Retrieve contraindication and safety information from Knowledge Base"""
        query = f"Contraindications, warnings, precautions, and safety information for {drug}"
        try:
            response = self.kb_client.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 10,
                        "filter": {"equals": {"key": "drug_name", "value": drug.lower().strip()}}
                    }
                }
            )
            results = response.get("retrievalResults", [])
            return "\n\n".join([r["content"]["text"] for r in results])
        except Exception:
            return ""

    def check_patient_safety(self, drug: str, condition: str, patient_data: dict, context: str) -> Tuple[bool, list]:
        """
        Check if drug is safe for the specific patient based on contraindications
        
        Args:
            drug: Drug name
            condition: Condition being treated
            patient_data: Patient information dict
            context: Contraindication information from knowledge base
            
        Returns:
            Tuple of (is_safe: bool, warnings: list)
        """
        if not context.strip() or not patient_data:
            return True, []
        
        # Build patient context string
        age = patient_data.get("age", "unknown")
        gender = patient_data.get("gender", "unknown")
        diagnosis = patient_data.get("diagnosis", "")
        social_risk = patient_data.get("social_risk_factors", "")
        
        # Extract medical history
        medical_history = patient_data.get("MedicalHistory", [])
        active_conditions = []
        previous_medications = []
        
        for history in medical_history:
            condition_name = history.get("diagnosisName", "")
            status = history.get("status", "")
            severity = history.get("severity", "")
            
            if status == "Active":
                active_conditions.append(f"{condition_name} ({severity})")
            
            # Extract previous medications
            treatment = history.get("treatment", {})
            medications = treatment.get("medications", [])
            for med in medications:
                med_name = med.get("name", "")
                med_status = med.get("status", "")
                if med_name and med_status == "Stopped":
                    previous_medications.append(med_name)
        
        # Determine patient characteristics
        is_post_transplant = "transplant" in diagnosis.lower()
        is_immunosuppressed = is_post_transplant or "immunosuppressed" in diagnosis.lower()
        age_category = "pediatric" if age != "unknown" and age < 18 else ("geriatric" if age != "unknown" and age >= 65 else "adult")
        
        patient_context = f"""Patient Profile:
- Age: {age} years ({age_category})
- Gender: {gender}
- Primary Diagnosis: {diagnosis}
- Social Risk Factors: {social_risk}
- Post-Transplant: {'Yes' if is_post_transplant else 'No'}
- Immunosuppressed: {'Yes' if is_immunosuppressed else 'No'}"""

        if active_conditions:
            patient_context += f"\n- Active Comorbidities: {', '.join(active_conditions)}"
        
        if previous_medications:
            patient_context += f"\n- Previously Stopped Medications: {', '.join(set(previous_medications))}"

        prompt = f"""You are a clinical pharmacology expert. Analyze if {drug} is safe for this specific patient.

{patient_context}

Drug Safety Information:
{context}

Analyze contraindications and respond in JSON format:
{{
    "has_absolute_contraindication": true/false,
    "has_relative_contraindication": true/false,
    "age_appropriate": true/false,
    "transplant_safe": true/false,
    "warnings": ["specific warning 1", "specific warning 2"]
}}

Consider:
1. Age-specific contraindications
2. Gender-specific contraindications
3. Immunosuppressant interactions (for transplant patients)
4. Bone marrow suppression risks (critical for hematologic malignancies)
5. Social risk factor interactions (smoking/alcohol)

Respond ONLY with valid JSON."""

        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            })
            response = self.runtime.invoke_model(modelId=MODEL_ARN, body=body)
            answer = json.loads(response.get("body").read())["content"][0]["text"]
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', answer, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                warnings = []
                
                # Check for absolute contraindication
                if result.get("has_absolute_contraindication"):
                    warnings.append("ABSOLUTE CONTRAINDICATION: This drug is contraindicated for this patient")
                    return False, warnings
                
                # Collect warnings
                if result.get("has_relative_contraindication"):
                    warnings.append("Relative contraindication present - use with extreme caution")
                
                if not result.get("age_appropriate", True):
                    warnings.append(f"Age-related concerns for {age_category} patients")
                
                if is_post_transplant and not result.get("transplant_safe", True):
                    warnings.append("May not be safe for post-transplant/immunosuppressed patients")
                
                warnings.extend(result.get("warnings", []))
                
                return not result.get("has_absolute_contraindication", False), warnings
        
        except Exception:
            pass
        
        return True, ["Unable to verify patient-specific safety"]

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


def format_bedrock_output(cdsco_approved: bool, usfda_approved: bool, drug: str, condition: str, 
                          patient_safe: bool = True, patient_warnings: list = None) -> str:
    """
    Format regulatory approval output
    
    Args:
        cdsco_approved: Whether approved by CDSCO
        usfda_approved: Whether approved by USFDA
        drug: Generic name of medicine
        condition: Indication/condition
        patient_safe: Whether safe for specific patient (optional)
        patient_warnings: List of patient-specific warnings (optional)
        
    Returns:
        Formatted output string
    """
    # Both approved
    if cdsco_approved and usfda_approved:
        approval_msg = (f"{drug} is approved for use in {condition} as per the CDSCO "
               f"(Indian health regulatory body) and also as per USFDA's USPI "
               f"(United States Prescriber information).")
    
    # Only CDSCO approved
    elif cdsco_approved and not usfda_approved:
        approval_msg = (f"{drug} is approved for use in {condition} as per the CDSCO "
               f"(Indian health regulatory body) but not as per USFDA's USPI "
               f"(United States Prescriber information).")
    
    # Only USFDA approved
    elif not cdsco_approved and usfda_approved:
        approval_msg = (f"{drug} is approved for use in {condition} as per USFDA's USPI "
               f"(United States Prescriber information) but not as per the CDSCO "
               f"(Indian health regulatory body).")
    
    # Neither approved (off-label)
    else:
        approval_msg = (f"{drug} is not approved for use in {condition} as per the CDSCO "
               f"(Indian health regulatory body) and also as per USFDA's USPI "
               f"(United States Prescriber information). Please review the iBR score "
               f"and consider alternative medications that are approved by regulatory "
               f"bodies for treating {condition}.")
    
    # Add patient safety information if provided
    if patient_warnings is not None:
        if not patient_safe:
            safety_msg = (f"\n\n⚠️ PATIENT SAFETY ALERT: {drug} has contraindications "
                         f"for this patient profile. This medication should NOT be used.")
        elif patient_warnings:
            safety_msg = (f"\n\n⚠️ PATIENT SAFETY WARNINGS for {drug}:\n" + 
                         "\n".join([f"• {w}" for w in patient_warnings]))
        else:
            safety_msg = (f"\n\n✓ No specific contraindications identified for this "
                         f"patient profile based on available data.")
        
        return approval_msg + safety_msg
    
    return approval_msg


def start(drug: str, condition: str, scoring_system=None, patient_data: dict = None) -> dict:
    """
    Main entry point for regulatory approval checking (CDSCO + USFDA)

    Args:
        drug: Generic name of medicine
        condition: Indication / disease
        scoring_system: Optional scoring system to add results to
        patient_data: Optional patient context dict with keys: age, gender, diagnosis, social_risk_factors

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

    # -------------------------------
    # Patient safety check (if patient_data provided)
    # -------------------------------
    patient_safe = True
    patient_warnings = None
    
    if patient_data:
        contraindication_context = checker.retrieve_contraindication_docs(drug)
        patient_safe, patient_warnings = checker.check_patient_safety(
            drug=drug,
            condition=condition,
            patient_data=patient_data,
            context=contraindication_context
        )

    output_text = format_bedrock_output(
        cdsco_approved=cdsco_approved,
        usfda_approved=usfda_approved,
        drug=drug,
        condition=condition,
        patient_safe=patient_safe,
        patient_warnings=patient_warnings
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

    # Build return dictionary (maintain original structure + add patient safety fields)
    result = {
        "drug": drug,
        "condition": condition,
        "cdsco_approved": cdsco_approved,
        "usfda_approved": usfda_approved,
        "output": output_text,
        "evidence_score": evidence_score
    }
    
    # Add patient safety fields only if patient_data was provided
    if patient_data:
        result["patient_safe"] = patient_safe
        result["patient_warnings"] = patient_warnings if patient_warnings else []
    
    return result