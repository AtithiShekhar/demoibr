"""
iBR Report Generator - Gemini API Integration
Generates patient-context-based monitoring protocols using Gemini AI
"""
import re

from typing import Dict, List, Any, Optional
import json
import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

class GeminiMonitoringProtocolGenerator:
    """Generates concise monitoring protocols using Gemini API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini client
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided. Set GEMINI_API_KEY environment variable.")
        
        # Initialize the modern GenAI Client
        self.client = genai.Client(api_key=self.api_key)
    
    def _call_gemini_api(self, prompt: str) -> str:
        """
        Call Gemini API to generate content using the Google GenAI SDK
        
        Args:
            prompt: The prompt to send to Gemini
            
        Returns:
            Generated text response
        """
        try:
            # Use the SDK client initialized in __init__
            # Model can be "gemini-2.0-flash" or "gemini-1.5-flash"
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    top_k=40,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )

            # The new SDK returns response.text directly if successful
            if response and response.text:
                # Optional: print for debugging similar to your original code
                # print(f'The response received from Gemini is: {response.text}')
                return response.text
            
            return "Error: Gemini API returned an empty response."

        except Exception as e:
            # Catching generic exceptions from the SDK (e.g., Auth, Quota, or Network)
            return f"Error calling Gemini API: {str(e)}"
    
    def _prepare_patient_context(self, patient_info: Dict) -> str:
        """
        Prepare patient context for RAG
        
        Args:
            patient_info: Patient demographic and medical information
            
        Returns:
            Formatted patient context string
        """
        context = "**Patient Information:**\n\n"
        
        # Basic demographics
        context += f"- Age: {patient_info.get('age', 'Unknown')} years\n"
        context += f"- Gender: {patient_info.get('gender', 'Unknown')}\n"
        
        # Current diagnosis
        if patient_info.get('diagnosis'):
            context += f"- Current Diagnosis: {patient_info['diagnosis']}\n"
        
        # Chief complaints
        chief_complaints = patient_info.get('chiefComplaints', [])
        if chief_complaints:
            complaints_list = [f"{c.get('complaint', '')} ({c.get('severity', '')}, {c.get('duration', '')})" 
                             for c in chief_complaints if c.get('complaint')]
            if complaints_list:
                context += f"- Chief Complaints: {', '.join(complaints_list)}\n"
        
        # Current diagnoses
        current_diagnoses = patient_info.get('currentDiagnoses', [])
        if current_diagnoses:
            context += "\n**Current Active Conditions:**\n"
            for dx in current_diagnoses:
                context += f"- {dx.get('diagnosisName', 'Unknown')} (Status: {dx.get('status', 'Unknown')}, Severity: {dx.get('severity', 'Unknown')})\n"
        
        # Medical history
        medical_history = patient_info.get('MedicalHistory', [])
        if medical_history:
            context += "\n**Medical History:**\n"
            for history_item in medical_history:
                diagnosis = history_item.get('diagnosisName', 'Unknown')
                date = history_item.get('diagnosisDate', 'Unknown date')
                status = history_item.get('status', 'Unknown status')
                context += f"- {diagnosis} (Since: {date}, Status: {status})\n"
        
        # Social risk factors
        if patient_info.get('social_risk_factors'):
            context += f"\n**Social Risk Factors:** {patient_info['social_risk_factors']}\n"
        print(f'patient context if {context}')
        return context

    def _prepare_adr_context(self, lt_adrs_list: list) -> str:
        """
        Prepare ADR context for RAG from risk_mitigation_measures list.
        
        Args:
            lt_adrs_list: List of dictionaries containing LT ADR risks
            
        Returns:
            Formatted ADR context string
        """
        if not lt_adrs_list:
            print("online 142")
            return "No specific life-threatening ADRs identified for monitoring."

        context = "**Life-Threatening Adverse Drug Reactions (ADRs) to Monitor:**\n\n"
        
        for adr_entry in lt_adrs_list:
            # 1. Extract data using keys found in your 'risk_mitigation_measures'
            medication = adr_entry.get('medicine', 'Unknown Medication')
            risk_name = adr_entry.get('risk_description', 'Critical Side Effect')
            raw_symptoms = adr_entry.get('proactive_actions_symptoms_to_monitor', '')
            immediate_action = adr_entry.get('immediate_actions_required', 'Contact healthcare provider immediately.')
            reasoning = adr_entry.get('immediate_actions_reasoning', '')

            # 2. Clean the symptom string
            # Your data has strings like '{, "symptoms": "Fever, Fatigue..." }'
            # This helper strips the pseudo-JSON formatting to get a clean list
            clean_symptoms = self._clean_symptom_string(raw_symptoms)

            # 3. Build the context block
            context += f"### Medication: {medication}\n"
            context += f"- **Potential Risk:** {risk_name}\n"
            context += f"- **Symptoms to Watch For:** {clean_symptoms}\n"
            context += f"- **Required Action:** {immediate_action}\n"
            if reasoning:
                context += f"- **Clinical Urgency:** {reasoning}\n"
            context += "\n---\n"
        print(f"the adr context is {context}")
        return context

    def _clean_symptom_string(self, symptom_str: str) -> str:
        """Helper to strip malformed JSON characters from symptom strings."""
        if not symptom_str or symptom_str == 'NA':
            print("return from 174")
            return "Not specified"
        
        # Remove curly braces, brackets, quotes, and the "symptoms" key name
        cleaned = re.sub(r'[\{\}\[\]\"]', '', symptom_str)
        cleaned = cleaned.replace(', symptoms:', '').replace('symptoms:', '')
        
        # Remove leading commas or whitespace left over
        cleaned = cleaned.strip().lstrip(',')
        
        return cleaned.strip()
    
    def _prepare_rmf_context(self, rmf_data: Dict) -> str:
        """
        Prepare Risk Mitigation Feasibility context
        
        Args:
            rmf_data: Risk mitigation feasibility data
            
        Returns:
            Formatted RMF context string
        """
        if not rmf_data:
            print('returnig from197')
            return ""
        
        context = "**Risk Mitigation Information:**\n\n"
        
        # Reversibility data
        reversibility_data = rmf_data.get('risk_reversibility_risk_tolerability', {})
        if reversibility_data:
            context += "**Reversibility Assessment:**\n"
            for key, value in reversibility_data.items():
                adr_name = key.split(' - ')[1] if ' - ' in key else key
                classification = value.get('classification', 'Unknown')
                reasoning = value.get('reasoning', '')
                
                context += f"- {adr_name}: {classification}\n"
                if reasoning:
                    context += f"  Reasoning: {reasoning[:200]}...\n" if len(reasoning) > 200 else f"  Reasoning: {reasoning}\n"
        
        # Preventability data
        preventability_data = rmf_data.get('risk_preventability', {})
        if preventability_data:
            context += "\n**Preventability Assessment:**\n"
            for key, value in preventability_data.items():
                adr_name = key.split(' - ')[1] if ' - ' in key else key
                classification = value.get('classification', 'Unknown')
                prevention_measures = value.get('prevention_measures', [])
                
                context += f"- {adr_name}: {classification}\n"
                if prevention_measures:
                    context += f"  Prevention: {', '.join(prevention_measures[:3])}\n"
        # print(f'the ')
        return context
    
    def generate_monitoring_protocol(self, analysis_results: Dict, patient_info: Dict) -> str:
        """
        Generate patient-friendly monitoring protocol using Gemini API
        
        Args:
            analysis_results: Complete analysis results with LT ADRs
            patient_info: Patient demographic and medical information
            
        Returns:
            Formatted monitoring protocol string
        """
        # Extract LT ADRs data
        # print(f'analysis result are{analysis_results}')
        lt_adrs_list = analysis_results.get("risk_mitigation_measures", [])        
        print(f'the lt_adrs are {lt_adrs_list}')
        if not lt_adrs_list:
         print("returning from there")
         return ("**Monitoring Protocol**\n\n"
               "Continue standard medication regimen as prescribed. "
               "Report any unusual symptoms to your healthcare provider.")
        
        # Extract RMF data if available

        rmf_data = analysis_results.get("factor_3_4_risk_mitigation_feasibility", {})
        print(f'rmf data is {rmf_data}')
        # Prepare context for RAG
        patient_context = self._prepare_patient_context(patient_info)
        adr_context = self._prepare_adr_context(lt_adrs_list)
        rmf_context = self._prepare_rmf_context(rmf_data)
        
        # Create prompt for Gemini
        prompt = f"""You are a medical AI assistant helping to create a patient-friendly monitoring protocol for medications with life-threatening adverse drug reactions (ADRs).

