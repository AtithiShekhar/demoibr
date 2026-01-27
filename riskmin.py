import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import re
from typing import Dict, List, Any, Optional
import google.generativeai as genai
import glob

# Load environment variables
load_dotenv()

class Step4_RMM_Generator:
    """
    Step 4: Risk Minimization Measures (RMM) Generator
    Uses Factor 3.2 & 3.3 output + FDA USPI + Gemini Flash 2.0 AI
    """
    
    def __init__(self):
        """Initialize with API keys"""
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"
        
        # Configure Gemini
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")
        
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        print(f"✓ Gemini Flash 2.0 initialized")
    
    # ============================================================================
    # PART 1: EXTRACT FDA SECTIONS
    # ============================================================================
    
    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extract FDA USPI sections"""
        try:
            search_variants = [medicine_name]
            
            medicine_lower = medicine_name.lower()
            if 'lithium' in medicine_lower:
                search_variants = ['lithium', 'lithium carbonate']
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
            label_data = all_results[0]
            for result in all_results:
                generic_names = result.get('openfda', {}).get('generic_name', [])
                if len(generic_names) == 1:
                    if generic_names[0].lower() == medicine_lower or medicine_lower in generic_names[0].lower():
                        label_data = result
                        break
            
            sections = {
                'drug_name': medicine_name,
                'warnings_and_cautions': self._extract_text(label_data, 'warnings_and_cautions'),
                'warnings': self._extract_text(label_data, 'warnings'),
                'adverse_reactions': self._extract_text(label_data, 'adverse_reactions'),
                'drug_interactions': self._extract_text(label_data, 'drug_interactions'),
                'dosage_and_administration': self._extract_text(label_data, 'dosage_and_administration')
            }
            
            return sections
            
        except Exception as e:
            print(f"Error extracting FDA data for {medicine_name}: {str(e)}")
            return None
    
    def _extract_text(self, label_data: Dict[str, Any], field_name: str) -> Optional[str]:
        """Helper to extract text from FDA label field"""
        field_data = label_data.get(field_name, [])
        if field_data and len(field_data) > 0:
            return "\n\n".join(field_data)
        return None
    
    # ============================================================================
    # PART 2: EXTRACT SECTION 5 MONITORING INSTRUCTIONS
    # ============================================================================
    
    def extract_section_5_monitoring(
        self, 
        adr_name: str, 
        section_5_text: str
    ) -> str:
        """
        Extract specific monitoring instructions from Section 5 for this ADR
        """
        
        if not section_5_text:
            return "NA"
        
        section_5_lower = section_5_text.lower()
        adr_lower = adr_name.lower()
        
        # Search for ADR-specific monitoring instructions
        adr_variations = [adr_lower]
        
        # Add variations
        if 'hepatotoxicity' in adr_lower or 'hepatic' in adr_lower or 'liver' in adr_lower:
            adr_variations.extend(['hepat', 'liver', 'lft', 'transaminase', 'alt', 'ast'])
        elif 'pulmonary' in adr_lower or 'lung' in adr_lower:
            adr_variations.extend(['pulmonary', 'lung', 'chest x-ray', 'pft', 'respiratory'])
        elif 'renal' in adr_lower or 'kidney' in adr_lower:
            adr_variations.extend(['renal', 'kidney', 'creatinine', 'egfr'])
        elif 'cardiac' in adr_lower or 'heart' in adr_lower:
            adr_variations.extend(['cardiac', 'heart', 'ecg', 'qt', 'arrhythmia'])
        elif 'thyroid' in adr_lower:
            adr_variations.extend(['thyroid', 'tsh', 't4', 't3'])
        elif 'hypotension' in adr_lower or 'blood pressure' in adr_lower:
            adr_variations.extend(['blood pressure', 'bp', 'hypotension'])
        elif 'lactic acidosis' in adr_lower:
            adr_variations.extend(['lactic acidosis', 'lactate', 'acidosis', 'renal function'])
        elif 'visual' in adr_lower or 'optic' in adr_lower or 'eye' in adr_lower:
            adr_variations.extend(['ophthalmic', 'visual', 'eye', 'vision', 'corneal'])
        
        # Try to find relevant section
        relevant_section = ""
        
        for variation in adr_variations:
            if variation in section_5_lower:
                # Extract context around this variation (500 chars)
                pos = section_5_lower.find(variation)
                if pos != -1:
                    start = max(0, pos - 250)
                    end = min(len(section_5_text), pos + 250)
                    relevant_section = section_5_text[start:end]
                    break
        
        if not relevant_section:
            return "NA"
        
        # Extract monitoring-specific sentences
        monitoring_keywords = [
            'monitor', 'obtain', 'measure', 'check', 'assess', 'evaluate',
            'baseline', 'periodic', 'regularly', 'every', 'before', 'during',
            'test', 'examination', 'screening'
        ]
        
        sentences = re.split(r'[.!?]\s+', relevant_section)
        monitoring_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(kw in sentence_lower for kw in monitoring_keywords):
                # Clean up the sentence
                sentence = sentence.strip()
                if len(sentence) > 20:  # Ignore very short fragments
                    monitoring_sentences.append(sentence)
        
        if monitoring_sentences:
            # Return the most relevant monitoring instruction
            return '. '.join(monitoring_sentences[:2])  # Max 2 sentences
        
        return "NA"
    
    # ============================================================================
    # PART 3: AI-GENERATED PROACTIVE ACTIONS (SYMPTOMS TO MONITOR)
    # ============================================================================
    
    def generate_proactive_actions(
        self,
        medicine: str,
        adr_name: str,
        fda_sections: Dict[str, Any]
    ) -> str:
        """
        Use Gemini Flash 2.0 to generate symptoms to monitor
        """
        
        section_5 = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
        section_6 = fda_sections.get('adverse_reactions', '')
        
        prompt = f"""You are a clinical pharmacovigilance expert. Based on the FDA USPI documentation for {medicine}, identify the specific clinical signs and symptoms that healthcare providers and patients should monitor for the adverse drug reaction: {adr_name}.

