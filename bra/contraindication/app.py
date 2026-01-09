import requests
from typing import Dict, List, Any, Optional
import os
import time
from scoring.benefit_factor import get_contraindication_data
class ContraindicationAnalyzer:
    def __init__(self):
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"

    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extracts relevant FDA sections (raw text only)"""
        try:
            search_query = f'openfda.generic_name:"{medicine_name}" OR openfda.brand_name:"{medicine_name}"'
            params = {'search': search_query, 'limit': 1}
            if self.fda_api_key: params['api_key'] = self.fda_api_key
            
            response = requests.get(self.fda_base_url, params=params, timeout=15)
            if response.status_code != 200: return None
            
            data = response.json().get('results', [{}])[0]
            return {
                'drug_name': medicine_name,
                'contraindications': self._get_text(data, 'contraindications'),
                'boxed_warning': self._get_text(data, 'boxed_warning'),
                'warnings': self._get_text(data, 'warnings_and_cautions') or self._get_text(data, 'warnings'),
                'pregnancy': self._get_text(data, 'pregnancy') or self._get_text(data, 'teratogenic_effects')
            }
        except Exception: return None

    def _get_text(self, data: Dict, field: str) -> str:
        return "\n".join(data.get(field, []))

    def check_match(self, medicine: str, sections: Dict, patient_data: Dict) -> Dict:
        """Core clinical matching logic"""
        patient = patient_data.get('patient', {})
        conditions = (patient.get('condition', '') + ',' + patient.get('diagnosis', '')).lower().split(',')
        conditions = [c.strip() for c in conditions if c.strip()]
        allergies = [a.lower() for a in patient.get('allergies', [])]
        meds = [m.lower() for m in patient_data.get('prescription', [])]

        # 1. Absolute Contraindications & Allergies
        contra_text = sections.get('contraindications', '').lower()
        for cond in conditions:
            if cond in contra_text:
                return {"status": "absolute", "reason": f"Contraindicated for {cond}", "risk": cond}
        
        for allergy in allergies:
            if medicine.lower() in allergy or allergy in medicine.lower():
                return {"status": "absolute", "reason": "Allergy detected", "risk": "hypersensitivity"}

        # 2. Pregnancy Check
        is_pregnant = any('pregnan' in cond for cond in conditions)
        if is_pregnant:
            preg_text = (sections.get('pregnancy', '') + sections.get('boxed_warning', '')).lower()
            if any(k in preg_text for k in ['contraindicated', 'fetal harm', 'category x', 'avoid']):
                return {"status": "pregnancy_warning", "reason": "High risk in pregnancy", "risk": "pregnancy"}

        # 3. Boxed Warnings
        boxed_text = sections.get('boxed_warning', '').lower()
        for cond in conditions:
            if cond in boxed_text:
                return {"status": "boxed_warning", "reason": f"Boxed warning for {cond}", "risk": cond}

        return {"status": "safe", "reason": "No absolute contraindications found", "risk": None}
def start(drug: str, patient_data: dict, scoring_system=None) -> dict:
    """Main entry point following the system's start() pattern"""
    analyzer = ContraindicationAnalyzer()
    
    sections = analyzer.extract_fda_sections(drug)
    if not sections:
        return {
            "found": False,
            "output": f"No FDA label data found for {drug}.",
            "contra_score": get_contraindication_data("no_data", scoring_system)
        }

    match_result = analyzer.check_match(drug, sections, patient_data)
    score_data = get_contraindication_data(match_result['status'], scoring_system)

    # Generate iBR Text
    ibr_output = ""
    if match_result['status'] != "safe":
        risk = match_result.get('risk', 'current condition')
        ibr_output = (f"Use of {drug} in patients having {risk} will cause more risks than benefits. "
                      f"Hence, use is restricted as per regulatory label documentation.")

    return {
        "found": True,
        "status": match_result['status'],
        "reason": match_result['reason'],
        "output": f"{match_result['reason']}. Weighted Score: {score_data['weighted_score']}",
        "ibr_text": ibr_output,
        "contra_score": score_data
    }