# detectors.py
import re
from typing import Dict, Any, List
from adrs.helpers import (
    _extract_context,
    _deduplicate_adrs,
    _can_patient_be_pregnant
)

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

def _extract_adr_name(self,context: str, keyword: str):
    context_lower = context.lower()

    serious_conditions = [
        'lactic acidosis', 'metabolic acidosis', 'diabetic ketoacidosis',
        'hemorrhagic pancreatitis', 'necrotizing pancreatitis', 'acute pancreatitis',
        'anaphylaxis', 'anaphylactic shock', 'anaphylactic reaction', 'angioedema',
        'stevens-johnson syndrome', 'toxic epidermal necrolysis',
        'respiratory failure', 'respiratory arrest',
        'acute liver failure', 'hepatic failure', 'hepatotoxicity',
        'pulmonary toxicity', 'cardiac arrest', 'ventricular arrhythmia',
        'torsades de pointes', 'agranulocytosis', 'neutropenia',
        'aplastic anemia', 'renal failure', 'acute kidney injury',
        'nephrotoxicity', 'ototoxicity', 'myocardial infarction',
        'stroke', 'pulmonary embolism', 'sepsis', 'rhabdomyolysis',
        'pancreatitis', 'hypoglycemia', 'hyperglycemia', 'heart failure',
        'ventricular fibrillation', 'spontaneous abortion'
    ]

    for condition in serious_conditions:
        if condition in context_lower:
            return condition.title()

    patterns = [
        r'cases of\s+([a-z\s]+?)(?:\s+have|\s+has|\s+may|\.|\s+in)',
        r'risk of\s+([a-z\s]+?)(?:\s+in|\s+and|\.|,)',
        r'may result in\s+([a-z\s]+?)(?:\,|\.|;)',
        r'can cause\s+([a-z\s]+?)(?:\,|\.|;|\s+in)',
    ]

    for pattern in patterns:
        match = re.search(pattern, context_lower)
        if match:
            adr_name = match.group(1).strip()
            if len(adr_name) > 5:
                return adr_name.title()

    return None