FDA Section 5 Warnings and Precautions (excerpt):
{section_5[:3000] if section_5 else 'Not available'}

FDA Section 6 Adverse Reactions (excerpt):
{section_6[:3000] if section_6 else 'Not available'}

ADR to monitor: {adr_name}

TASK: Provide a comprehensive, comma-separated list of specific symptoms and signs that should be monitored. Include:
1. Early warning signs (prodromal symptoms)
2. Key clinical manifestations
3. Observable physical signs
4. Laboratory abnormalities (if mentioned)

EXAMPLES:
- For Hepatotoxicity: Fatigue, Malaise, Anorexia (loss of appetite), Nausea, Vomiting, Right upper quadrant abdominal pain or discomfort, Low-grade fever, Jaundice (yellowing of skin or eyes), Dark urine, Pale / Clay-colored stools, Pruritus (itching)
- For Pulmonary toxicity: Dyspnea (shortness of breath), initially on exertion, Dry cough (non-productive), Fatigue, Chest tightness, Reduced exercise tolerance, Mild fever, Persistent or worsening dyspnea at rest, Tachypnea (rapid breathing), Hypoxia (low oxygen saturation)
- For Hypotension: Dizziness, Light headedness, Syncope, Fatigue, Blurred vision
- For TEN: Fever, Rash, Mucosal ulcers, Eye redness, Skin pain or blistering

CRITICAL RULES:
1. Return ONLY the comma-separated symptom list
2. No introductory text, no explanations
3. Use proper medical terminology with clarifications in parentheses when helpful
4. Be comprehensive but focused on clinically observable/reportable symptoms
5. Order symptoms from early/common to severe/less common

