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