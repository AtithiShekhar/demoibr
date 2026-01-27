# ================================
# alternatives/fda_finder.py
# ================================

import requests
import pandas as pd
from typing import List, Dict


class FDAAlternativesFinder:
    """
    Find alternative medications for a given medicine and condition using FDA API
    """
    
    BASE_URL = "https://api.fda.gov/drug/label.json"
    
    def __init__(self):
        self.session = requests.Session()
    
    def search_by_indication(self, condition: str, limit: int = 1000) -> List[Dict]:
        """
        Search FDA drug labels by indication/condition
        """
        print(f"\n🔍 Searching FDA database for condition: '{condition}'")
        
        # Build search query for indications_and_usage field
        search_query = f'indications_and_usage:"{condition}"'
        
        params = {
            'search': search_query,
            'limit': limit
        }
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            print(f"Found {len(results)} drug labels")
            return results
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"No results found for condition: '{condition}'")
                return []
            else:
                print(f"HTTP Error: {e}")
                return []
        except Exception as e:
            print(f"Error searching FDA API: {e}")
            return []
    
    def extract_active_moieties(self, results: List[Dict], exclude_medicine: str = None) -> pd.DataFrame:
        """
        Extract and deduplicate active moiety names from search results
        """
        medications = []
        exclude_lower = exclude_medicine.lower() if exclude_medicine else None
        
        for result in results:
            # Extract relevant fields
            brand_name = result.get('openfda', {}).get('brand_name', ['Unknown'])[0] if result.get('openfda', {}).get('brand_name') else 'Unknown'
            generic_name = result.get('openfda', {}).get('generic_name', ['Unknown'])[0] if result.get('openfda', {}).get('generic_name') else 'Unknown'
            
            # Get substance/active moiety names
            substance_names = result.get('openfda', {}).get('substance_name', [])
            
            # Get manufacturer
            manufacturer = result.get('openfda', {}).get('manufacturer_name', ['Unknown'])[0] if result.get('openfda', {}).get('manufacturer_name') else 'Unknown'
            
            # Get product type (prescription vs OTC)
            product_type = result.get('openfda', {}).get('product_type', ['Unknown'])[0] if result.get('openfda', {}).get('product_type') else 'Unknown'
            
            # Get route of administration
            route = result.get('openfda', {}).get('route', ['Unknown'])
            route_str = ', '.join(route) if route else 'Unknown'
            
            if substance_names:
                for substance in substance_names:
                    # Skip if this is the original medicine
                    if exclude_lower and exclude_lower in substance.lower():
                        continue
                    
                    medications.append({
                        'Active_Moiety': substance,
                        'Brand_Name': brand_name,
                        'Generic_Name': generic_name,
                        'Manufacturer': manufacturer,
                        'Product_Type': product_type,
                        'Route': route_str
                    })
            else:
                # Skip if this is the original medicine
                if exclude_lower and (exclude_lower in generic_name.lower() or exclude_lower in brand_name.lower()):
                    continue
                
                # If no substance name, use generic name
                medications.append({
                    'Active_Moiety': generic_name,
                    'Brand_Name': brand_name,
                    'Generic_Name': generic_name,
                    'Manufacturer': manufacturer,
                    'Product_Type': product_type,
                    'Route': route_str
                })
        
        # Create DataFrame
        df = pd.DataFrame(medications)
        
        if len(df) == 0:
            return df
        
        # Remove duplicates based on Active_Moiety
        print(f"\nTotal medications before deduplication: {len(df)}")
        df_unique = df.drop_duplicates(subset=['Active_Moiety'], keep='first')
        print(f"Unique active moieties: {len(df_unique)}")
        
        return df_unique
    
    def get_top_alternatives(self, medicine: str, condition: str, top_n: int = 3) -> List[Dict]:
        """
        Get top N alternative medications (excluding the original medicine)
        
        Args:
            medicine: Name of the input medicine to exclude
            condition: Medical condition/indication
            top_n: Number of top alternatives to return
            
        Returns:
            List of dictionaries with alternative medication details
        """
        print(f"\n{'='*60}")
        print(f"Finding alternatives for: {medicine}")
        print(f"Condition: {condition}")
        print(f"{'='*60}")
        
        # Search for all medications for the condition
        results = self.search_by_indication(condition)
        
        if not results:
            print(f"No alternatives found for {condition}")
            return []
        
        # Extract and deduplicate active moieties (excluding original medicine)
        df_medications = self.extract_active_moieties(results, exclude_medicine=medicine)
        
        if len(df_medications) == 0:
            print(f"No alternatives found after filtering")
            return []
        
        # Filter for prescription medications only
        df_rx = df_medications[df_medications['Product_Type'].str.contains('PRESCRIPTION', case=False, na=False)]
        
        print(f"\nPrescription alternatives found: {len(df_rx)}")
        
        # Get top N alternatives
        top_alternatives = df_rx.head(top_n)
        alternatives_list = top_alternatives.to_dict('records')
        
        print(f"\nTop {len(alternatives_list)} alternatives:")
        for i, alt in enumerate(alternatives_list, 1):
            print(f"  {i}. {alt['Active_Moiety']} ({alt['Brand_Name']})")
        
        return alternatives_list