{patient_context}

{adr_context}

{rmf_context}

**Task:**
Generate a concise, patient-friendly monitoring protocol in the EXACT format shown below. The protocol should:

1. Be tailored to THIS SPECIFIC PATIENT's medical conditions and risk factors
2. Categorize symptoms by body system (e.g., Breathing Problems, Urine/Kidney Problems, Heart Problems, Liver Problems, Skin Problems, Stomach/Digestive Problems, etc.)
3. Use simple, clear language that patients can understand
4. Add context-specific notes when the patient has relevant existing conditions (e.g., "especially important due to existing kidney condition")
5. Recommend specific lab tests based on the ADRs and patient's medical history
6. Organize lab tests into categories (KFTs, LFTs, Blood Tests, Cardiac Markers, etc.)

**REQUIRED FORMAT (follow this EXACTLY):**

**Monitoring Protocol**

Please be aware and monitor for the following signs or symptoms and report immediately to your healthcare provider:

**Breathing Problems** : Trouble breathing, Chest tightness, Loud wheezing sound

**Urine / Kidney Problems** : Passing very little urine, Swelling of feet or face (especially important due to existing kidney condition)

**Heart Problems** : Very fast heartbeat, Feeling faint or dizzy, Swelling of legs

**Liver Problems** : Yellow eyes or yellow skin, Dark colored urine, Severe vomiting, Pain on the right side of stomach