def find_drug_interactions(
        self,
        medicine_name: str,
        fda_sections: Dict[str, Any],
        patient_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Factor 3.3: Identify Drug Interactions
        Categories: Contraindicated, LT, Serious, Non-serious
        """
        
        if not fda_sections:
            return {
                'contraindicated': [],
                'lt_interactions': [],
                'serious_interactions': [],
                'non_serious_interactions': []
            }
        
        interactions_text = fda_sections.get('drug_interactions', '')
        contraindications_text = fda_sections.get('contraindications', '')
        
        if not interactions_text:
            return {
                'contraindicated': [],
                'lt_interactions': [],
                'serious_interactions': [],
                'non_serious_interactions': []
            }
        
        patient_meds = [m.lower().strip() for m in patient_data.get('prescription', [])]
        patient_meds = [m for m in patient_meds if m != medicine_name.lower()]
        
        contraindicated = []
        lt_interactions = []
        serious_interactions = []
        non_serious_interactions = []
        
        interactions_lower = interactions_text.lower()
        contraindications_lower = contraindications_text.lower() if contraindications_text else ""
        
        for med in patient_meds:
            if med in interactions_lower:
                context = self._extract_context(interactions_text, med, chars=500)
                context_lower = context.lower()
                
                # Check if truly contraindicated (must be in contraindications section OR explicitly say "contraindicated")
                is_contraindicated = False
                if contraindications_text and med in contraindications_lower:
                    # Check in contraindications section
                    contraind_context = self._extract_context(contraindications_text, med, chars=300)
                    is_contraindicated = True
                    context = contraind_context
                elif 'is contraindicated' in context_lower or 'are contraindicated' in context_lower:
                    # Only if it explicitly says "X is contraindicated"
                    # Check if the contraindication is specifically for this drug combination
                    contraind_pattern = f'{med}.*is contraindicated|concomitant use.*{med}.*is contraindicated'
                    if re.search(contraind_pattern, context_lower):
                        is_contraindicated = True
                
                if is_contraindicated:
                    contraindicated.append({
                        'medicine': medicine_name,
                        'interacting_drug': med,
                        'interaction_type': 'contraindicated',
                        'context': context,
                        'risk_factors': self._extract_interaction_risk_factors(context, patient_data)
                    })
                
                # Check for life-threatening interactions
                elif any(kw in context_lower for kw in ['fatal', 'death', 'life-threatening']) or \
                     any(event in context_lower for event in ['bleeding', 'hemorrhage', 'anaphylaxis']):
                    lt_interactions.append({
                        'medicine': medicine_name,
                        'interacting_drug': med,
                        'interaction_type': 'life-threatening',
                        'context': context,
                        'risk_factors': self._extract_interaction_risk_factors(context, patient_data)
                    })
                
                # Check for serious interactions (myopathy, rhabdomyolysis, etc.)
                elif 'serious' in context_lower or \
                     any(term in context_lower for term in ['myopathy', 'rhabdomyolysis', 'toxicity', 'severe']):
                    serious_interactions.append({
                        'medicine': medicine_name,
                        'interacting_drug': med,
                        'interaction_type': 'serious',
                        'context': context,
                        'risk_factors': self._extract_interaction_risk_factors(context, patient_data)
                    })
                
                # Non-serious (efficacy changes)
                else:
                    if 'efficacy' in context_lower or 'effectiveness' in context_lower or \
                       'increased levels' in context_lower or 'decreased levels' in context_lower:
                        non_serious_interactions.append({
                            'medicine': medicine_name,
                            'interacting_drug': med,
                            'interaction_type': 'non-serious',
                            'context': context,
                            'risk_factors': []
                        })
        
        return {
            'contraindicated': contraindicated,
            'lt_interactions': lt_interactions,
            'serious_interactions': serious_interactions,
            'non_serious_interactions': non_serious_interactions
        }

def _clean_serious_adr_name(self, text: str) -> str:
        """Clean up serious ADR name from statement"""
        text = text.strip()
        
        # Remove leading/trailing punctuation
        text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
        
        # Remove parenthetical references like "(5.2)" or "[see Warnings and Precautions (5.3)]"
        text = re.sub(r'\[see[^\]]*\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(see[^\)]*\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\d+\.?\d*\)', '', text)
        text = re.sub(r'\[[\d\.]+\]', '', text)
        
        # Remove "see section X" type references
        text = re.sub(r'\s*see\s+section\s+\d+.*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*see\s+warnings.*$', '', text, flags=re.IGNORECASE)
        
        text = text.strip()
        
        # If too short after cleaning, return None
        if len(text) < 5:
            return None
        
        return text.title()
    
    
def _extract_interaction_risk_factors(self, context: str, patient_data: Dict[str, Any]) -> List[str]:
        """Extract risk factors for interactions (includes medical history)"""
        
        patient = patient_data.get('patient', {})
        context_lower = context.lower()
        
        risk_factors = []
        
        # Build list of patient conditions
        patient_conditions = []
        if patient.get('condition'):
            patient_conditions.append(patient.get('condition', '').lower())
        if patient.get('diagnosis'):
            patient_conditions.append(patient.get('diagnosis', '').lower())
        
        # Extract from MedicalHistory
        medical_history = patient_data.get('MedicalHistory', [])
        for history in medical_history:
            if history.get('status') == 'Active':
                condition_name = history.get('diagnosisName', '').lower()
                if condition_name:
                    patient_conditions.append(condition_name)
        
        # Check for medical conditions mentioned in FDA context
        for risk_type, keywords in self.risk_factor_patterns.items():
            if any(kw in context_lower for kw in keywords):
                # Check if patient has this condition
                for patient_condition in patient_conditions:
                    if any(kw in patient_condition for kw in keywords):
                        risk_factors.append(f"{risk_type} condition")
                        break
        
        return list(set(risk_factors))