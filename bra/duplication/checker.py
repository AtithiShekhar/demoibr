"""
duplication/checker.py
Therapeutic Duplication Checker - Integrated Module
"""

import json
import requests
from typing import Dict, List, Any, Optional
import os
import time
from itertools import combinations
from datetime import datetime


class TherapeuticDuplicationChecker:
    """Therapeutic Duplication Analyzer"""
    
    def __init__(self):
        self.fda_base_url = "https://api.fda.gov/drug/label.json"
        
        # Drug class groupings (abbreviated for space)
        self.drug_classes = {
            'statins': ['atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin'],
            'nsaids': ['ibuprofen', 'naproxen', 'diclofenac', 'celecoxib'],
            'beta_blockers': ['metoprolol', 'atenolol', 'propranolol', 'carvedilol'],
            'ace_inhibitors': ['lisinopril', 'enalapril', 'ramipril', 'benazepril'],
            # Add more classes as needed
        }
        
        # Appropriate combinations
        self.appropriate_combinations = [
            ('spironolactone', 'furosemide'),
            ('aspirin', 'clopidogrel'),
            ('metformin', 'glipizide'),
            # Add more combinations
        ]
    
    def extract_therapeutic_data(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extract FDA data for medicine"""
        try:
            search_query = f'openfda.generic_name:"{medicine_name}" OR openfda.brand_name:"{medicine_name}"'
            params = {'search': search_query, 'limit': 1}
            
            response = requests.get(self.fda_base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'results' not in data or len(data['results']) == 0:
                return None
            
            label_data = data['results'][0]
            
            return {
                'drug_name': medicine_name,
                'mechanism_of_action': self._extract_text(label_data, 'mechanism_of_action'),
                'indications_and_usage': self._extract_text(label_data, 'indications_and_usage'),
                'pharmacologic_class': self._extract_pharmacologic_class(label_data)
            }
            
        except Exception as e:
            print(f"Error extracting data for {medicine_name}: {str(e)}")
            return None
    
    def _extract_text(self, label_data: Dict[str, Any], field_name: str) -> Optional[str]:
        """Helper to extract text from FDA label field"""
        field_data = label_data.get(field_name, [])
        if field_data and len(field_data) > 0:
            text = "\n\n".join(field_data)
            return text[:500] if len(text) > 500 else text
        return None
    
    def _extract_pharmacologic_class(self, label_data: Dict[str, Any]) -> Optional[str]:
        """Extract pharmacologic class"""
        openfda = label_data.get('openfda', {})
        pharm_class = openfda.get('pharm_class_epc', [])
        if not pharm_class:
            pharm_class = openfda.get('pharm_class_moa', [])
        
        if pharm_class and len(pharm_class) > 0:
            return ", ".join(pharm_class[:3])
        return None
    
    def analyze_duplications(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis function"""
        medicines = patient_data.get('prescription', [])
        
        if len(medicines) < 2:
            return {
                'summary': 'Not enough medications to analyze (need at least 2)',
                'redundant_duplicate': [],
                'overlap_with_rationale': [],
                'unique_no_overlap': [],
                'total_medications': len(medicines)
            }
        
        # Extract FDA data
        extracted_data = {}
        for medicine in medicines:
            data = self.extract_therapeutic_data(medicine)
            if data:
                extracted_data[medicine] = data
            time.sleep(0.3)  # Rate limiting
        
        # Compare pairs
        valid_medicines = {name: data for name, data in extracted_data.items() if data is not None}
        
        if len(valid_medicines) < 2:
            return {
                'summary': 'Insufficient FDA data to analyze',
                'redundant_duplicate': [],
                'overlap_with_rationale': [],
                'unique_no_overlap': [],
                'total_medications': len(medicines)
            }
        
        results = []
        medicine_pairs = list(combinations(valid_medicines.keys(), 2))
        
        for med1, med2 in medicine_pairs:
            result = self._categorize_pair(
                med1, valid_medicines[med1],
                med2, valid_medicines[med2]
            )
            results.append(result)
        
        # Categorize results
        redundant = [r for r in results if r['category'] == 'redundant']
        overlap = [r for r in results if r['category'] == 'overlap']
        unique = [r for r in results if r['category'] == 'unique']
        
        # Generate summary
        if redundant:
            summary = f"❌ CRITICAL: {len(redundant)} redundant/duplicate prescription(s) found"
        elif overlap:
            summary = f"⚠️ CAUTION: {len(overlap)} medication pair(s) with overlap detected"
        else:
            summary = f"✓ All {len(unique)} medication pair(s) have unique roles"
        
        return {
            'date': datetime.now().isoformat(),
            'summary': summary,
            'redundant_duplicate': redundant,
            'overlap_with_rationale': overlap,
            'unique_no_overlap': unique,
            'total_medications': len(medicines),
            'pairs_analyzed': len(results)
        }
    
    def _categorize_pair(self, med1_name: str, med1_data: Dict, med2_name: str, med2_data: Dict) -> Dict:
        """Categorize medicine pair"""
        med1_lower = med1_name.lower().strip()
        med2_lower = med2_name.lower().strip()
        
        # Check if same class
        same_class_name = None
        for class_name, drug_list in self.drug_classes.items():
            if any(d in med1_lower for d in drug_list) and any(d in med2_lower for d in drug_list):
                same_class_name = class_name
                break
        
        if same_class_name:
            # Check if appropriate combination
            is_appropriate = self._is_appropriate_combination(med1_lower, med2_lower)
            
            if is_appropriate:
                return {
                    'medicine_1': med1_name,
                    'medicine_2': med2_name,
                    'category': 'overlap',
                    'reason': f'Same class ({same_class_name}) but clinically recognized combination',
                    'recommendation': '✓ Appropriate combination - verify indication'
                }
            else:
                return {
                    'medicine_1': med1_name,
                    'medicine_2': med2_name,
                    'category': 'redundant',
                    'reason': f'Same drug class: {same_class_name}',
                    'recommendation': '⚠️ REDUNDANT - Review if both are necessary'
                }
        
        # Default to unique
        return {
            'medicine_1': med1_name,
            'medicine_2': med2_name,
            'category': 'unique',
            'reason': 'No significant overlap detected',
            'recommendation': '✓ Medications appear to have unique roles'
        }
    
    def _is_appropriate_combination(self, med1: str, med2: str) -> bool:
        """Check if combination is appropriate"""
        for combo in self.appropriate_combinations:
            if (combo[0] in med1 and combo[1] in med2) or \
               (combo[1] in med1 and combo[0] in med2):
                return True
        return False


def start(patient_data: Dict[str, Any], scoring_system=None) -> Dict:
    """
    Main entry point for therapeutic duplication checking
    
    Args:
        patient_data: Full patient data including prescriptions
        scoring_system: Optional scoring system to add results to
        
    Returns:
        Dictionary with duplication analysis results
    """
    checker = TherapeuticDuplicationChecker()
    result = checker.analyze_duplications(patient_data)
    
    # Calculate duplication score
    duplication_score = calculate_duplication_score(result)
    
    # Add to scoring system if provided
    if scoring_system:
        scoring_system.add_analysis("therapeutic_duplication", {
            **result,
            'duplication_score': duplication_score
        })
    
    # Format output
    output_text = format_duplication_output(result)
    
    return {
        'summary': result['summary'],
        'redundant_count': len(result['redundant_duplicate']),
        'overlap_count': len(result['overlap_with_rationale']),
        'unique_count': len(result['unique_no_overlap']),
        'duplication_score': duplication_score,
        'output': output_text,
        'detailed_results': result
    }


def calculate_duplication_score(result: Dict) -> Dict:
    """
    Calculate duplication risk score
    Weight: 80 (high risk) to 100 (no risk)
    Score: 1-5
    """
    redundant_count = len(result['redundant_duplicate'])
    overlap_count = len(result['overlap_with_rationale'])
    
    if redundant_count > 0:
        # Critical - redundant prescriptions
        weight = 80
        score = 1
        category = "High Risk - Redundant Prescriptions"
    elif overlap_count > 2:
        # Multiple overlaps
        weight = 90
        score = 2
        category = "Medium Risk - Multiple Overlaps"
    elif overlap_count > 0:
        # Some overlap
        weight = 95
        score = 3
        category = "Low Risk - Minor Overlap"
    else:
        # No duplications
        weight = 100
        score = 5
        category = "No Risk - Unique Medications"
    
    weighted_score = weight * score
    
    return {
        'duplication_category': category,
        'weight': weight,
        'score': score,
        'weighted_score': weighted_score,
        'redundant_found': redundant_count,
        'overlaps_found': overlap_count
    }


def format_duplication_output(result: Dict) -> str:
    """Format output text"""
    output = [f"Therapeutic Duplication Analysis: {result['summary']}"]
    
    if result['redundant_duplicate']:
        output.append("\n❌ Redundant Prescriptions:")
        for item in result['redundant_duplicate']:
            output.append(f"  - {item['medicine_1']} + {item['medicine_2']}: {item['reason']}")
    
    if result['overlap_with_rationale']:
        output.append("\n⚠️ Overlapping Medications:")
        for item in result['overlap_with_rationale']:
            output.append(f"  - {item['medicine_1']} + {item['medicine_2']}: {item['reason']}")
    
    return "\n".join(output)