Your response (symptoms only):"""

        try:
            response = self.model.generate_content(prompt)
            symptoms = response.text.strip()
            
            # Clean up response
            symptoms = symptoms.replace('\n', ', ')
            symptoms = re.sub(r'\s*,\s*', ', ', symptoms)
            
            # Remove any leading "Symptoms:" or similar
            symptoms = re.sub(r'^(symptoms?|signs?|monitor|to monitor):\s*', '', symptoms, flags=re.IGNORECASE)
            
            return symptoms
            
        except Exception as e:
            print(f"Error generating proactive actions: {str(e)}")
            # Fallback to basic list
            return f"Monitor patient for signs and symptoms of {adr_name}"
    
    # ============================================================================
    # PART 4: AI-SELECTED IMMEDIATE ACTIONS
    # ============================================================================
    
    def select_immediate_actions(
        self,
        medicine: str,
        adr_name: str,
        risk_type: str,
        fda_sections: Dict[str, Any],
        is_drug_interaction: bool = False
    ) -> Dict[str, str]:
        """
        Use Gemini Flash 2.0 + Rules to select appropriate immediate actions
        """
        
        section_5 = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
        dosage_info = fda_sections.get('dosage_and_administration', '')
        
        # STRICT RULES for certain ADRs
        strict_rules = {
            'lactic acidosis': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'stevens-johnson syndrome': 'Discontinuation with initiation of better alternatives in safety and efficacy AND/OR initiation of required supplementations',
            'toxic epidermal necrolysis': 'Discontinuation with initiation of better alternatives in safety and efficacy AND/OR initiation of required supplementations',
            'anaphylaxis': 'Discontinuation with initiation of better alternatives in safety and efficacy AND/OR initiation of required supplementations',
            'anaphylactic': 'Discontinuation with initiation of better alternatives in safety and efficacy AND/OR initiation of required supplementations',
            'agranulocytosis': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'aplastic anemia': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'acute liver failure': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'hepatic failure': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'respiratory failure': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'cardiac arrest': 'Discontinuation with initiation of better alternatives in safety and efficacy',
            'ventricular fibrillation': 'Dose optimisation, or temporary interruption, or discontinuation with initiation of better alternatives in safety and efficacy',
        }
        
        # Check if this ADR has a strict rule
        adr_lower = adr_name.lower()
        for key, action in strict_rules.items():
            if key in adr_lower:
                return {
                    'action': action,
                    'reasoning': f'{adr_name} is a life-threatening emergency requiring immediate intervention as per FDA guidelines.'
                }
        
        # Use AI for other cases
        prompt = f"""You are a clinical pharmacology expert. Recommend the appropriate immediate action(s) for managing this adverse drug reaction.

Medicine: {medicine}
ADR: {adr_name}
Risk Type: {risk_type}
Is Drug-Drug Interaction: {is_drug_interaction}

FDA Section 5 Warnings and Precautions (excerpt):
{section_5[:2000] if section_5 else 'Not available'}

FDA Dosage and Administration (excerpt):
{dosage_info[:1000] if dosage_info else 'Not available'}

AVAILABLE OPTIONS (select one or more):
1. Dose optimisation
2. Temporary interruption
3. Discontinuation with initiation of better alternatives in safety and efficacy
4. Initiation of required supplementations

SELECTION CRITERIA:
- **Dose optimisation**: Choose if the ADR is dose-dependent and reducing dose may mitigate risk while maintaining efficacy
- **Temporary interruption**: Choose if the ADR resolves upon temporary drug withdrawal and can be restarted later
- **Discontinuation**: Choose if the ADR is irreversible, life-threatening, or severe enough to warrant permanent cessation
- **Supplementations**: Choose if the ADR is due to drug-induced deficiency (e.g., Vitamin B12 deficiency with Metformin) OR if supportive care is needed (e.g., for TEN/SJS)

COMBINATION RULES:
- Use "AND/OR" when multiple actions may be appropriate
- Use "or" when alternatives exist
- For drug interactions: often "discontinuation" or "dose adjustment" of one drug

EXAMPLES:
- Hepatotoxicity (severe): "Discontinuation with initiation of better alternatives in safety and efficacy"
- Hypotension (mild-moderate): "Dose optimisation, or temporary interruption, or discontinuation with initiation of better alternatives in safety and efficacy"
- Vitamin B12 Deficiency: "Initiation of required supplementations"
- TEN/SJS: "Discontinuation with initiation of better alternatives in safety and efficacy AND/OR initiation of required supplementations"
- Pulmonary toxicity (dose-dependent): "Dose optimisation, or discontinuation with initiation of better alternatives in safety and efficacy"

