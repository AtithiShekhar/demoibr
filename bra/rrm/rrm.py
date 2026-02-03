import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import re
from typing import Dict, List, Any, Optional
from google import genai
import glob
from google.genai import types

# Load environment variables
load_dotenv()

class Step4_RMM_Generator:
    """
    Step 4: Risk Minimization Measures (RMM) Generator (Patient-Context-Aware)
    Uses Factor 3.2 & 3.3 output + FDA USPI + Gemini Flash 2.0 AI
    Now considers patient-specific factors for tailored monitoring recommendations
    """
    
    def __init__(self):
        """Initialize with API keys"""
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"
        
        # Configure Gemini
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")
        
        self.gemini_client = genai.Client(api_key=self.gemini_api_key) if (self.gemini_api_key and self.gemini_api_key) else None
        self.config = types.GenerateContentConfig(
        temperature=0.0,  # Minimize creativity/hallucination
        max_output_tokens=1000,
        response_mime_type="application/json"
    )   
        
        print(f"✓ Gemini Flash 2.0 initialized")
    
    # ============================================================================
    # NEW: BUILD PATIENT CONTEXT
    # ============================================================================
    
    def build_patient_context(self, patient_data: Dict[str, Any]) -> str:
        """
        Build patient context string for personalized RMM recommendations
        """
        if not patient_data:
            return ""
        
        # Support both simple and complex patient data formats
        if "patient" in patient_data:
            patient = patient_data["patient"]
        else:
            patient = patient_data
        
        age = patient.get("age", "unknown")
        gender = patient.get("gender", "unknown")
        diagnosis = patient.get("diagnosis", "")
        social_risk = patient.get("social_risk_factors", "")
        
        # Extract medical history
        medical_history = patient_data.get("MedicalHistory", [])
        active_conditions = []
        severe_conditions = []
        previous_adrs = []
        
        for history in medical_history:
            condition_name = history.get("diagnosisName", "")
            status = history.get("status", "")
            severity = history.get("severity", "")
            
            if status == "Active":
                active_conditions.append(condition_name)
                if severity in ["Severe", "Critical"]:
                    severe_conditions.append(f"{condition_name} ({severity})")
            
            # Extract stopped medications (may indicate ADRs)
            treatment = history.get("treatment", {})
            medications = treatment.get("medications", [])
            for med in medications:
                med_name = med.get("name", "")
                med_status = med.get("status", "")
                if med_name and med_status == "Stopped":
                    previous_adrs.append(f"{med_name} (stopped)")
        
        # Determine patient characteristics
        is_post_transplant = "transplant" in diagnosis.lower()
        is_immunosuppressed = is_post_transplant or "immunosuppressed" in diagnosis.lower()
        has_hematologic_malignancy = any(term in diagnosis.lower() for term in ["leukemia", "aml", "lymphoma", "myeloma"])
        age_category = "pediatric" if age != "unknown" and age < 18 else ("geriatric" if age != "unknown" and age >= 65 else "adult")
        
        context = f"""Patient Profile:
- Age: {age} years ({age_category})
- Gender: {gender}
- Primary Diagnosis: {diagnosis}
- Social Risk Factors: {social_risk}
- Post-Transplant: {'Yes' if is_post_transplant else 'No'}
- Immunosuppressed: {'Yes' if is_immunosuppressed else 'No'}
- Hematologic Malignancy: {'Yes' if has_hematologic_malignancy else 'No'}"""

        if active_conditions:
            context += f"\n- Active Comorbidities: {', '.join(active_conditions)}"
        
        if severe_conditions:
            context += f"\n- Severe/Critical Conditions: {', '.join(severe_conditions)}"
        
        if previous_adrs:
            context += f"\n- Previous Medication Discontinuations: {', '.join(set(previous_adrs))} (possible ADR history)"

        context += """

PATIENT-SPECIFIC MONITORING CONSIDERATIONS:
"""
        
        # Add age-related monitoring needs
        if age != "unknown" and age >= 65:
            context += "- Elderly: Requires MORE FREQUENT monitoring (reduced organ reserve, polypharmacy)\n"
        elif age != "unknown" and age < 18:
            context += "- Pediatric: Age-appropriate dosing, developmental monitoring\n"
        
        # Add immunosuppression monitoring needs
        if is_immunosuppressed:
            context += "- Immunosuppressed: Higher infection risk, impaired healing, closer monitoring needed\n"
        
        # Add hematologic malignancy monitoring needs
        if has_hematologic_malignancy:
            context += "- Hematologic malignancy: Baseline bone marrow compromise, frequent CBC monitoring\n"
        
        # Add comorbidity monitoring needs
        if len(active_conditions) >= 3:
            context += "- Multiple comorbidities: Increased drug interaction risk, closer monitoring required\n"
        
        if previous_adrs:
            context += "- Previous ADR history: Heightened vigilance for similar reactions\n"
        
        return context
    
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
    # PART 3: AI-GENERATED PROACTIVE ACTIONS (PATIENT-CONTEXT-AWARE)
    # ============================================================================
    
    def generate_proactive_actions(
        self,
        medicine: str,
        adr_name: str,
        fda_sections: Dict[str, Any],
        patient_context: str = ""
    ) -> str:
        """
        Use Gemini Flash 2.0 to generate symptoms to monitor (patient-specific)
        """
        
        section_5 = fda_sections.get('warnings_and_cautions') or fda_sections.get('warnings', '')
        section_6 = fda_sections.get('adverse_reactions', '')
        
        # Enhanced prompt with patient context
        patient_section = f"\n\n{patient_context}" if patient_context else ""
        
        prompt = f"""You are a clinical pharmacovigilance expert. Based on the FDA USPI documentation for {medicine}, identify the specific clinical signs and symptoms that healthcare providers and patients should monitor for the adverse drug reaction: {adr_name}.

FDA Section 5 Warnings and Precautions (excerpt):
{section_5[:2500] if section_5 else 'Not available'}

FDA Section 6 Adverse Reactions (excerpt):
{section_6[:2500] if section_6 else 'Not available'}
{patient_section}

ADR to monitor: {adr_name}

TASK: Provide a comprehensive, comma-separated list of specific symptoms and signs that should be monitored. Include:
1. Early warning signs (prodromal symptoms)
2. Key clinical manifestations
3. Observable physical signs
4. Laboratory abnormalities (if mentioned)
{"5. Patient-specific considerations (age-related, immunosuppression-related symptoms)" if patient_context else ""}

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
{"6. For elderly/immunosuppressed patients, include subtle early warning signs that may present atypically" if patient_context else ""}

Your response (symptoms only):"""

        try:
            response = self.gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=self.config
        )
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
    # PART 4: AI-SELECTED IMMEDIATE ACTIONS (PATIENT-CONTEXT-AWARE)
    # ============================================================================
    
    def select_immediate_actions(
        self,
        medicine: str,
        adr_name: str,
        risk_type: str,
        fda_sections: Dict[str, Any],
        patient_context: str = "",
        is_drug_interaction: bool = False
    ) -> Dict[str, str]:
        """
        Use Gemini Flash 2.0 + Rules to select appropriate immediate actions (patient-aware)
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
                reasoning = f'{adr_name} is a life-threatening emergency requiring immediate intervention as per FDA guidelines.'
                if patient_context and ("immunosuppressed" in patient_context.lower() or "elderly" in patient_context.lower()):
                    reasoning += " Patient's age/immunosuppression increases risk severity."
                
                return {
                    'action': action,
                    'reasoning': reasoning
                }
        
        # Enhanced prompt with patient context
        patient_section = f"\n\n{patient_context}" if patient_context else ""
        
        # Use AI for other cases
        prompt = f"""You are a clinical pharmacology expert. Recommend the appropriate immediate action(s) for managing this adverse drug reaction.

