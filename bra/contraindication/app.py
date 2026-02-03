# ================================
# contraindication/app.py (Patient-Context-Aware)
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
    
    # Transplant/Immunosuppressed
    if any(k in text for k in ["transplant", "immunosuppressed", "immunocompromised", "bone marrow"]):
        concepts.add("IMMUNOSUPPRESSED")
    
    # Leukemia/Cancer
    if any(k in text for k in ["leukemia", "aml", "cancer", "malignancy"]):
        concepts.add("HEMATOLOGIC_MALIGNANCY")

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
        Now supports both formats: new format with currentDiagnoses, and simple format with patient.diagnosis
        
        Args:
            patient_data: Full patient data
            current_diagnosis: The diagnosis for which this drug is prescribed (to exclude)
        """
        concepts = set()

        # NEW FORMAT: From currentDiagnoses array
        for diag in patient_data.get("currentDiagnoses", []):
            diag_name = diag.get("diagnosisName", "")
            
            # Skip the diagnosis being treated - drug should be for this condition
            if current_diagnosis and diag_name.lower() == current_diagnosis.lower():
                continue
                
            concepts |= normalize_to_concepts(diag_name)

        # NEW FORMAT: From chief complaints
        for complaint in patient_data.get("chiefComplaints", []):
            complaint_text = complaint.get("complaint", "")
            concepts |= normalize_to_concepts(complaint_text)

        # NEW FORMAT: From clinical notes
        notes = patient_data.get("clinicalNotes", {}).get("physicianNotes", "")
        concepts |= normalize_to_concepts(notes)

        # SIMPLE FORMAT: From patient.diagnosis (if exists)
        if "patient" in patient_data:
            patient = patient_data["patient"]
            diagnosis_text = patient.get("diagnosis", "")
            
            # Split by commas to handle multiple diagnoses
            diagnoses = [d.strip() for d in diagnosis_text.split(',') if d.strip()]
            for diag in diagnoses:
                # Skip the diagnosis being treated
                if current_diagnosis and diag.lower() == current_diagnosis.lower():
                    continue
                concepts |= normalize_to_concepts(diag)
            
            # Extract from social risk factors
            social_risk = patient.get("social_risk_factors", "")
            concepts |= normalize_to_concepts(social_risk)

        return concepts

    def build_patient_context_string(self, patient_data: dict) -> str:
        """
        Build a patient context string for enhanced contraindication analysis
        """
        if "patient" not in patient_data:
            return ""
        
        patient = patient_data["patient"]
        age = patient.get("age", "unknown")
        gender = patient.get("gender", "unknown")
        diagnosis = patient.get("diagnosis", "")
        social_risk = patient.get("social_risk_factors", "")
        
        # Extract medical history
        medical_history = patient_data.get("MedicalHistory", [])
        active_conditions = []
        previous_medications = []
        severe_conditions = []
        
        for history in medical_history:
            condition_name = history.get("diagnosisName", "")
            status = history.get("status", "")
            severity = history.get("severity", "")
            
            if status == "Active":
                active_conditions.append(condition_name)
                if severity in ["Severe", "Critical"]:
                    severe_conditions.append(f"{condition_name} ({severity})")
            
            # Extract stopped medications (may indicate previous ADRs)
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
        
        context = f"""Patient Profile:
- Age: {age} years ({age_category})
- Gender: {gender}
- Primary Diagnosis: {diagnosis}
- Social Risk Factors: {social_risk}
- Post-Transplant: {'Yes' if is_post_transplant else 'No'}
- Immunosuppressed: {'Yes' if is_immunosuppressed else 'No'}"""

        if active_conditions:
            context += f"\n- Active Comorbidities: {', '.join(active_conditions)}"
        
        if severe_conditions:
            context += f"\n- Severe/Critical Conditions: {', '.join(severe_conditions)}"
        
        if previous_medications:
            context += f"\n- Previously Stopped Medications: {', '.join(set(previous_medications))} (may indicate previous ADRs)"
        
        return context

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
            
            # Build patient context for enhanced explanation
            patient_context = self.build_patient_context_string(patient_data)
            
            return {
                "status": "absolute",
                "risk": risk,
                "reason": f"Contraindicated in {risk.replace('_', ' ').lower()}",
                "fda_sections": sections,
                "matched_concepts": list(overlap),
                "treating_diagnosis": diagnosis,
                "patient_context": patient_context
            }

        print(f"[Contraindication] ✓ No contraindications found for {drug} in treating {diagnosis}")
        return None


def explain_with_gemini(drug: str, risk: str, diagnosis: str, fda_context: str, patient_context: str = "") -> str:
    """
    Generate clinical explanation using Gemini with patient context
    """
    if not gemini_client or not fda_context:
        return f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=200,
    )

    # Enhanced prompt with patient context
    patient_section = f"\n\nPATIENT CONTEXT:\n{patient_context}" if patient_context else ""

    prompt = f"""You are a clinical pharmacologist.
TASK: Explain why {drug} (prescribed for {diagnosis}) is contraindicated in patients with {risk.replace('_', ' ').lower()}.

SOURCE MATERIAL:
{fda_context[:3500]}
{patient_section}

INSTRUCTIONS:
1. Use ONLY the source material provided.
2. Focus on the physiological mechanism or specific clinical risk.
3. If patient context is provided, explain how their specific characteristics (age, immunosuppression, comorbidities) increase the contraindication risk.
4. Be concise (2-4 sentences)."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {type(e).__name__} - {e}")
        base_msg = f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."
        if patient_context and "immunosuppressed" in patient_context.lower():
            base_msg += " This is particularly concerning for immunosuppressed patients."
        return base_msg


def start(drug: str, diagnosis: str, patient_data: dict, scoring_system=None) -> dict:
    """
    Main contraindication checker entry point (patient-context-aware)
    
    Args:
        drug: Medicine name
        diagnosis: Diagnosis for which drug is prescribed
        patient_data: Full patient data (supports both new and simple formats)
        scoring_system: Optional scoring system
        
    Returns:
        Contraindication analysis result with patient context
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

    # Get explanation with patient context
    patient_context = result.get("patient_context", "")
    explanation = explain_with_gemini(drug, result["risk"], diagnosis, fda_context, patient_context)
    
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
        "treating_diagnosis": diagnosis,
        "patient_context_applied": bool(patient_context)
    }