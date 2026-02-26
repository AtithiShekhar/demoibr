# ================================
# contraindication/app.py (Patient-Context-Aware)
# CORRECTED VERSION
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

    def extract_patient_conditions(self, patient_data: Dict[str, Any], exclude_diagnosis: str = None) -> Set[str]:
        """
        Extract patient conditions from normalized data structure
        UPDATED: Handles currentDiagnoses, MedicalHistory, and pregnancy
        CORRECTED: Returns concepts as Set, excludes diagnosis being treated
        
        Args:
            patient_data: Full patient data
            exclude_diagnosis: Diagnosis being treated (to exclude from contraindication check)
        
        Returns:
            Set of all patient condition concepts
        """
        all_conditions = []
        
        patient = patient_data.get("patientInfo", {})
        
        # Basic demographics
        age = patient.get("age", 0)
        if age >= 65:
            all_conditions.append("elderly")
        elif age < 18:
            all_conditions.append("pediatric")
        
        # Primary diagnosis
        if patient.get("diagnosis"):
            all_conditions.append(patient["diagnosis"].lower())
        
        # Pregnancy context
        pregnancy_info = patient.get("pregnancy_info", {})
        if pregnancy_info:
            pregnancy_status = pregnancy_info.get("pregnancy_status", "Not Applicable")
            if pregnancy_status == "Ongoing Pregnancy":
                all_conditions.append("pregnancy")
                all_conditions.append("pregnant")
                trimester = pregnancy_info.get("Trimester")
                if trimester:
                    all_conditions.append(f"trimester {trimester}")
            elif pregnancy_status == "Planning":
                all_conditions.append("planning pregnancy")
            
            if pregnancy_info.get("lactation") == "Yes":
                all_conditions.append("lactation")
                all_conditions.append("breastfeeding")
        
        # Current diagnoses
        for diag in patient_data.get("currentDiagnoses", []):
            if diag.get("status") in ["Active", "Severe"]:
                all_conditions.append(diag.get("diagnosisName", "").lower())
        
        # Medical history (active conditions only)
        for history in patient_data.get("MedicalHistory", []):
            if history.get("status") in ["Active", "Chronic"]:
                all_conditions.append(history.get("diagnosisName", "").lower())
        
        # Social risk factors
        if patient.get("social_risk_factors"):
            all_conditions.append(patient["social_risk_factors"].lower())
        
        # Convert all conditions to concepts
        all_concepts = set()
        for condition in all_conditions:
            all_concepts |= normalize_to_concepts(condition)
        
        # Exclude the diagnosis being treated
        if exclude_diagnosis:
            exclude_concepts = normalize_to_concepts(exclude_diagnosis)
            all_concepts -= exclude_concepts
        
        return all_concepts

    def build_patient_context_string(self, patient_data: dict) -> str:
        """
        Build a patient context string for enhanced contraindication analysis
        """
        if "patientInfo" not in patient_data:
            return ""
        
        patient = patient_data["patientInfo"]
        age = patient.get("age", "unknown")
        gender = patient.get("gender", "unknown")
        diagnosis = patient.get("diagnosis", "")
        social_risk = patient.get("social_risk_factors", "")
        
        # Pregnancy context
        pregnancy_info = patient.get("pregnancy_info", {})
        pregnancy_status = pregnancy_info.get("pregnancy_status", "Not Applicable")
        is_pregnant = pregnancy_status == "Ongoing Pregnancy"
        trimester = pregnancy_info.get("Trimester")
        is_lactating = pregnancy_info.get("lactation") == "Yes"
        
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
        
        # Add pregnancy context
        if gender.lower() == "female":
            context += f"\n- Pregnancy Status: {pregnancy_status}"
            if is_pregnant:
                context += f"\n- Trimester: {trimester if trimester else 'Unknown'}"
                context += "\n- ⚠️ PREGNANCY: Check teratogenic potential"
            if is_lactating:
                context += "\n- Lactation: Active"
                context += "\n- ⚠️ LACTATION: Check breast milk excretion"

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
    CORRECTED: Fixed prompt template
    """
    if not gemini_client or not fda_context:
        return f"Based on FDA label documentation, {drug} is contraindicated in patients with {risk.replace('_', ' ').lower()}."

    config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=200,
    )

    # Enhanced prompt with patient context
    patient_section = f"\n\nPATIENT CONTEXT:\n{patient_context}" if patient_context else ""
    
    prompt = f"""You are a clinical pharmacist explaining FDA contraindications.

Drug: {drug}
Condition being treated: {diagnosis}
Contraindication detected: {risk.replace('_', ' ').title()}

FDA Label Context:
{fda_context[:500]}
{patient_section}

Task: Explain in 2-3 sentences why {drug} is contraindicated for this patient, focusing on the {risk.replace('_', ' ').lower()} concern. Use clear clinical language."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
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