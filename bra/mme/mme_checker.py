"""
fda/mme_checker.py
FDA Market Experience Checker Module
"""

import requests
from datetime import datetime
from typing import Optional, Dict


class FDADrugChecker:
    BASE_URL = "https://api.fda.gov/drug/drugsfda.json"
    
    def __init__(self):
        self.session = requests.Session()
    
    def search(self, drug_name: str) -> Optional[Dict]:
        """Automated search: Fetches, filters, and calculates MME"""
        try:
            params = {
                'search': f'products.brand_name:"{drug_name}" products.active_ingredients.name:"{drug_name}"',
                'limit': 50
            }
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            if response.status_code != 200:
                return None
            
            results = response.json().get('results', [])
            return self._process_results(results)
        except Exception:
            return None

    def _process_results(self, results: list) -> Optional[Dict]:
        earliest_date = None
        best_match = None

        for res in results:
            app_num = res.get('application_number', '')
            # Filter: Exclude ANDA, keep NDA/BLA
            if app_num.startswith('ANDA') or not (app_num.startswith('NDA') or app_num.startswith('BLA')):
                continue
            
            # Filter: Check if discontinued
            products = res.get('products', [])
            if all('DISCONTINUED' in p.get('marketing_status', '').upper() for p in products):
                continue
            
            # Extract ORIG submission date
            subs = res.get('submissions', [])
            orig = next((s for s in subs if s.get('submission_type') == 'ORIG'), None)
            date_str = orig.get('submission_status_date') if orig else None
            
            if date_str:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                if earliest_date is None or date_obj < earliest_date:
                    earliest_date = date_obj
                    best_match = {
                        'generic': ', '.join([i.get('name') for p in products for i in p.get('active_ingredients', [])]),
                        'date': date_obj
                    }
        
        if not best_match: return None

        years = int((datetime.now() - best_match['date']).days / 365.25)
        return {
            "generic_name": best_match['generic'],
            "approval_date": best_match['date'].strftime('%d-%b-%Y'),
            "years": years
        }


def format_fda_output(drug: str, approval_date: str, years: int) -> str:
    return (f"{drug} is first approved by USFDA on {approval_date} and first "
            f"approved by CDSCO on [CDSCO approval date not available]. {drug} "
            f"is in the market for more than {years} years of post-market experience.")

def start(drug: str, scoring_system=None) -> dict:
    """
    Main entry point for FDA market experience checking

    Args:
        drug: Medicine name
        scoring_system: Optional scoring system to add results to

    Returns:
        Dictionary with FDA data, formatted output, and market experience score
    """
    fda = FDADrugChecker()
    fda_data = fda.search(drug)

    if fda_data:
        output_text = format_fda_output(
            fda_data["generic_name"],
            fda_data["approval_date"],
            fda_data["years"]
        )

        # -------------------------------
        # Market experience scoring
        # -------------------------------
        if scoring_system:
            from scoring.benefit_factor import get_market_experience_data

            evidence_score = get_market_experience_data(
                years_in_market=fda_data["years"],
                scoring_system=scoring_system
            )
        else:
            evidence_score = None

        return {
            "found": True,
            "generic_name": fda_data["generic_name"],
            "approval_date": fda_data["approval_date"],
            "years": fda_data["years"],
            "output": output_text,
            "evidence_score": evidence_score
        }

    else:
        return {
            "found": False,
            "output": f"No USFDA approval data found for {drug}.",
            "evidence_score": None
        }