# ================================
# contraindication/app.py (FIXED)
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
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if (GEMINI_AVAILABLE and GEMINI_API_KEY) else None


def normalize_to_concepts(text: str) -> Set[str]:
    """Extract medical concepts from text"""
    text = text.lower()
    concepts = set()

    # Pregnancy
    if any(k in text for k in ["pregnan", "gestation", "expecting", "gravid"]):
        concepts.add("PREGNANCY")

    # Heart Failure
    if any(k in text for k in ["heart failure", "cardiac failure", "chf", "congestive heart"]):
        if any(k in text for k in ["acute", "decompensated", "unstable", "severe"]):
            concepts.add("HEART_FAILURE_ACUTE")
        concepts.add("HEART_FAILURE")

    # Asthma
    if "asthma" in text:
        if any(k in text for k in ["acute", "attack", "exacerbation", "severe"]):
            concepts.add("ASTHMA_ACUTE")
        concepts.add("ASTHMA")

    # Renal
    if any(k in text for k in ["renal failure", "kidney failure", "ckd", "renal impairment", "kidney disease", "nephropathy"]):
        concepts.add("RENAL_FAILURE")

    # Hepatic
    if any(k in text for k in ["hepatic", "liver failure", "cirrhosis", "liver disease", "hepatitis"]):
        concepts.add("HEPATIC_FAILURE")

    # GI Bleeding
    if any(k in text for k in ["gi bleed", "gastrointestinal bleeding", "peptic ulcer", "gastric ulcer", "stomach bleeding"]):
        concepts.add("GI_BLEED")

    # Hypotension
    if any(k in text for k in ["hypotension", "low blood pressure", "cardiogenic shock", "shock"]):
        concepts.add("HYPOTENSION")

    # Bradycardia
    if any(k in text for k in ["bradycardia", "slow heart rate", "heart block", "av block"]):
        concepts.add("BRADYCARDIA")
    
    # Hypertension
    if any(k in text for k in ["hypertension", "high blood pressure", "htn"]):
        concepts.add("HYPERTENSION")
    
    # Diabetes
    if any(k in text for k in ["diabetes", "diabetic", "hyperglycemia", "dm"]):
        concepts.add("DIABETES")
    
    # Stroke
    if any(k in text for k in ["stroke", "cerebrovascular", "cva"]):
        concepts.add("STROKE")
    
    # Myocardial Infarction
    if any(k in text for k in ["myocardial infarction", "heart attack", "mi", "acute coronary"]):
        concepts.add("MYOCARDIAL_INFARCTION")
    
    # Arrhythmia
    if any(k in text for k in ["arrhythmia", "atrial fibrillation", "afib", "ventricular tachycardia"]):
        concepts.add("ARRHYTHMIA")

    # COPD
    if any(k in text for k in ["copd", "chronic obstructive", "emphysema", "chronic bronchitis"]):
        concepts.add("COPD")
    
    # Seizure
    if any(k in text for k in ["seizure", "epilepsy", "convulsion"]):
        concepts.add("SEIZURE")
    
    # Depression
    if any(k in text for k in ["depression", "depressive disorder", "mdd"]):
        concepts.add("DEPRESSION")
    
    # Glaucoma
    if "glaucoma" in text:
        concepts.add("GLAUCOMA")

    return concepts


