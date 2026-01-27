
# ================================
# alternatives/analyzer.py
# ================================

from typing import List, Dict
from pubmed.searcher import PubMedSearcher


def analyze_alternatives_rct(
    alternatives: List[Dict],
    condition: str,
    email: str = None
) -> List[Dict]:
    """
    Analyze RCT counts for alternative medications using existing PubMed searcher
    
    Args:
        alternatives: List of alternative medication dictionaries
        condition: Medical condition
        email: Email for PubMed API
        
    Returns:
        List of dictionaries with medicine details and RCT counts
    """
    pubmed = PubMedSearcher(email=email)
    results = []
    
    print(f"\n{'='*60}")
    print(f"Analyzing RCT counts for {len(alternatives)} alternatives")
    print(f"{'='*60}")
    
    for alt in alternatives:
        medicine_name = alt['Active_Moiety']
        try:
            print(f"\nSearching RCTs for: {medicine_name} + {condition}")
            rct_count, conclusions = pubmed.search(medicine_name, condition)
            
            results.append({
                'name': medicine_name,
                'brand_name': alt.get('Brand_Name', 'Unknown'),
                'generic_name': alt.get('Generic_Name', 'Unknown'),
                'manufacturer': alt.get('Manufacturer', 'Unknown'),
                'route': alt.get('Route', 'Unknown'),
                'rct_count': rct_count,
                'top_conclusions': conclusions[:2] if conclusions else []  # Include top 2 conclusions
            })
            
            print(f"  → RCT count: {rct_count}")
        except Exception as e:
            print(f"  → Error: {e}")
            results.append({
                'name': medicine_name,
                'brand_name': alt.get('Brand_Name', 'Unknown'),
                'generic_name': alt.get('Generic_Name', 'Unknown'),
                'manufacturer': alt.get('Manufacturer', 'Unknown'),
                'route': alt.get('Route', 'Unknown'),
                'rct_count': 0,
                'top_conclusions': [],
                'error': str(e)
            })
    
    return results