RESPOND IN THIS EXACT FORMAT:
ACTION: [Your selected action(s) using exact phrasing from options above]
REASONING: [One concise sentence explaining why]

Your response:"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse response
            action_match = re.search(r'ACTION:\s*(.+?)(?:\n|REASONING:)', response_text, re.IGNORECASE | re.DOTALL)
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE | re.DOTALL)
            
            if action_match and reasoning_match:
                action = action_match.group(1).strip()
                reasoning = reasoning_match.group(1).strip()
                
                return {
                    'action': action,
                    'reasoning': reasoning
                }
            else:
                # Fallback parsing
                lines = response_text.split('\n')
                action = lines[0].replace('ACTION:', '').strip() if lines else ''
                reasoning = lines[1].replace('REASONING:', '').strip() if len(lines) > 1 else ''
                
                return {
                    'action': action or 'Discontinuation with initiation of better alternatives in safety and efficacy',
                    'reasoning': reasoning or f'Based on severity of {adr_name}'
                }
            
        except Exception as e:
            print(f"Error selecting immediate actions: {str(e)}")
            # Fallback based on risk type
            if 'LT' in risk_type or 'Fatal' in risk_type:
                return {
                    'action': 'Discontinuation with initiation of better alternatives in safety and efficacy',
                    'reasoning': f'Life-threatening nature of {adr_name} requires immediate cessation'
                }
            else:
                return {
                    'action': 'Dose optimisation, or temporary interruption',
                    'reasoning': f'Serious ADR requiring clinical monitoring and possible intervention'
                }
    
    # ============================================================================
    # PART 5: GENERATE RMM TABLE FROM FACTOR 3.2 & 3.3 OUTPUT
    # ============================================================================
    
    def generate_rmm_table(
        self,
        factor_output_file: str
    ) -> Dict[str, Any]:
        """
        Main function: Generate complete RMM table from Factor 3.2 & 3.3 output
        """
        
        print("\n" + "=" * 80)
        print("STEP 4: RISK MINIMIZATION MEASURES (RMM) GENERATION")
        print("=" * 80 + "\n")
        
        # Load Factor 3.2 & 3.3 output
        try:
            with open(factor_output_file, 'r') as f:
                factor_output = json.load(f)
        except FileNotFoundError:
            print(f"❌ Error: {factor_output_file} not found!")
            return {}
        
        patient_data = factor_output.get('patient', {})
        medications = factor_output.get('medications', [])
        
        # Extract FDA sections for all medications
        print("Extracting FDA USPI sections...")
        fda_data = {}
        for i, med in enumerate(medications, 1):
            print(f"[{i}/{len(medications)}] {med}...")
            sections = self.extract_fda_sections(med)
            fda_data[med] = sections
            time.sleep(0.3)
        
        print("\nGenerating RMM entries with AI...\n")
        
        rmm_entries = []
        
        # Process Factor 3.2.1: Life-Threatening ADRs
        lt_adrs = factor_output.get('factor_3_2', {}).get('LT_ADRs', {})
        
        for medicine, data in lt_adrs.items():
            print(f"Processing {medicine} - LT ADRs...")
            fda_sections = fda_data.get(medicine)
            
            if not fda_sections:
                print(f"  ⚠️  No FDA data available, skipping...")
                continue
            
            all_adrs = data.get('with_risk_factors', []) + data.get('without_risk_factors', [])
            
            for adr in all_adrs:
                adr_name = adr['adr_name']
                print(f"  • {adr_name}...")
                
                # Extract Section 5 monitoring
                section_5_text = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
                section_5_extract = self.extract_section_5_monitoring(adr_name, section_5_text)
                
                # Generate proactive actions (symptoms to monitor)
                proactive_actions = self.generate_proactive_actions(medicine, adr_name, fda_sections)
                time.sleep(1)  # Rate limiting for Gemini API
                
                # Select immediate actions
                immediate_actions_result = self.select_immediate_actions(
                    medicine, adr_name, 'LT/Fatal ADR', fda_sections
                )
                time.sleep(1)  # Rate limiting
                
                rmm_entry = {
                    'medicine': medicine,
                    'risk_type': 'LT/Fatal ADR',
                    'risk_description': adr_name,
                    'section_5_warnings_and_precautions_extract': section_5_extract,
                    'proactive_actions_symptoms_to_monitor': proactive_actions,
                    'immediate_actions_required': immediate_actions_result['action'],
                    'immediate_actions_reasoning': immediate_actions_result['reasoning']
                }
                
                rmm_entries.append(rmm_entry)
        
        # Process Factor 3.2.2: Serious ADRs
        serious_adrs = factor_output.get('factor_3_2', {}).get('Serious_ADRs', {})
        
        for medicine, data in serious_adrs.items():
            print(f"Processing {medicine} - Serious ADRs...")
            fda_sections = fda_data.get(medicine)
            
            if not fda_sections:
                print(f"  ⚠️  No FDA data available, skipping...")
                continue
            
            all_adrs = data.get('with_risk_factors', []) + data.get('without_risk_factors', [])
            
            for adr in all_adrs:
                adr_name = adr['adr_name']
                print(f"  • {adr_name}...")
                
                # Extract Section 5 monitoring
                section_5_text = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
                section_5_extract = self.extract_section_5_monitoring(adr_name, section_5_text)
                
                # Generate proactive actions
                proactive_actions = self.generate_proactive_actions(medicine, adr_name, fda_sections)
                time.sleep(1)
                
                # Select immediate actions
                immediate_actions_result = self.select_immediate_actions(
                    medicine, adr_name, 'Non-LT/Fatal, But Serious ADR', fda_sections
                )
                time.sleep(1)
                
                rmm_entry = {
                    'medicine': medicine,
                    'risk_type': 'Non-LT/Fatal, But Serious ADR',
                    'risk_description': adr_name,
                    'section_5_warnings_and_precautions_extract': section_5_extract,
                    'proactive_actions_symptoms_to_monitor': proactive_actions,
                    'immediate_actions_required': immediate_actions_result['action'],
                    'immediate_actions_reasoning': immediate_actions_result['reasoning']
                }
                
                rmm_entries.append(rmm_entry)
        
        # Process Factor 3.3: Drug-Drug Interactions
        interactions = factor_output.get('factor_3_3', {}).get('interactions', {})
        
        for medicine, data in interactions.items():
            print(f"Processing {medicine} - Drug Interactions...")
            fda_sections = fda_data.get(medicine)
            
            if not fda_sections:
                continue
            
            # Process all interaction types
            all_interactions = (
                data.get('contraindicated', []) +
                data.get('lt_interactions', []) +
                data.get('serious_interactions', []) +
                data.get('non_serious_interactions', [])
            )
            
            for interaction in all_interactions:
                interacting_drug = interaction['interacting_drug']
                interaction_type = interaction['interaction_type']
                
                print(f"  • Interaction with {interacting_drug} ({interaction_type})...")
                
                # Determine risk type for interaction
                if interaction_type == 'contraindicated':
                    risk_type = 'Contraindicated Drug-Drug Interaction'
                elif interaction_type == 'life-threatening':
                    risk_type = 'LT Drug-Drug Interaction'
                elif interaction_type == 'serious':
                    risk_type = 'Serious Drug-Drug Interaction'
                else:
                    risk_type = 'Non-serious Drug-Drug Interaction'
                
                risk_description = f"Drug interaction: {medicine} + {interacting_drug}"
                
                # Extract Section 7 (Drug Interactions) monitoring
                section_7_text = fda_sections.get('drug_interactions', '')
                section_5_extract = self.extract_section_5_monitoring(interacting_drug, section_7_text)
                
                if section_5_extract == "NA" and section_7_text:
                    # Try to extract any relevant text
                    pos = section_7_text.lower().find(interacting_drug.lower())
                    if pos != -1:
                        start = max(0, pos - 150)
                        end = min(len(section_7_text), pos + 150)
                        section_5_extract = section_7_text[start:end].strip()
                
                # Generate proactive actions for the interaction
                interaction_prompt_sections = {
                    'warnings_and_cautions': f"Drug Interaction Context: {interaction['context']}",
                    'adverse_reactions': '',
                    'drug_interactions': section_7_text
                }
                
                proactive_actions = self.generate_proactive_actions(
                    medicine, 
                    f"interaction with {interacting_drug}", 
                    interaction_prompt_sections
                )
                time.sleep(1)
                
                # Select immediate actions for interaction
                immediate_actions_result = self.select_immediate_actions(
                    medicine,
                    f"interaction with {interacting_drug}",
                    risk_type,
                    interaction_prompt_sections,
                    is_drug_interaction=True
                )
                time.sleep(1)
                
                rmm_entry = {
                    'medicine': medicine,
                    'risk_type': risk_type,
                    'risk_description': risk_description,
                    'section_5_warnings_and_precautions_extract': section_5_extract,
                    'proactive_actions_symptoms_to_monitor': proactive_actions,
                    'immediate_actions_required': immediate_actions_result['action'],
                    'immediate_actions_reasoning': immediate_actions_result['reasoning']
                }
                
                rmm_entries.append(rmm_entry)
        
        # Generate final output
        rmm_output = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': patient_data,
            'medications': medications,
            'rmm_table': rmm_entries,
            'total_rmm_entries': len(rmm_entries)
        }
        
        return rmm_output
    
    def print_rmm_report(self, rmm_output: Dict[str, Any]):
        """Print formatted RMM report"""
        
        print("\n" + "=" * 80)
        print("STEP 4: RISK MINIMIZATION MEASURES (RMM) TABLE")
        print("=" * 80)
        
        patient = rmm_output.get('patient', {})
        print(f"\nPatient: {patient.get('age')}y {patient.get('gender')}")
        print(f"Medications: {', '.join(rmm_output.get('medications', []))}")
        print(f"Total RMM Entries: {rmm_output.get('total_rmm_entries', 0)}")
        
        print("\n" + "=" * 80)
        
        for i, entry in enumerate(rmm_output.get('rmm_table', []), 1):
            print(f"\n[{i}] {entry['medicine']} - {entry['risk_description']}")
            print(f"    Risk Type: {entry['risk_type']}")
            print(f"    Section 5 Extract: {entry['section_5_warnings_and_precautions_extract']}")
            print(f"    Symptoms to Monitor: {entry['proactive_actions_symptoms_to_monitor'][:200]}...")
            print(f"    Immediate Actions: {entry['immediate_actions_required']}")
            print(f"    Reasoning: {entry['immediate_actions_reasoning']}")
        
        print("\n" + "=" * 80 + "\n")