Please do the following lab tests and share reports with your healthcare provider:

● **Kidney Function Tests (KFTs)**
  ○ Serum creatinine
  ○ Blood urea

● **Liver Function Tests (LFTs)**
  ○ AST (SGOT), ALT (SGPT), Bilirubin

**Frequency**

● Every 2 weeks, or as advised by your doctor

**IMPORTANT INSTRUCTIONS:**
- Only include symptom categories that are RELEVANT to the ADRs listed above
- Add patient-context notes (in parentheses) ONLY when the patient has a relevant existing condition
- Select lab tests based on the specific ADRs and patient's medical conditions
- Use simple, patient-friendly language
- Keep symptom descriptions concise (3-5 symptoms per category)
- Organize symptoms from most to least critical
- DO NOT include any preamble, explanations, or additional text - ONLY the monitoring protocol in the exact format shown

Generate the monitoring protocol now:"""

        # Call Gemini API
        response = self._call_gemini_api(prompt)
        
        # Clean up response (remove any markdown code blocks if present)
        response = response.strip()
        if response.startswith("```"):
            # Remove markdown code block markers
            lines = response.split('\n')
            response = '\n'.join([line for line in lines if not line.strip().startswith("```")])
            response = response.strip()
        
        return response


def integrate_with_ibr_generator(IBRReportGenerator):
    """
    Function to integrate Gemini monitoring protocol into existing IBR generator
    
    Args:
        IBRReportGenerator: The existing IBR report generator class
        
    Returns:
        Modified class with Gemini integration
    """
    
    # Store original generate_monitoring_protocol method
    original_generate_monitoring_protocol = IBRReportGenerator.generate_monitoring_protocol
    
    @classmethod
    def generate_monitoring_protocol_with_gemini(cls, analysis_results: Dict, patient_info: Dict, 
                                                 conditional_meds: List = None,
                                                 use_gemini: bool = True,
                                                 gemini_api_key: str = None) -> str:
        """
        Generate monitoring protocol with optional Gemini AI enhancement
        
        Args:
            analysis_results: Complete analysis results
            patient_info: Patient demographic and medical information
            conditional_meds: List of conditional medications (optional)
            use_gemini: Whether to use Gemini API (default: True)
            gemini_api_key: Google API key for Gemini
            
        Returns:
            Formatted monitoring protocol string
        """
        if use_gemini:
            try:
                # Use Gemini API
                gemini_generator = GeminiMonitoringProtocolGenerator(api_key=gemini_api_key)
                return gemini_generator.generate_monitoring_protocol(analysis_results, patient_info)
            except Exception as e:
                print(f"Warning: Gemini API failed ({str(e)}), falling back to default method")
                # Fall back to original method if Gemini fails
                return original_generate_monitoring_protocol(analysis_results, patient_info, conditional_meds)
        else:
            # Use original method
            return original_generate_monitoring_protocol(analysis_results, patient_info, conditional_meds)
    
    # Replace method
    IBRReportGenerator.generate_monitoring_protocol = generate_monitoring_protocol_with_gemini
    
    return IBRReportGenerator


# Standalone function for easy integration
def generate_gemini_monitoring_protocol(analysis_results: Dict, patient_info: Dict, 
                                       gemini_api_key: str = None) -> str:
    """
    Standalone function to generate monitoring protocol using Gemini
    
    Args:
        analysis_results: Complete analysis results with LT ADRs
        patient_info: Patient demographic and medical information
        gemini_api_key: Google API key for Gemini
        
    Returns:
        Formatted monitoring protocol string
    """
    print("inside the generate_gemini_monitornig_protocol")
    generator = GeminiMonitoringProtocolGenerator(api_key=gemini_api_key)
    return generator.generate_monitoring_protocol(analysis_results, patient_info)


if __name__ == "__main__":
    # Example usage
    print("Gemini Monitoring Protocol Generator")
    print("=" * 80)
    print("\nThis module integrates Gemini API for dynamic monitoring protocol generation.")
    print("\nUsage:")
    print("1. Set GOOGLE_API_KEY environment variable")
    print("2. Import and use generate_gemini_monitoring_protocol() function")
    print("3. Or integrate with existing IBRReportGenerator class")
    print("\nExample:")
    print("""
    from gemini_monitoring_protocol import generate_gemini_monitoring_protocol
    
    protocol = generate_gemini_monitoring_protocol(
        analysis_results=analysis_results,
        patient_info=patient_info,
        gemini_api_key="your-api-key"
    )
    """)