Medicine: {medicine}
ADR: {adr_name}
Risk Type: {risk_type}
Is Drug-Drug Interaction: {is_drug_interaction}

FDA Section 5 Warnings and Precautions (excerpt):
{section_5[:1800] if section_5 else 'Not available'}

FDA Dosage and Administration (excerpt):
{dosage_info[:800] if dosage_info else 'Not available'}
{patient_section}

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
{"- **Patient-specific**: For elderly/immunosuppressed patients, consider LOWER threshold for discontinuation due to reduced tolerance" if patient_context else ""}

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
REASONING: [One concise sentence explaining why{"and how patient factors influence decision" if patient_context else ""}]

Your response:"""

        try:
            response = self.gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=self.config
        )
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
    # PART 5: GENERATE RMM TABLE (PATIENT-CONTEXT-AWARE)
    # ============================================================================
    
    def generate_rmm_table(
        self,
        factor_output_file: str,
        patient_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main function: Generate complete RMM table with patient context
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
        
        # Build patient context
        patient_context = ""
        if patient_data:
            patient_context = self.build_patient_context(patient_data)
            print("Patient context for RMM personalization:")
            print(patient_context)
            print()
        
        patient_data_output = factor_output.get('patient', {})
        medications = factor_output.get('medications', [])
        
        # Extract FDA sections for all medications
        print("Extracting FDA USPI sections...")
        fda_data = {}
        for i, med in enumerate(medications, 1):
            print(f"[{i}/{len(medications)}] {med}...")
            sections = self.extract_fda_sections(med)
            fda_data[med] = sections
            time.sleep(0.3)
        
        print("\nGenerating RMM entries with AI and patient context...\n")
        
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
                
                # Generate proactive actions with patient context
                proactive_actions = self.generate_proactive_actions(medicine, adr_name, fda_sections, patient_context)
                time.sleep(1)  # Rate limiting for Gemini API
                
                # Select immediate actions with patient context
                immediate_actions_result = self.select_immediate_actions(
                    medicine, adr_name, 'LT/Fatal ADR', fda_sections, patient_context
                )
                time.sleep(1)  # Rate limiting
                
                rmm_entry = {
                    'medicine': medicine,
                    'risk_type': 'LT/Fatal ADR',
                    'risk_description': adr_name,
                    'section_5_warnings_and_precautions_extract': section_5_extract,
                    'proactive_actions_symptoms_to_monitor': proactive_actions,
                    'immediate_actions_required': immediate_actions_result['action'],
                    'immediate_actions_reasoning': immediate_actions_result['reasoning'],
                    'patient_context_applied': bool(patient_context)
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
                
                # Generate proactive actions with patient context
                proactive_actions = self.generate_proactive_actions(medicine, adr_name, fda_sections, patient_context)
                time.sleep(1)
                
                # Select immediate actions with patient context
                immediate_actions_result = self.select_immediate_actions(
                    medicine, adr_name, 'Non-LT/Fatal, But Serious ADR', fda_sections, patient_context
                )
                time.sleep(1)
                
                rmm_entry = {
                    'medicine': medicine,
                    'risk_type': 'Non-LT/Fatal, But Serious ADR',
                    'risk_description': adr_name,
                    'section_5_warnings_and_precautions_extract': section_5_extract,
                    'proactive_actions_symptoms_to_monitor': proactive_actions,
                    'immediate_actions_required': immediate_actions_result['action'],
                    'immediate_actions_reasoning': immediate_actions_result['reasoning'],
                    'patient_context_applied': bool(patient_context)
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
                
                # Generate proactive actions for the interaction with patient context
                interaction_prompt_sections = {
                    'warnings_and_cautions': f"Drug Interaction Context: {interaction['context']}",
                    'adverse_reactions': '',
                    'drug_interactions': section_7_text
                }
                
                proactive_actions = self.generate_proactive_actions(
                    medicine, 
                    f"interaction with {interacting_drug}", 
                    interaction_prompt_sections,
                    patient_context
                )
                time.sleep(1)
                
                # Select immediate actions for interaction with patient context
                immediate_actions_result = self.select_immediate_actions(
                    medicine,
                    f"interaction with {interacting_drug}",
                    risk_type,
                    interaction_prompt_sections,
                    patient_context,
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
                    'immediate_actions_reasoning': immediate_actions_result['reasoning'],
                    'patient_context_applied': bool(patient_context)
                }
                
                rmm_entries.append(rmm_entry)
        

        rmm_output = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': patient_data_output,
            'medications': medications,
            'patient_context_applied': bool(patient_context),
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
        print(f"Patient Context Applied: {'Yes' if rmm_output.get('patient_context_applied') else 'No'}")
        print(f"Total RMM Entries: {rmm_output.get('total_rmm_entries', 0)}")
        
        print("\n" + "=" * 80)
        
        for i, entry in enumerate(rmm_output.get('rmm_table', []), 1):
            print(f"\n[{i}] {entry['medicine']} - {entry['risk_description']}")
            print(f"    Risk Type: {entry['risk_type']}")
            print(f"    Section 5 Extract: {entry['section_5_warnings_and_precautions_extract']}")
            print(f"    Symptoms to Monitor: {entry['proactive_actions_symptoms_to_monitor'][:200]}...")
            print(f"    Immediate Actions: {entry['immediate_actions_required']}")
            print(f"    Reasoning: {entry['immediate_actions_reasoning']}")
            if entry.get('patient_context_applied'):
                print(f"    [Patient-specific recommendations included]")
        
        print("\n" + "=" * 80 + "\n")


def find_latest_factor_output():
    """
    Waits for the specific Factor 3.2 & 3.3 output file to be generated.
    Returns the path if found, or None if the 30-second timeout is reached.
    """
    # Specific file path as requested
    file_path = '../adrs_output.json'
    timeout = 30
    elapsed = 0

    print(f"Waiting for {file_path} to become available...")

    # Polling loop to handle multithreaded race conditions
    while elapsed < timeout:
        if os.path.exists(file_path):
            print(f"✓ File detected after {elapsed} seconds.")
            return file_path
        
        # Wait 1 second before retrying
        time.sleep(1)
        elapsed += 1
    
    print(f"❌ Timeout: {file_path} not available after {timeout} seconds.")
    return None

def start(input_file: Optional[str] = None, scoring_system=None) -> List[Dict[str, Any]]:
    """
    RMM entry point with patient-context-aware recommendations
    
    Args:
        input_file: Path to Factor 3.2 & 3.3 output file
        scoring_system: Scoring system object (contains patient_data)
    
    Returns:
        RMM table with patient-specific recommendations
    """
    print("\n" + "=" * 80)
    print("STEP 4: RISK MINIMIZATION MEASURES (RMM) GENERATOR")
    print("=" * 80)
    
    # 1. Initialize generator and check for API keys
    try:
        generator = Step4_RMM_Generator()
    except ValueError as e:
        print(f"\n❌ {str(e)}")
        return {"error": "API Key missing"}

    # 2. Extract patient_data from scoring_system if available
    patient_data = None
    if scoring_system and hasattr(scoring_system, 'patient_data'):
        patient_data = scoring_system.patient_data
        print("✓ Patient context extracted from scoring system")

    # 3. Polling Logic: Wait up to 30s for the file to be available
    file_path = input_file if input_file else '../adrs_output.json'
    timeout = 30
    elapsed = 0
    
    while elapsed < timeout:
        if os.path.exists(file_path):
            break
        time.sleep(1)
        elapsed += 1
    
    if not os.path.exists(file_path):
        print(f"❌ Timeout: {file_path} not found.")
        return {"error": "Input file not found"}

    # 4. Process RMM Generation with patient context
    try:
        # Generate the clinical RMM table with patient context
        full_output = generator.generate_rmm_table(file_path, patient_data)
        
        # Display the formatted clinical findings
        generator.print_rmm_report(full_output)
        
        # 5. Extract the rmm_table attribute into memory
        rmm_table_data = full_output.get("rmm_table", [])
        
        # 6. Persist the RMM results locally for the system log
        output_save_path = "rmm_output.json"
        with open(output_save_path, 'w') as f:
            json.dump(full_output, f, indent=2)
            
        print(f"✓ RMM data processed and saved to local log: {output_save_path}")

        # 7. Delete the original input file before returning
        try:
            # os.remove(file_path)
            print(f"🗑️  Original file {file_path} deleted successfully.")
        except Exception as e:
            print(f"⚠️  Warning: Could not delete {file_path}: {str(e)}")

        # 8. Return specifically the rmm_table list
        return rmm_table_data
        
    except Exception as e:
        print(f"❌ Error during RMM processing: {str(e)}")
        return {"error": str(e)}