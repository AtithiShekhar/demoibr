import json
import requests
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from adrs.detectors import _extract_interaction_risk_factors
import re
import time
from adrs.helpers import (
    _extract_text,
    _extract_context,
    _deduplicate_adrs,
    _can_patient_be_pregnant
)

from adrs.detectors import (
    _extract_adr_name,
    _clean_serious_adr_name,
    find_drug_interactions
)
# Load environment variables
load_dotenv()

class Factor_3_2_3_3_Analyzer_Fixed:
    _extract_text = _extract_text
    _extract_context = _extract_context
    _deduplicate_adrs = _deduplicate_adrs
    _can_patient_be_pregnant = _can_patient_be_pregnant
    _extract_interaction_risk_factors = _extract_interaction_risk_factors 
    _extract_adr_name = _extract_adr_name
    _clean_serious_adr_name = _clean_serious_adr_name

    def find_drug_interactions(self, *args, **kwargs):
        return find_drug_interactions(self, *args, **kwargs)
    """
    Factor 3.2: Life-Threatening ADRs/Interactions
    Factor 3.3: Serious ADRs/Interactions
    CORRECTED VERSION - Fixes all identified issues
    """
    
    def __init__(self):
        """Initialize with FDA API key"""
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"
        
        # Life-Threatening Keywords (Factor 3.2.1)
        self.lt_keywords = [
            'fatal',
            'potentially fatal',
            'may result in death',
            'death',
            'mortality',
            'associated with fatal outcomes',
            'can be fatal',
            'risk of death',
            'lactic acidosis',
            'metabolic acidosis'
        ]
        
        # High-Risk Clinical Events (Factor 3.2.1)
        self.high_risk_events = [
            'anaphylaxis',
            'anaphylactic reaction',
            'anaphylactic shock',
            'stevens-johnson syndrome',
            'stevens johnson',
            'toxic epidermal necrolysis',
            'torsades de pointes',
            'ventricular arrhythmia',
            'ventricular fibrillation',
            'acute liver failure',
            'hepatic failure',
            'respiratory failure',
            'respiratory arrest',
            'agranulocytosis',
            'neutropenic sepsis',
            'bone marrow suppression',
            'aplastic anemia',
            'cardiac arrest',
            'sudden cardiac death',
            'heart failure',
            'pulmonary toxicity',
            'hepatotoxicity',
            'acute kidney injury',
            'renal failure',
            'necrotizing pancreatitis',
            'hemorrhagic pancreatitis'
        ]
        
        # Serious ADR Keywords (Factor 3.2.2)
        self.serious_keywords = [
            'serious adverse reactions',
            'serious side effects',
            'the following serious adverse reactions',
            'serious adverse reactions are described in more detail'
        ]
        
        # Risk factor patterns
        self.risk_factor_patterns = {
            'renal': ['renal impairment', 'kidney disease', 'egfr', 'creatinine clearance', 
                     'renal dysfunction', 'kidney failure', 'renal failure', 'chronic kidney disease'],
            'hepatic': ['liver disease', 'hepatic impairment', 'cirrhosis', 'liver failure',
                       'hepatic dysfunction'],
            'cardiac': ['heart failure', 'chf', 'cardiac dysfunction', 'cardiomyopathy',
                       'congestive heart failure', 'ventricular fibrillation', 'arrhythmia',
                       'ventricular tachycardia', 'atrial fibrillation'],
            'age': ['elderly', 'geriatric', 'age', 'older patients', 'patients over'],
            'metabolic': ['diabetes', 'diabetic', 'metabolic acidosis', 'hyperglycemia', 'hypoglycemia'],
            'respiratory': ['copd', 'asthma', 'respiratory disease', 'pulmonary disease'],
            'vascular': ['deep vein thrombosis', 'dvt', 'pulmonary embolism', 'thrombosis', 'venous thrombosis'],
            'lipid': ['hyperlipidemia', 'hypertriglyceridemia', 'high cholesterol', 'dyslipidemia']
        }
    
    # ============================================================================
    # PART 1: EXTRACT FDA SECTIONS
    # ============================================================================
    
    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extract relevant FDA sections"""
        try:
            search_variants = [medicine_name]
            
            medicine_lower = medicine_name.lower()
            if 'lithium' in medicine_lower:
                search_variants = ['lithium', 'lithium carbonate', 'lithium citrate']
            elif 'metformin' in medicine_lower:
                search_variants = ['metformin', 'metformin hydrochloride']
            elif 'warfarin' in medicine_lower:
                search_variants = ['warfarin', 'warfarin sodium']
            elif 'simvastatin' in medicine_lower:
                search_variants = ['simvastatin']
            elif 'amiodarone' in medicine_lower:
                search_variants = ['amiodarone', 'amiodarone hydrochloride']
            
            all_results = []
            
            for variant in search_variants:
                search_query = f'openfda.generic_name:"{variant}" OR openfda.brand_name:"{variant}"'
                params = {
                    'search': search_query,
                    'limit': 5
                }
                if self.fda_api_key:
                    params['api_key'] = self.fda_api_key
                
                try:
                    response = requests.get(self.fda_base_url, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'results' in data and len(data['results']) > 0:
                        all_results.extend(data['results'])
                        break
                except:
                    continue
            
            if not all_results:
                params['search'] = f'"{medicine_name}"'
                response = requests.get(self.fda_base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if 'results' not in data or len(data['results']) == 0:
                    return None
                all_results = data['results']
            
            # Prefer single-ingredient products
            results = all_results
            single_ingredient = None
            
            for result in results:
                generic_names = result.get('openfda', {}).get('generic_name', [])
                
                if len(generic_names) == 1:
                    if generic_names[0].lower() == medicine_lower or medicine_lower in generic_names[0].lower():
                        single_ingredient = result
                        break
            
            label_data = single_ingredient if single_ingredient else results[0]
            
            sections = {
                'drug_name': medicine_name,
                'boxed_warning': self._extract_text(label_data, 'boxed_warning'),
                'warnings_and_cautions': self._extract_text(label_data, 'warnings_and_cautions'),
                'warnings': self._extract_text(label_data, 'warnings'),
                'precautions': self._extract_text(label_data, 'precautions'),
                'adverse_reactions': self._extract_text(label_data, 'adverse_reactions'),
                'drug_interactions': self._extract_text(label_data, 'drug_interactions'),
                'contraindications': self._extract_text(label_data, 'contraindications')
            }
            
            return sections
            
        except Exception as e:
            print(f"Error extracting data for {medicine_name}: {str(e)}")
            return None
    # ============================================================================
    # FACTOR 3.2.1: LIFE-THREATENING ADRs
    # ============================================================================
    
    def find_life_threatening_adrs(
        self, 
        medicine_name: str,
        fda_sections: Dict[str, Any],
        patient_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Factor 3.2.1: Identify Life-Threatening ADRs
        """
        
        if not fda_sections:
            return {'with_risk_factors': [], 'without_risk_factors': []}
        
        can_be_pregnant = self._can_patient_be_pregnant(patient_data)
        
        # Search Section 6 Adverse Reactions first
        adverse_reactions = fda_sections.get('adverse_reactions', '')
        warnings = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
        boxed_warning = fda_sections.get('boxed_warning', '')
        
        all_lt_adrs = []
        
        # Check Adverse Reactions section
        if adverse_reactions:
            lt_adrs_from_ar = self._search_for_lt_adrs(
                adverse_reactions, 
                'Section 6 Adverse Reactions',
                medicine_name,
                can_be_pregnant
            )
            all_lt_adrs.extend(lt_adrs_from_ar)
        
        # Check Warnings section
        if warnings:
            lt_adrs_from_warn = self._search_for_lt_adrs(
                warnings,
                'Section 5 Warnings and Precautions',
                medicine_name,
                can_be_pregnant
            )
            all_lt_adrs.extend(lt_adrs_from_warn)
        
        # Check Boxed Warning
        if boxed_warning:
            lt_adrs_from_boxed = self._search_for_lt_adrs(
                boxed_warning,
                'Boxed Warning',
                medicine_name,
                can_be_pregnant
            )
            all_lt_adrs.extend(lt_adrs_from_boxed)
        
        # Deduplicate
        unique_lt_adrs = self._deduplicate_adrs(all_lt_adrs)
        
        # Match patient risk factors
        with_risk_factors = []
        without_risk_factors = []
        
        for adr in unique_lt_adrs:
            risk_match = self._match_patient_risk_factors(adr, patient_data, fda_sections)
            
            adr_result = {
                'medicine': medicine_name,
                'adr_name': adr['adr_name'],
                'section': adr['section'],
                'risk_factors': risk_match['matched_factors'],
                'fda_context': adr['context']
            }
            
            if risk_match['has_risk_factors']:
                with_risk_factors.append(adr_result)
            else:
                without_risk_factors.append(adr_result)
        
        return {
            'with_risk_factors': with_risk_factors,
            'without_risk_factors': without_risk_factors
        }
    
    def _search_for_lt_adrs(
        self, 
        text: str, 
        section_name: str, 
        medicine_name: str,
        can_be_pregnant: bool
    ) -> List[Dict[str, Any]]:
        """Search for life-threatening ADRs in text"""
        
        if not text:
            return []
        
        text_lower = text.lower()
        found_adrs = []
        
        # Search for high-risk events FIRST (more specific)
        for event in self.high_risk_events:
            if event in text_lower:
                # Filter pregnancy-related events
                pregnancy_events = ['spontaneous abortion', 'fetal death', 'fetal harm', 
                                  'embryo-fetal toxicity', 'fetal toxicity']
                if any(preg_event in event for preg_event in pregnancy_events):
                    if not can_be_pregnant:
                        continue
                
                context = self._extract_context(text, event, chars=300)
                
                found_adrs.append({
                    'medicine': medicine_name,
                    'adr_name': event.title(),
                    'section': section_name,
                    'context': context,
                    'detection_method': 'high_risk_event',
                    'keyword': event
                })
        
        # Search for keywords (less specific, so check if not already found as event)
        for keyword in self.lt_keywords:
            if keyword in text_lower:
                context = self._extract_context(text, keyword, chars=300)
                adr_name = self._extract_adr_name(context, keyword)
                
                if adr_name and adr_name != 'None':
                    # Skip if already found as high-risk event
                    already_found = False
                    for existing_adr in found_adrs:
                        if existing_adr['adr_name'].lower() == adr_name.lower():
                            already_found = True
                            break
                    
                    if not already_found:
                        # Filter pregnancy-related
                        pregnancy_terms = ['spontaneous abortion', 'fetal', 'pregnancy', 'embryo']
                        if any(term in adr_name.lower() for term in pregnancy_terms):
                            if not can_be_pregnant:
                                continue
                        
                        found_adrs.append({
                            'medicine': medicine_name,
                            'adr_name': adr_name,
                            'section': section_name,
                            'context': context,
                            'detection_method': 'keyword',
                            'keyword': keyword
                        })
        
        return found_adrs
    
    # ============================================================================
    # FACTOR 3.2.2: SERIOUS ADRs
    # ============================================================================
    
    def find_serious_adrs(
        self,
        medicine_name: str,
        fda_sections: Dict[str, Any],
        patient_data: Dict[str, Any],
        lt_adrs: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Factor 3.2.2: Identify Serious ADRs (excluding LT ADRs)
        """
        
        if not fda_sections:
            return {'with_risk_factors': [], 'without_risk_factors': []}
        
        # Get all LT ADR names to exclude
        lt_adr_names = set()
        for adr in lt_adrs['with_risk_factors'] + lt_adrs['without_risk_factors']:
            lt_adr_names.add(adr['adr_name'].lower())
        
        # Search Section 6 Adverse Reactions
        adverse_reactions = fda_sections.get('adverse_reactions', '')
        warnings = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
        
        all_serious_adrs = []
        
        # Look for the specific statement pattern
        if adverse_reactions:
            serious_adrs_from_ar = self._search_for_serious_adrs(
                adverse_reactions,
                'Section 6 Adverse Reactions',
                medicine_name,
                lt_adr_names
            )
            all_serious_adrs.extend(serious_adrs_from_ar)
        
        if warnings:
            serious_adrs_from_warn = self._search_for_serious_adrs(
                warnings,
                'Section 5 Warnings and Precautions',
                medicine_name,
                lt_adr_names
            )
            all_serious_adrs.extend(serious_adrs_from_warn)
        
        # Deduplicate
        unique_serious_adrs = self._deduplicate_adrs(all_serious_adrs)
        
        # Match patient risk factors
        with_risk_factors = []
        without_risk_factors = []
        
        for adr in unique_serious_adrs:
            risk_match = self._match_patient_risk_factors(adr, patient_data, fda_sections)
            
            adr_result = {
                'medicine': medicine_name,
                'adr_name': adr['adr_name'],
                'section': adr['section'],
                'risk_factors': risk_match['matched_factors'],
                'fda_context': adr['context']
            }
            
            if risk_match['has_risk_factors']:
                with_risk_factors.append(adr_result)
            else:
                without_risk_factors.append(adr_result)
        
        return {
            'with_risk_factors': with_risk_factors,
            'without_risk_factors': without_risk_factors
        }
    
    def _search_for_serious_adrs(
        self, 
        text: str, 
        section_name: str, 
        medicine_name: str,
        lt_adr_names: set
    ) -> List[Dict[str, Any]]:
        """Search for serious ADRs in text"""
        
        if not text:
            return []
        
        text_lower = text.lower()
        found_adrs = []
        
        # Look for the specific pattern
        patterns = [
            r'the following serious adverse reactions are described in more detail[^:]*:([^\.]+(?:\.[^\.]{10,100})?)',
            r'serious adverse reactions include:([^\.]+(?:\.[^\.]{10,100})?)',
            r'serious side effects include:([^\.]+(?:\.[^\.]{10,100})?)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Extract the list of ADRs
                adr_list_text = match.group(1)
                
                # Split by common delimiters
                potential_adrs = re.split(r'[,;•\n]', adr_list_text)
                
                for potential_adr in potential_adrs:
                    adr_clean = potential_adr.strip()
                    
                    # Skip empty or very short
                    if len(adr_clean) < 5:
                        continue
                    
                    # Skip if it's a reference or connector
                    skip_words = ['see', 'section', 'and', 'or', 'the', 'in', 'of', 'warnings']
                    if any(adr_clean.startswith(word) for word in skip_words):
                        continue
                    
                    # Clean up the ADR name
                    adr_name = _clean_serious_adr_name(self,text= adr_clean)
                    
                    if not adr_name or adr_name == 'None':
                        continue
                    
                    # Skip if already in LT ADRs
                    if adr_name.lower() in lt_adr_names:
                        continue
                    
                    # Skip if contains LT keywords
                    if any(lt_kw in adr_name.lower() for lt_kw in self.lt_keywords):
                        continue
                    
                    # Skip if it's a high-risk event (those are LT ADRs)
                    if any(event in adr_name.lower() for event in self.high_risk_events):
                        continue
                    
                    context = self._extract_context(text, adr_name, chars=300)
                    
                    found_adrs.append({
                        'medicine': medicine_name,
                        'adr_name': adr_name,
                        'section': section_name,
                        'context': context,
                        'detection_method': 'serious_statement'
                    })
        
        return found_adrs
    
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _match_patient_risk_factors(
        self,
        adr: Dict[str, Any],
        patient_data: Dict[str, Any],
        fda_sections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Match patient conditions to risk factors"""
        
        patient = patient_data.get('patient', {})
        context_lower = adr['context'].lower()
        
        # Also search full section text for better risk factor matching
        full_text = ""
        if adr['section'] == 'Section 6 Adverse Reactions':
            full_text = fda_sections.get('adverse_reactions', '')
        elif adr['section'] == 'Section 5 Warnings and Precautions':
            full_text = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
        elif adr['section'] == 'Boxed Warning':
            full_text = fda_sections.get('boxed_warning', '')
        
        full_text_lower = full_text.lower() if full_text else ""
        
        matched_factors = []
        
        # Check AGE
        patient_age = patient.get('age', 0)
        if patient_age > 65:
            if any(kw in context_lower or kw in full_text_lower 
                   for kw in self.risk_factor_patterns['age']):
                matched_factors.append(f"age >65 (patient age: {patient_age})")
        
        # Check CONDITIONS
        patient_conditions = []
        if patient.get('condition'):
            patient_conditions.append(patient['condition'].lower())
        if patient.get('diagnosis'):
            # Split diagnosis by commas
            diagnoses = [d.strip() for d in patient['diagnosis'].lower().split(',')]
            patient_conditions.extend(diagnoses)
        
        for condition in patient_conditions:
            for risk_type, keywords in self.risk_factor_patterns.items():
                if risk_type == 'age':
                    continue
                
                # Check if patient has this condition
                patient_has_condition = any(kw in condition for kw in keywords)
                
                # Check if FDA text mentions this risk factor
                fda_mentions_risk = any(kw in context_lower or kw in full_text_lower for kw in keywords)
                
                if patient_has_condition and fda_mentions_risk:
                    matched_factors.append(f"{risk_type} condition ({condition})")
        
        # Deduplicate risk factors
        unique_factors = []
        seen = set()
        for factor in matched_factors:
            key = factor.split('(')[0].strip().lower()
            if key not in seen:
                seen.add(key)
                unique_factors.append(factor)
        
        return {
            'has_risk_factors': len(unique_factors) > 0,
            'matched_factors': unique_factors
        }   
    
    
    # ============================================================================
    # OUTPUT GENERATION
    # ============================================================================
    
    def generate_output_text(
        self,
        factor_type: str,
        sub_factor: str,
        medicine: str,
        adr_name: str,
        risk_factors: List[str]
    ) -> str:
        """Generate output text according to documentation format"""
        
        if factor_type == 'LT_ADR':
            if sub_factor == 'with_risk_factors':
                risk_spec = ", ".join(risk_factors)
                return (f"Use of this {medicine} in patients having this {risk_spec}, "
                       f"will cause LT ADRs {adr_name}, below measures are recommended to "
                       f"follow by patient to prevent this ADR occurrence. – to cross refer "
                       f"to the output for step 4 (RMM).")
            else:
                return (f"Use of this {medicine} may cause LT ADRs {adr_name}. Monitor patient "
                       f"closely for signs and symptoms. – to cross refer to the output for "
                       f"step 4 (RMM).")
        
        elif factor_type == 'Serious_ADR':
            if sub_factor == 'with_risk_factors':
                risk_spec = ", ".join(risk_factors)
                return (f"Use of this {medicine} in patients having this {risk_spec}, "
                       f"will cause Serious ADRs {adr_name}, below measures are recommended "
                       f"to follow by patient to prevent this ADR occurrence. – to cross refer "
                       f"to the output for step 4 (RMM).")
            else:
                return (f"Use of this {medicine} may cause Serious ADRs like {adr_name}, "
                       f"below measures are recommended to follow by patient to prevent this "
                       f"ADR occurrence. – to cross refer to the output for step 4 (RMM).")
        
        elif factor_type == 'Interaction':
            if sub_factor == 'contraindicated':
                return (f"Concurrent use of this {medicine} with {adr_name} is contraindicated. "
                       f"– to cross refer to the output for step 4 (RMM).")
            elif sub_factor == 'lt':
                return (f"Concurrent use of this {medicine} with {adr_name} is a life-threatening "
                       f"interaction that can cause LT ADRs, below measures are recommended to "
                       f"follow by patient to prevent this interaction. – to cross refer to the "
                       f"output for step 4 (RMM).")
            elif sub_factor == 'serious':
                return (f"Concurrent use of this {medicine} with {adr_name} may cause serious "
                       f"ADRs. Monitor patient closely. – to cross refer to the output for "
                       f"step 4 (RMM).")
            else:
                return (f"Concurrent use of this {medicine} with {adr_name} may affect efficacy. "
                       f"Monitor patient response.")
        
        return ""
    

    def analyze(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis workflow"""
        
        medicines = patient_data.get('prescription', [])
        
        if not medicines:
            return {
                'factor_3_2': {'LT_ADRs': {}, 'Serious_ADRs': {}},
                'factor_3_3': {'interactions': {}}
            }
        
        print("\n" + "=" * 80)
        print("FACTOR 3.2 & 3.3 ANALYSIS (CORRECTED)")
        print("=" * 80 + "\n")
        
        # Extract FDA data
        print("Extracting FDA data...")
        extracted_data = {}
        for i, medicine in enumerate(medicines, 1):
            print(f"[{i}/{len(medicines)}] {medicine}...")
            sections = self.extract_fda_sections(medicine)
            extracted_data[medicine] = sections
            time.sleep(0.3)
        
        print("\nAnalyzing...")
        
        results_3_2_lt = {}
        results_3_2_serious = {}
        results_3_3 = {}
        
        for medicine in medicines:
            fda_sections = extracted_data.get(medicine)
            
            if not fda_sections:
                continue
            
            # Factor 3.2.1: Life-Threatening ADRs
            lt_results = self.find_life_threatening_adrs(medicine, fda_sections, patient_data)
            if lt_results['with_risk_factors'] or lt_results['without_risk_factors']:
                results_3_2_lt[medicine] = lt_results
            
            # Factor 3.2.2: Serious ADRs
            serious_results = self.find_serious_adrs(medicine, fda_sections, patient_data, lt_results)
            if serious_results['with_risk_factors'] or serious_results['without_risk_factors']:
                results_3_2_serious[medicine] = serious_results
            
            # Factor 3.3: Drug Interactions
            interaction_results = self.find_drug_interactions(medicine, fda_sections, patient_data)
            if any(interaction_results.values()):
                results_3_3[medicine] = interaction_results
        
        return {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': patient_data.get('patient', {}),
            'medications': medicines,
            'factor_3_2': {
                'LT_ADRs': results_3_2_lt,
                'Serious_ADRs': results_3_2_serious
            },
            'factor_3_3': {
                'interactions': results_3_3
            }
        }
    
    def print_report(self, results: Dict[str, Any]):
        """Print formatted report"""
        
        print("\n" + "=" * 80)
        print("FACTOR 3.2 & 3.3 ANALYSIS REPORT (CORRECTED)")
        print("=" * 80)
        
        patient = results.get('patient', {})
        print(f"\nPatient: {patient.get('age')}y {patient.get('gender')}")
        print(f"Diagnosis: {patient.get('diagnosis')}")
        print(f"Condition: {patient.get('condition')}")
        print(f"Medications: {', '.join(results.get('medications', []))}")
        
        # Factor 3.2.1: Life-Threatening ADRs
        lt_adrs = results['factor_3_2']['LT_ADRs']
        
        if lt_adrs:
            print("\n" + "=" * 80)
            print("FACTOR 3.2.1: LIFE-THREATENING ADRs")
            print("=" * 80)
            
            for medicine, data in lt_adrs.items():
                print(f"\n{medicine}:")
                
                if data['with_risk_factors']:
                    print("\n  Sub-factor: Life-threatening ADRs/DI + risk factors")
                    for adr in data['with_risk_factors']:
                        print(f"\n  • ADR: {adr['adr_name']}")
                        print(f"    Risk Factors: {', '.join(adr['risk_factors'])}")
                        output = self.generate_output_text(
                            'LT_ADR', 'with_risk_factors',
                            medicine, adr['adr_name'], adr['risk_factors']
                        )
                        print(f"    Output: {output}")
                
                if data['without_risk_factors']:
                    print("\n  Sub-factor: Life-threatening ADRs/DI, with No risk factors")
                    for adr in data['without_risk_factors']:
                        print(f"\n  • ADR: {adr['adr_name']}")
                        output = self.generate_output_text(
                            'LT_ADR', 'without_risk_factors',
                            medicine, adr['adr_name'], []
                        )
                        print(f"    Output: {output}")
        
        # Factor 3.2.2: Serious ADRs
        serious_adrs = results['factor_3_2']['Serious_ADRs']
        
        if serious_adrs:
            print("\n" + "=" * 80)
            print("FACTOR 3.2.2: SERIOUS ADRs")
            print("=" * 80)
            
            for medicine, data in serious_adrs.items():
                print(f"\n{medicine}:")
                
                if data['with_risk_factors']:
                    print("\n  Sub-factor: Serious ADRs + risk factors/interactions")
                    for adr in data['with_risk_factors']:
                        print(f"\n  • ADR: {adr['adr_name']}")
                        print(f"    Risk Factors: {', '.join(adr['risk_factors'])}")
                        output = self.generate_output_text(
                            'Serious_ADR', 'with_risk_factors',
                            medicine, adr['adr_name'], adr['risk_factors']
                        )
                        print(f"    Output: {output}")
                
                if data['without_risk_factors']:
                    print("\n  Sub-factor: Serious ADRs, no risk factors/no interactions")
                    for adr in data['without_risk_factors']:
                        print(f"\n  • ADR: {adr['adr_name']}")
                        output = self.generate_output_text(
                            'Serious_ADR', 'without_risk_factors',
                            medicine, adr['adr_name'], []
                        )
                        print(f"    Output: {output}")
        
        # Factor 3.3: Drug Interactions
        interactions = results['factor_3_3']['interactions']
        
        if interactions:
            print("\n" + "=" * 80)
            print("FACTOR 3.3: DRUG INTERACTIONS")
            print("=" * 80)
            
            for medicine, data in interactions.items():
                print(f"\n{medicine}:")
                
                if data['contraindicated']:
                    print("\n  Sub-factor: Contraindicated Interactions")
                    for interaction in data['contraindicated']:
                        print(f"\n  • Contraindicated with: {interaction['interacting_drug']}")
                        if interaction['risk_factors']:
                            print(f"    Risk Factors: {', '.join(interaction['risk_factors'])}")
                        output = self.generate_output_text(
                            'Interaction', 'contraindicated',
                            medicine, interaction['interacting_drug'], []
                        )
                        print(f"    Output: {output}")
                
                if data['lt_interactions']:
                    print("\n  Sub-factor: LT Interactions")
                    for interaction in data['lt_interactions']:
                        print(f"\n  • LT interaction with: {interaction['interacting_drug']}")
                        if interaction['risk_factors']:
                            print(f"    Risk Factors: {', '.join(interaction['risk_factors'])}")
                        output = self.generate_output_text(
                            'Interaction', 'lt',
                            medicine, interaction['interacting_drug'], []
                        )
                        print(f"    Output: {output}")
                
                if data['serious_interactions']:
                    print("\n  Sub-factor: Serious Interactions")
                    for interaction in data['serious_interactions']:
                        print(f"\n  • Serious interaction with: {interaction['interacting_drug']}")
                        if interaction['risk_factors']:
                            print(f"    Risk Factors: {', '.join(interaction['risk_factors'])}")
                        output = self.generate_output_text(
                            'Interaction', 'serious',
                            medicine, interaction['interacting_drug'], []
                        )
                        print(f"    Output: {output}")
                
                if data['non_serious_interactions']:
                    print("\n  Sub-factor: Non-serious Interactions")
                    for interaction in data['non_serious_interactions']:
                        print(f"\n  • Non-serious interaction with: {interaction['interacting_drug']}")
        
        if not lt_adrs and not serious_adrs and not interactions:
            print("\n✓ No life-threatening ADRs, serious ADRs, or interactions detected.")
        
        print("\n" + "=" * 80 + "\n")