def find_latest_factor_output():
    """Find the most recent Factor 3.2 & 3.3 output file"""
    # Look for files matching the pattern
    pattern = 'factor_3_2_3_3_report*.json'
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Sort by modification time, get the most recent
    latest_file = max(files, key=os.path.getmtime)
    return latest_file


def main():
    """Main execution"""
    
    print("\n" + "=" * 80)
    print("STEP 4: RISK MINIMIZATION MEASURES (RMM) GENERATOR")
    print("Powered by Gemini Flash 2.0")
    print("=" * 80)
    
    # Initialize generator
    try:
        generator = Step4_RMM_Generator()
    except ValueError as e:
        print(f"\n❌ {str(e)}")
        print("Please add GEMINI_API_KEY to your .env file")
        return
    
    # Find the latest Factor 3.2 & 3.3 output file
    factor_output_file = find_latest_factor_output()
    
    if not factor_output_file:
        print(f"\n⚠️  No Factor 3.2 & 3.3 output file found!")
        print("Please run Factor 3.2 & 3.3 analysis first to generate the input file.")
        print("Or specify the correct filename in the code.")
        return
    
    print(f"\nUsing input file: {factor_output_file}\n")
    
    # Generate RMM table
    rmm_output = generator.generate_rmm_table(factor_output_file)
    
    # Print report
    generator.print_rmm_report(rmm_output)
    
    # Save to JSON
    output_file = f"step4_rmm_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(rmm_output, f, indent=2)
    
    print(f"✓ RMM table saved to: {output_file}\n")


if __name__ == "__main__":
    main()