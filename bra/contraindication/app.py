

# ================================
# contraindication/app.py
# ================================

import requests
from typing import Dict, Any, Optional
import os
from scoring.benefit_factor import get_contraindication_data


class ContraindicationAnalyzer:
    def __init__(self):
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"

    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extracts relevant FDA sections"""
        try:
            search_query = f'openfda.generic_name:"{medicine_name}" OR openfda.brand_name:"{medicine_name}"'
            params = {'search': search_query, 'limit': 1}
            if self.fda_api_key: 
                params['api_key'] = self.fda_api_key
            
            response = requests.get(self.fda_base_url, params=params, timeout=15)
            if response.status_code != 200: 
                return None
            
            data = response.json().get('results', [{}])[0]
            return {
                'drug_name': medicine_name,
                'contraindications': self._get_text(data, 'contraindications'),
                'boxed_warning': self._get_text(data, 'boxed_warning'),
                'warnings': self._get_text(data, 'warnings_and_cautions') or self._get_text(data, 'warnings'),
                'pregnancy': self._get_text(data, 'pregnancy') or self._get_text(data, 'teratogenic_effects')
            }
        except Exception: 
            return None

    def _get_text(self, data: Dict, field: str) -> str:
        return "\n".join(data.get(field, []))

    def check_match(self, medicine: str, sections: Dict, patient_data: Dict) -> Dict:
        """Core clinical matching logic - Updated for EMR format"""
        # Handle both old format (patient dict) and new EMR format
        patient = patient_data.get('patient', patient_data)
        
        # Extract conditions from multiple sources
        conditions = []
        
        # Old format support
        if 'condition' in patient:
            conditions.extend(patient.get('condition', '').lower().split(','))
        if 'diagnosis' in patient:
            conditions.extend(patient.get('diagnosis', '').lower().split(','))
        
        # NEW: Extract from currentDiagnoses (EMR format)
        current_diagnoses = patient_data.get('currentDiagnoses', [])
        for diag in current_diagnoses:
            diag_name = diag.get('diagnosisName', '').lower()
            if diag_name:
                conditions.append(diag_name)
        
        # NEW: Extract from chiefComplaints (EMR format)
        chief_complaints = patient_data.get('chiefComplaints', [])
        for complaint in chief_complaints:
            complaint_text = complaint.get('complaint', '').lower()
            if complaint_text:
                conditions.append(complaint_text)
        
        # Clean up conditions list
        conditions = [c.strip() for c in conditions if c.strip()]
        
        # Extract allergies
        allergies = [a.lower() for a in patient.get('allergies', [])]

        print(f"[Contraindication Check] Drug: {medicine}")
        print(f"[Contraindication Check] Conditions found: {conditions}")

        # 1. Absolute Contraindications & Allergies
        contra_text = sections.get('contraindications', '').lower()
        for cond in conditions:
            if cond and cond in contra_text:
                print(f"[Contraindication Check] ⚠️ FOUND in contraindications: {cond}")
                return {"status": "absolute", "reason": f"Contraindicated for {cond}", "risk": cond}
        
        for allergy in allergies:
            if medicine.lower() in allergy or allergy in medicine.lower():
                print(f"[Contraindication Check] ⚠️ ALLERGY detected")
                return {"status": "absolute", "reason": "Allergy detected", "risk": "hypersensitivity"}

        # 2. Pregnancy Check
        is_pregnant = any('pregnan' in cond for cond in conditions)
        print(f"[Contraindication Check] Pregnancy detected: {is_pregnant}")
        
        if is_pregnant:
            preg_text = (sections.get('pregnancy', '') + sections.get('boxed_warning', '')).lower()
            print(f"[Contraindication Check] Pregnancy text length: {len(preg_text)}")
            
            # Check for pregnancy contraindication keywords
            pregnancy_keywords = ['contraindicated', 'fetal harm', 'category x', 'avoid', 
                                 'teratogenic', 'birth defects', 'pregnancy category d']
            
            for keyword in pregnancy_keywords:
                if keyword in preg_text:
                    print(f"[Contraindication Check] ⚠️ PREGNANCY WARNING found: {keyword}")
                    return {"status": "pregnancy_warning", 
                           "reason": f"Contraindicated in pregnancy ({keyword})", 
                           "risk": "pregnancy"}

        # 3. Boxed Warnings
        boxed_text = sections.get('boxed_warning', '').lower()
        for cond in conditions:
            if cond and cond in boxed_text:
                print(f"[Contraindication Check] ⚠️ BOXED WARNING for: {cond}")
                return {"status": "boxed_warning", "reason": f"Boxed warning for {cond}", "risk": cond}

        print(f"[Contraindication Check] ✓ No contraindications found")
        return {"status": "safe", "reason": "No absolute contraindications found", "risk": None}


def start(drug: str, patient_data: dict, scoring_system=None) -> dict:
    """Main entry point"""
    analyzer = ContraindicationAnalyzer()
    
    sections = analyzer.extract_fda_sections(drug)
    if not sections:
        score_data = get_contraindication_data("no_data", scoring_system)
        return {
            "found": False,
            "output": f"No FDA label data found for {drug}.",
            "contra_score": score_data,
            "has_contraindication": False
        }

    match_result = analyzer.check_match(drug, sections, patient_data)
    score_data = get_contraindication_data(match_result['status'], scoring_system)

    # Determine if contraindication exists
    has_contraindication = match_result['status'] in ['absolute', 'boxed_warning', 'pregnancy_warning']

    # Generate iBR Text
    ibr_output = ""
    if has_contraindication:
        risk = match_result.get('risk', 'current condition')
        ibr_output = (f"Use of {drug} in patients having {risk} will cause more risks than benefits. "
                      f"Hence, use is restricted as per regulatory label documentation.")

    return {
        "found": True,
        "status": match_result['status'],
        "reason": match_result['reason'],
        "output": f"{match_result['reason']}. Weighted Score: {score_data['weighted_score']}",
        "ibr_text": ibr_output,
        "contra_score": score_data,
        "has_contraindication": has_contraindication
    }