def extract_contraindication_concepts(text: str) -> Set[str]:
    """
    Extract contraindicated conditions from FDA label text
    ONLY from sections explicitly marked as contraindications
    """
    text = text.lower()
    concepts = set()

    # Must contain contraindication keywords
    if not any(k in text for k in ["contraindicated", "contraindication", "should not be used"]):
        return concepts

    # Extract concepts from contraindication context
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

    def extract_patient_conditions(self, patient_data: dict, current_diagnosis: str = None) -> Set[str]:
        """
        Extract patient's medical conditions EXCLUDING the diagnosis being treated
        
        Args:
            patient_data: Full patient data
            current_diagnosis: The diagnosis for which this drug is prescribed (to exclude)
        """
        concepts = set()

        # From diagnoses (EXCLUDING current diagnosis being treated)
        for diag in patient_data.get("currentDiagnoses", []):
            diag_name = diag.get("diagnosisName", "")
            
            # Skip the diagnosis being treated - drug should be for this condition
            if current_diagnosis and diag_name.lower() == current_diagnosis.lower():
                continue
                
            concepts |= normalize_to_concepts(diag_name)

        # From chief complaints
        for complaint in patient_data.get("chiefComplaints", []):
            complaint_text = complaint.get("complaint", "")
            concepts |= normalize_to_concepts(complaint_text)

        # From clinical notes
        notes = patient_data.get("clinicalNotes", {}).get("physicianNotes", "")
        concepts |= normalize_to_concepts(notes)

        return concepts

    def detect(self, drug: str, diagnosis: str, patient_data: dict) -> Optional[Dict]:
        """
        Detect contraindications for drug based on patient's OTHER conditions
        
        Args:
            drug: Medicine name
            diagnosis: Diagnosis for which drug is prescribed
            patient_data: Full patient data
            
        Returns:
            Contraindication details if found, None otherwise
        """
        sections = self.extract_fda_sections(drug)
        if not sections:
            print(f"[Contraindication] No FDA data for {drug}")
            return None

        # Extract patient concepts EXCLUDING the diagnosis being treated
        patient_concepts = self.extract_patient_conditions(patient_data, diagnosis)
        print(f"[Contraindication] Patient other conditions: {patient_concepts}")
        print(f"[Contraindication] Treating diagnosis: {diagnosis} (excluded from contraindication check)")

        # Extract FDA contraindication concepts
        fda_text = sections.get("contraindications", "") + " " + sections.get("boxed_warning", "")
        fda_concepts = extract_contraindication_concepts(fda_text)
        print(f"[Contraindication] FDA contraindicated conditions: {fda_concepts}")

        # Find overlap between patient's other conditions and drug contraindications
        overlap = patient_concepts & fda_concepts
        if overlap:
            risk = next(iter(overlap))
            print(f"[Contraindication] ⚠️  CONTRAINDICATION DETECTED: {risk}")
            print(f"[Contraindication] Drug {drug} is contraindicated in {risk}, which patient has")
            return {
                "status": "absolute",
                "risk": risk,
                "reason": f"Contraindicated in {risk.replace('_', ' ').lower()}",
                "fda_sections": sections,
                "matched_concepts": list(overlap),
                "treating_diagnosis": diagnosis
            }

        print(f"[Contraindication] ✓ No contraindications found for {drug} in treating {diagnosis}")
        return None


def explain_with_gemini(drug: str, risk: str, diagnosis: str, fda_context: str) -> str:
    """Generate clinical explanation using Gemini"""
    if not gemini_client or not fda_context:
        return f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=150,
    )

    prompt = f"""You are a clinical pharmacologist.
TASK: Explain why {drug} (prescribed for {diagnosis}) is contraindicated in patients with {risk.replace('_', ' ').lower()}.
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
        print(f"Gemini API Error: {type(e).__name__} - {e}")
        return f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."


def start(drug: str, diagnosis: str, patient_data: dict, scoring_system=None) -> dict:
    """
    Main contraindication checker entry point
    
    Args:
        drug: Medicine name
        diagnosis: Diagnosis for which drug is prescribed
        patient_data: Full patient data
        scoring_system: Optional scoring system
        
    Returns:
        Contraindication analysis result
    """
    analyzer = ContraindicationAnalyzer()
    result = analyzer.detect(drug, diagnosis, patient_data)

    if not result:
        score_data = get_contraindication_data("safe", scoring_system)
        return {
            "found": False,
            "status": "safe",
            "reason": "No contraindications detected",
            "contra_score": score_data,
            "has_contraindication": False,
            "treating_diagnosis": diagnosis
        }

    # Build FDA context for Gemini
    fda_context = "\n\n".join(
        f"{k.upper()}:\n{v}" for k, v in result["fda_sections"].items() if v
    )

    # Get explanation
    explanation = explain_with_gemini(drug, result["risk"], diagnosis, fda_context)
    
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
        "has_contraindication": True,
        "treating_diagnosis": diagnosis
    }