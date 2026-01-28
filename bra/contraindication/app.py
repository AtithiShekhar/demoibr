
# ================================
# contraindication/app.py (COMPLETE REWRITE WITH GEMINI)
# ================================

import requests
import os
from typing import Dict, Any, Optional, Set
from scoring.benefit_factor import get_contraindication_data

# Gemini SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Gemini SDK not available. Install: pip install google-generativeai")


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
print(f'the gemini key is {GEMINI_API_KEY}')
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if (GEMINI_AVAILABLE and GEMINI_API_KEY) else None


def normalize_to_concepts(text: str) -> Set[str]:
    """Extract medical concepts from text"""
    text = text.lower()
    concepts = set()

    # Pregnancy
    if "pregnan" in text:
        concepts.add("PREGNANCY")

    # Heart Failure
    if "heart failure" in text:
        if any(k in text for k in ["acute", "decompensated", "unstable"]):
            concepts.add("HEART_FAILURE_ACUTE")
        else:
            concepts.add("HEART_FAILURE_CHRONIC")

    # Asthma
    if "asthma" in text:
        if any(k in text for k in ["acute", "attack", "exacerbation"]):
            concepts.add("ASTHMA_ACUTE")
        else:
            concepts.add("ASTHMA_CHRONIC")

    # Renal
    if any(k in text for k in ["renal failure", "kidney failure", "ckd", "renal impairment"]):
        concepts.add("RENAL_FAILURE")

    # Hepatic
    if any(k in text for k in ["hepatic", "liver failure", "cirrhosis"]):
        concepts.add("HEPATIC_FAILURE")

    # GI Bleeding
    if any(k in text for k in ["gi bleed", "gastrointestinal bleeding", "peptic ulcer"]):
        concepts.add("GI_BLEED")

    # Hypotension
    if any(k in text for k in ["hypotension", "low blood pressure", "cardiogenic shock"]):
        concepts.add("HYPOTENSION")

    # Bradycardia
    if any(k in text for k in ["bradycardia", "slow heart rate", "heart block"]):
        concepts.add("BRADYCARDIA")

    return concepts


def extract_concepts_from_fda(text: str) -> Set[str]:
    """Extract contraindicated concepts from FDA text"""
    text = text.lower()
    concepts = set()

    # Only extract if explicitly contraindicated
    if "contraindicated" not in text and "contraindication" not in text:
        return concepts

    # Extract the same concepts
    concepts |= normalize_to_concepts(text)
    
    return concepts


class ContraindicationAnalyzer:
    def __init__(self):
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"

    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, str]]:
        """Extract FDA label sections"""
        try:
            query = f'openfda.generic_name:"{medicine_name}" OR openfda.brand_name:"{medicine_name}"'
            params = {"search": query, "limit": 1}
            if self.fda_api_key:
                params["api_key"] = self.fda_api_key

            resp = requests.get(self.fda_base_url, params=params, timeout=15)
            if resp.status_code != 200:
                return None

            data = resp.json().get("results", [{}])[0]
            return {
                "contraindications": "\n".join(data.get("contraindications", [])),
                "boxed_warning": "\n".join(data.get("boxed_warning", [])),
                "warnings": "\n".join(data.get("warnings_and_cautions", []) or data.get("warnings", [])),
                "pregnancy": "\n".join(data.get("pregnancy", []) or data.get("teratogenic_effects", [])),
            }
        except Exception as e:
            print(f"FDA API Error for {medicine_name}: {e}")
            return None

    def extract_patient_concepts(self, patient_data: dict) -> Set[str]:
        """Extract medical concepts from patient data"""
        concepts = set()

        # From diagnoses
        for diag in patient_data.get("currentDiagnoses", []):
            diag_name = diag.get("diagnosisName", "")
            concepts |= normalize_to_concepts(diag_name)

        # From chief complaints
        for complaint in patient_data.get("chiefComplaints", []):
            complaint_text = complaint.get("complaint", "")
            concepts |= normalize_to_concepts(complaint_text)

        # From clinical notes
        notes = patient_data.get("clinicalNotes", {}).get("physicianNotes", "")
        concepts |= normalize_to_concepts(notes)

        return concepts

    def detect(self, drug: str, patient_data: dict) -> Optional[Dict]:
        """Detect contraindications using concept matching"""
        sections = self.extract_fda_sections(drug)
        if not sections:
            print(f"[Contraindication] No FDA data for {drug}")
            return None

        # Extract patient concepts
        patient_concepts = self.extract_patient_concepts(patient_data)
        print(f"[Contraindication] Patient concepts: {patient_concepts}")

        # Extract FDA contraindication concepts
        fda_text = sections.get("contraindications", "") + " " + sections.get("boxed_warning", "")
        fda_concepts = extract_concepts_from_fda(fda_text)
        print(f"[Contraindication] FDA concepts: {fda_concepts}")

        # Find overlap
        overlap = patient_concepts & fda_concepts
        if overlap:
            risk = next(iter(overlap))
            print(f"[Contraindication] ⚠️  MATCH FOUND: {risk}")
            return {
                "status": "absolute",
                "risk": risk,
                "reason": f"Contraindicated in {risk.replace('_', ' ').lower()}",
                "fda_sections": sections,
                "matched_concepts": list(overlap)
            }

        print(f"[Contraindication] ✓ No contraindications found")
        return None

def explain_with_gemini(drug: str, risk: str, fda_context: str) -> str:
    # for m in gemini_client.models.list():
    #  print(m.name, m.supported_generation_methods)
    if not gemini_client or not fda_context:
        return f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."

    # Use a specific configuration for clinical accuracy
    config = types.GenerateContentConfig(
        temperature=0.0,  # Minimize creativity/hallucination
        max_output_tokens=150,
    )

    prompt = f"""You are a clinical pharmacologist.
TASK: Explain the contraindication of {drug} in the context of {risk.replace('_', ' ').lower()}.
SOURCE MATERIAL:
{fda_context[:4000]} 

INSTRUCTIONS:
1. Use ONLY the source material provided.
2. Focus on the physiological mechanism or specific clinical risk.
3. Be concise (2-3 sentences)."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        return response.text.strip()
    except Exception as e:
        # Log error details but return the safe fallback
        print(f"Gemini API Error: {type(e).__name__} - {e}")
        return f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."
    
def start(drug: str, patient_data: dict, scoring_system=None) -> dict:
    """Main contraindication checker entry point"""
    analyzer = ContraindicationAnalyzer()
    result = analyzer.detect(drug, patient_data)

    if not result:
        score_data = get_contraindication_data("safe", scoring_system)
        return {
            "found": True,
            "status": "safe",
            "reason": "No contraindications detected",
            "contra_score": score_data,
            "has_contraindication": False
        }

    # Build FDA context for Gemini
    fda_context = "\n\n".join(
        f"{k.upper()}:\n{v}" for k, v in result["fda_sections"].items() if v
    )

    # Get explanation
    explanation = explain_with_gemini(drug, result["risk"], fda_context)
    
    # Determine status type
    status = result["status"]
    if "PREGNANCY" in result["risk"]:
        status = "pregnancy_warning"
    elif result["fda_sections"].get("boxed_warning"):
        status = "boxed_warning"
    
    score_data = get_contraindication_data(status, scoring_system)

    return {
        "found": True,
        "status": status,
        "risk": result["risk"],
        "reason": result["reason"],
        "clinical_explanation": explanation,
        "matched_conditions": result["matched_concepts"],
        "contra_score": score_data,
        "has_contraindication": True
    }