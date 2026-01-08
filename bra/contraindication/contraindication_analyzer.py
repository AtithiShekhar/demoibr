import json
import requests
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import re
from pathlib import Path
current_dir = Path(__file__).resolve().parent
dotenv_path = current_dir / 'utils' / '.env'
# Load environment variables
load_dotenv(dotenv_path=dotenv_path)

class SimpleFDAAnalyzer:
    """
    Two-part approach:
    Part 1: Extract contraindications data (pure extraction, no interpretation)
    Part 2: Simple matching of patient conditions to contraindications
    """
    
    def __init__(self):
        """Initialize with FDA API key"""
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        print(self.fda_api_key)
        self.fda_base_url = "https://api.fda.gov/drug/label.json"
    
    # ============================================================================
    # PART 1: PURE DATA EXTRACTION (No AI, no interpretation)
    # ============================================================================
    
    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """
        Part 1: Extract relevant FDA sections for a medicine
        Returns raw text from FDA API, no interpretation
        """
        try:
            # Query FDA API
            search_query = f'openfda.generic_name:"{medicine_name}" OR openfda.brand_name:"{medicine_name}"'
            params = {
                'search': search_query,
                'limit': 1
            }
            if self.fda_api_key:
                params['api_key'] = self.fda_api_key
            
            response = requests.get(self.fda_base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'results' not in data or len(data['results']) == 0:
                # Try alternative search
                params['search'] = f'"{medicine_name}"'
                response = requests.get(self.fda_base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'results' not in data or len(data['results']) == 0:
                    return None
            
            label_data = data['results'][0]
            
            # Extract all relevant sections (raw text only)
            sections = {
                'drug_name': medicine_name,
                'contraindications': self._extract_text(label_data, 'contraindications'),
                'boxed_warning': self._extract_text(label_data, 'boxed_warning'),
                'warnings': self._extract_text(label_data, 'warnings_and_cautions') or 
                           self._extract_text(label_data, 'warnings'),
                'pregnancy': self._extract_text(label_data, 'pregnancy') or
                            self._extract_text(label_data, 'teratogenic_effects'),
                'precautions': self._extract_text(label_data, 'precautions')
            }
            
            return sections
            
        except Exception as e:
            print(f"Error extracting data for {medicine_name}: {str(e)}")
            return None
    
    def _extract_text(self, label_data: Dict[str, Any], field_name: str) -> Optional[str]:
        """Helper to extract text from FDA label field"""
        field_data = label_data.get(field_name, [])
        if field_data and len(field_data) > 0:
            return "\n\n".join(field_data)
        return None
    
    def extract_all_medicines(self, medicine_list: List[str]) -> Dict[str, Any]:
        """
        Part 1: Extract FDA data for all medicines
        Returns: Dictionary mapping medicine name to extracted sections
        """
        print("\n" + "=" * 80)
        print("PART 1: EXTRACTING FDA DATA")
        print("=" * 80 + "\n")
        
        extracted_data = {}
        
        for i, medicine in enumerate(medicine_list, 1):
            print(f"[{i}/{len(medicine_list)}] Extracting: {medicine}...")
            sections = self.extract_fda_sections(medicine)
            
            if sections:
                # Count what we found
                found = []
                if sections['contraindications']: found.append("contraindications")
                if sections['boxed_warning']: found.append("boxed_warning")
                if sections['warnings']: found.append("warnings")
                if sections['pregnancy']: found.append("pregnancy")
                
                print(f"  ✓ Found: {', '.join(found) if found else 'no sections'}")
                extracted_data[medicine] = sections
            else:
                print(f"  ✗ No FDA data found")
                extracted_data[medicine] = None
            
            time.sleep(0.3)  # Rate limiting
        
        print("\n" + "=" * 80)
        print(f"Extraction complete: {len(extracted_data)} medicines")
        print("=" * 80 + "\n")
        
        return extracted_data
    
    # ============================================================================
    # PART 2: SIMPLE MATCHING (Direct text matching, minimal logic)
    # ============================================================================
    
    def match_contraindications(
        self, 
        patient_data: Dict[str, Any], 
        extracted_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Part 2: Simple matching of patient conditions to contraindications
        Uses direct text matching, no complex AI interpretation
        """
        print("\n" + "=" * 80)
        print("PART 2: MATCHING PATIENT TO CONTRAINDICATIONS")
        print("=" * 80 + "\n")
        
        patient = patient_data.get('patient', {})
        
        # Build patient condition list (lowercase for matching)
        patient_conditions = []
        if patient.get('condition'):
            # Split multiple conditions
            conditions = patient['condition'].lower().split(',')
            patient_conditions.extend([c.strip() for c in conditions])
        
        if patient.get('diagnosis'):
            patient_conditions.append(patient['diagnosis'].lower())
        
        # Patient allergies
        patient_allergies = [a.lower() for a in patient.get('allergies', [])]
        
        # Patient medications (for DDI checking)
        patient_meds = [m.lower() for m in patient_data.get('prescription', [])]
        
        print(f"Patient conditions: {patient_conditions}")
        print(f"Patient allergies: {patient_allergies if patient_allergies else 'None'}")
        print(f"Patient medications: {patient_meds}")
        print()
        
        results = []
        
        for medicine, sections in extracted_data.items():
            print(f"Checking: {medicine}")
            
            if sections is None:
                results.append({
                    'medicine': medicine,
                    'contraindicated': False,
                    'status': 'no_data',
                    'reason': 'No FDA data available'
                })
                print(f"  → No data\n")
                continue
            
            # Check contraindications
            match_result = self._simple_match(
                medicine,
                sections,
                patient_conditions,
                patient_allergies,
                patient_meds
            )
            
            results.append(match_result)
            
            # Print result
            if match_result['contraindicated']:
                print(f"  🚨 CONTRAINDICATED: {match_result['reason']}")
            else:
                print(f"  ✓ Safe: {match_result['reason']}")
            print()
        
        return results
    
    def _simple_match(
        self,
        medicine: str,
        sections: Dict[str, Any],
        patient_conditions: List[str],
        patient_allergies: List[str],
        patient_meds: List[str]
    ) -> Dict[str, Any]:
        """
        Simple direct matching logic
        Returns: {medicine, contraindicated, status, reason, fda_quote}
        """
        
        # Combine all relevant sections for checking
        contraindications_text = sections.get('contraindications', '') or ''
        boxed_warning_text = sections.get('boxed_warning', '') or ''
        pregnancy_text = sections.get('pregnancy', '') or ''
        warnings_text = sections.get('warnings', '') or ''
        
        # Convert to lowercase for matching
        contra_lower = contraindications_text.lower()
        boxed_lower = boxed_warning_text.lower()
        pregnancy_lower = pregnancy_text.lower()
        warnings_lower = warnings_text.lower()
        
        # Priority 1: Check CONTRAINDICATIONS section
        if contraindications_text:
            # Check patient conditions
            for condition in patient_conditions:
                if condition in contra_lower:
                    # Extract relevant quote
                    quote = self._extract_quote(contraindications_text, condition)
                    return {
                        'medicine': medicine,
                        'contraindicated': True,
                        'status': 'absolute',
                        'reason': f"Patient has {condition}",
                        'fda_quote': quote
                    }
            
            # Check allergies (hypersensitivity)
            if patient_allergies:
                medicine_lower = medicine.lower()
                for allergy in patient_allergies:
                    if medicine_lower in allergy or allergy in medicine_lower:
                        quote = self._extract_quote(contraindications_text, 'hypersensitivity')
                        return {
                            'medicine': medicine,
                            'contraindicated': True,
                            'status': 'absolute',
                            'reason': f"Patient allergic to {medicine}",
                            'fda_quote': quote
                        }
            
            # Check drug-drug interactions
            ddi_result = self._check_ddi(medicine, contraindications_text, patient_meds)
            if ddi_result:
                return ddi_result
        
        # Priority 2: CONSERVATIVE PREGNANCY CHECKING (very important!)
        # Check if patient is pregnant (look for pregnancy in any condition)
        is_pregnant = any('pregnan' in cond for cond in patient_conditions)
        
        if is_pregnant:
            # CONSERVATIVE APPROACH: Check ALL sections for pregnancy concerns
            # Pregnancy is too critical to miss - if ANY section mentions pregnancy
            # with cautionary language, we flag it
            
            # Expanded pregnancy warning keywords (conservative)
            pregnancy_warning_keywords = [
                'contraindicated',
                'should not be used',
                'must not be used',
                'do not use',
                'not recommended',
                'may cause fetal harm',
                'fetal harm',
                'category x',
                'category d',
                'avoid in pregnan',
                'avoid during pregnan',
                'teratogenic',
                'birth defects',
                'fetal abnormalities',
                'use only if',
                'potential risk',
                'can cause harm',
                'should be avoided'
            ]
            
            # Check 1: CONTRAINDICATIONS section (highest priority)
            if 'pregnan' in contra_lower:
                quote = self._extract_quote(contraindications_text, 'pregnan')
                return {
                    'medicine': medicine,
                    'contraindicated': True,
                    'status': 'absolute',
                    'reason': 'Patient is pregnant - contraindicated',
                    'fda_quote': quote
                }
            
            # Check 2: BOXED WARNING section
            if 'pregnan' in boxed_lower:
                # If pregnancy mentioned in boxed warning, it's serious
                for keyword in pregnancy_warning_keywords:
                    if keyword in boxed_lower:
                        quote = self._extract_quote(boxed_warning_text, 'pregnan')
                        return {
                            'medicine': medicine,
                            'contraindicated': True,
                            'status': 'absolute',
                            'reason': 'Patient is pregnant - boxed warning',
                            'fda_quote': quote
                        }
            
            # Check 3: PREGNANCY section (8.1)
            if pregnancy_text and 'pregnan' in pregnancy_lower:
                # Look for ANY cautionary language
                for keyword in pregnancy_warning_keywords:
                    if keyword in pregnancy_lower:
                        quote = self._extract_quote(pregnancy_text, keyword, chars=200)
                        return {
                            'medicine': medicine,
                            'contraindicated': True,
                            'status': 'pregnancy_warning',
                            'reason': 'Patient is pregnant - pregnancy warning found',
                            'fda_quote': quote
                        }
            
            # Check 4: WARNINGS section (if pregnancy mentioned with cautionary language)
            if 'pregnan' in warnings_lower:
                for keyword in pregnancy_warning_keywords:
                    if keyword in warnings_lower:
                        quote = self._extract_quote(warnings_text, 'pregnan', chars=200)
                        return {
                            'medicine': medicine,
                            'contraindicated': True,
                            'status': 'pregnancy_warning',
                            'reason': 'Patient is pregnant - warning in label',
                            'fda_quote': quote
                        }
            
            # If patient is pregnant and drug has ANY pregnancy information at all
            # but we couldn't find clear warnings, still flag for clinical review
            if pregnancy_text:
                quote = self._extract_quote(pregnancy_text, 'pregnan', chars=150)
                return {
                    'medicine': medicine,
                    'contraindicated': True,
                    'status': 'pregnancy_needs_review',
                    'reason': 'Patient is pregnant - requires clinical review',
                    'fda_quote': quote or 'Pregnancy information found in FDA label - verify safety'
                }
        
        # Priority 3: Check BOXED WARNING
        if boxed_warning_text:
            for condition in patient_conditions:
                if condition in boxed_lower:
                    quote = self._extract_quote(boxed_warning_text, condition)
                    return {
                        'medicine': medicine,
                        'contraindicated': True,
                        'status': 'boxed_warning',
                        'reason': f"Patient has {condition} (Boxed Warning)",
                        'fda_quote': quote
                    }
        
        # No contraindications found
        return {
            'medicine': medicine,
            'contraindicated': False,
            'status': 'safe',
            'reason': 'No matching contraindications found',
            'fda_quote': ''
        }
    
    def _check_ddi(self, medicine: str, contra_text: str, patient_meds: List[str]) -> Optional[Dict]:
        """Check for drug-drug interactions"""
        contra_lower = contra_text.lower()
        
        # Common DDI phrases
        ddi_phrases = [
            'do not coadminister',
            'do not use with',
            'concomitant use',
            'concurrent use',
            'combination with'
        ]
        
        # Check if there's a DDI warning
        has_ddi = any(phrase in contra_lower for phrase in ddi_phrases)
        
        if not has_ddi:
            return None
        
        # Extract mentioned drug names and check if patient is on them
        # Simple approach: check if any patient med appears after DDI phrase
        for med in patient_meds:
            if med.lower() != medicine.lower():  # Don't match the drug to itself
                if med.lower() in contra_lower:
                    # Found a potential DDI
                    quote = self._extract_quote(contra_text, med, chars=150)
                    return {
                        'medicine': medicine,
                        'contraindicated': True,
                        'status': 'drug_interaction',
                        'reason': f"Patient taking both {medicine} and {med}",
                        'fda_quote': quote
                    }
        
        return None
    
    def _extract_quote(self, text: str, keyword: str, chars: int = 200) -> str:
        """Extract a relevant quote from text around a keyword"""
        if not text:
            return ""
        
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Find keyword position
        pos = text_lower.find(keyword_lower)
        if pos == -1:
            return text[:chars]  # Return beginning if keyword not found
        
        # Extract surrounding text
        start = max(0, pos - chars//2)
        end = min(len(text), pos + chars//2)
        
        quote = text[start:end].strip()
        
        # Clean up
        if start > 0:
            quote = "..." + quote
        if end < len(text):
            quote = quote + "..."
        
        return quote
    
    # ============================================================================
    # SIMPLE OUTPUT GENERATION
    # ============================================================================
    
    def generate_simple_report(
        self,
        patient_data: Dict[str, Any],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate simple, clear report"""
        
        contraindicated = [r for r in results if r['contraindicated']]
        safe = [r for r in results if not r['contraindicated']]
        
        # Simple summary
        if contraindicated:
            summary = f"⚠️ STOP {len(contraindicated)} medication(s) immediately"
        else:
            summary = f"✓ All {len(safe)} medications are safe to continue"
        
        report = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': {
                'age': patient_data['patient'].get('age'),
                'gender': patient_data['patient'].get('gender'),
                'conditions': patient_data['patient'].get('condition'),
                'allergies': patient_data['patient'].get('allergies', [])
            },
            'summary': summary,
            'contraindicated_medications': contraindicated,
            'safe_medications': safe,
            'total_medications': len(results)
        }
        
        return report
    
    def print_simple_report(self, report: Dict[str, Any]):
        """Print simple, readable report"""
        print("\n" + "=" * 80)
        print("CONTRAINDICATION REPORT")
        print("=" * 80)
        print(f"\nPatient: {report['patient']['age']}y {report['patient']['gender']}")
        print(f"Conditions: {report['patient']['conditions']}")
        if report['patient']['allergies']:
            print(f"Allergies: {', '.join(report['patient']['allergies'])}")
        
        print(f"\n{report['summary']}")
        print("=" * 80)
        
        # Show contraindicated medications
        if report['contraindicated_medications']:
            print("\n🚨 CONTRAINDICATED MEDICATIONS - STOP IMMEDIATELY:\n")
            for med in report['contraindicated_medications']:
                print(f"  ❌ {med['medicine']}")
                print(f"     Reason: {med['reason']}")
                
                # Show status if it's pregnancy-related
                if med.get('status') in ['pregnancy_warning', 'pregnancy_needs_review']:
                    print(f"     ⚠️  PREGNANCY DETECTED - Requires clinical review")
                
                if med.get('fda_quote'):
                    quote = med['fda_quote'][:200] if len(med['fda_quote']) > 200 else med['fda_quote']
                    print(f"     FDA: \"{quote}...\"")
                print()
        
        # Show safe medications
        if report['safe_medications']:
            print("\n✓ SAFE TO CONTINUE:\n")
            for med in report['safe_medications']:
                print(f"  ✓ {med['medicine']}")
                if med['status'] == 'no_data':
                    print(f"     Note: {med['reason']}")
            print()
        
        print("=" * 80 + "\n")
    
    # ============================================================================
    # MAIN WORKFLOW
    # ============================================================================
    
    def analyze(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main workflow: Two-part analysis
        """
        medicines = patient_data.get('prescription', [])
        
        # PART 1: Extract FDA data (pure extraction)
        extracted_data = self.extract_all_medicines(medicines)
        
        # PART 2: Match patient to contraindications (simple matching)
        results = self.match_contraindications(patient_data, extracted_data)
        
        # Generate simple report
        report = self.generate_simple_report(patient_data, results)
        
        return report


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("SIMPLE FDA CONTRAINDICATION ANALYZER")
    print("Two-Part Approach: Extract → Match → Report")
    print("=" * 80)
    
    # Load patient input
    try:
        with open('input.json', 'r') as f:
            patient_input = json.load(f)
    except FileNotFoundError:
        print("\n❌ Error: patient_input.json not found!")
        return
    except json.JSONDecodeError:
        print("\n❌ Error: Invalid JSON in patient_input.json")
        return
    
    # Initialize analyzer
    analyzer = SimpleFDAAnalyzer()
    
    # Run analysis
    report = analyzer.analyze(patient_input)
    
    # Print simple report
    analyzer.print_simple_report(report)
    
    # Save detailed report
    output_file = f"contraindication_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Detailed report saved to: {output_file}\n")


if __name__ == "__main__":
    main()
