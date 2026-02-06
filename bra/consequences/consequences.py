import json
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

class Factor_2_6_Consequences_Analyzer:
    """
    Factor 2.6: Consequences of Non-Treatment
    Uses Gemini Flash 2.0 to determine medical need severity
    """
    
    def __init__(self):
        """Initialize with Gemini API"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")
        
        # Configure new Gemini client
            self.client = genai.Client(api_key=self.gemini_api_key)
        
        print(f"✓ Gemini client initialized")
    
    # ============================================================================
    # PART 1: PARSE DIAGNOSES FROM PATIENT DATA
    # ============================================================================
    
    def extract_diagnoses(self, patient_data: Dict[str, Any]) -> List[str]:
        """
        Extract individual diagnoses from patient data
        Handles comma-separated diagnoses
        """
        
        patient = patient_data.get('patient', {})
        
        # Get diagnosis from both 'diagnosis' and 'condition' fields
        diagnosis_text = patient.get('diagnosis', '')
        condition_text = patient.get('condition', '')
        
        # Combine both
        full_diagnosis = f"{diagnosis_text}, {condition_text}".strip(', ')
        
        if not full_diagnosis:
            return []
        
        # Split by commas
        diagnoses = [d.strip() for d in full_diagnosis.split(',') if d.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_diagnoses = []
        for d in diagnoses:
            d_lower = d.lower()
            if d_lower not in seen:
                seen.add(d_lower)
                unique_diagnoses.append(d)
        
        return unique_diagnoses
    
    # ============================================================================
    # PART 2: ANALYZE CONSEQUENCES WITH GEMINI (PATIENT-CONTEXT-AWARE)
    # ============================================================================
    
    def analyze_consequences(
        self,
        disease: str,
        patient_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use Gemini to analyze consequences of non-treatment with patient context
        """
        
        # Build patient context if provided
        patient_context = ""
        if patient_data:
            patient = patient_data.get('patient', {})
            age = patient.get('age', 'unknown')
            gender = patient.get('gender', 'unknown')
            diagnosis = patient.get('diagnosis', '')
            social_risk = patient.get('social_risk_factors', '')
            
            # Extract medical history
            medical_history = patient_data.get('MedicalHistory', [])
            active_conditions = []
            severe_conditions = []
            
            for history in medical_history:
                condition_name = history.get('diagnosisName', '')
                status = history.get('status', '')
                severity = history.get('severity', '')
                
                if status == 'Active':
                    active_conditions.append(condition_name)
                    if severity in ['Severe', 'Critical']:
                        severe_conditions.append(f"{condition_name} ({severity})")
            
            # Determine patient characteristics
            is_post_transplant = 'transplant' in diagnosis.lower()
            is_immunosuppressed = is_post_transplant or 'immunosuppressed' in diagnosis.lower()
            age_category = "pediatric" if age != "unknown" and age < 18 else ("geriatric" if age != "unknown" and age >= 65 else "adult")
            
            patient_context = f"""
PATIENT CONTEXT (consider for severity assessment):
- Age: {age} years ({age_category})
- Gender: {gender}
- Primary Diagnosis: {diagnosis}
- Social Risk Factors: {social_risk}
- Post-Transplant: {'Yes' if is_post_transplant else 'No'}
- Immunosuppressed: {'Yes' if is_immunosuppressed else 'No'}"""

            if active_conditions:
                patient_context += f"\n- Active Comorbidities: {', '.join(active_conditions)}"
            
            if severe_conditions:
                patient_context += f"\n- Severe/Critical Conditions: {', '.join(severe_conditions)}"

            patient_context += f"""

Consider how this patient's specific characteristics (age, immunosuppression, comorbidities) 
affect the severity and timeframe of consequences if {disease} is left untreated.
"""
        
        prompt = f"""You are a medical expert. Classify untreated {disease} consequences.
{patient_context}
CLASSIFICATION RULES (STRICT):

1. **Acute, life-threatening**: Death/irreversible damage within hours-days WITHOUT treatment
   - Examples: Ventricular fibrillation, Anaphylaxis, Status epilepticus, Acute MI
   - NOT diabetes, hypertension, COPD (these are chronic)

2. **Acute, non-life-threatening**: Worsens in days-weeks but NOT immediately fatal
   - Examples: UTI, Mild pneumonia, Gastroenteritis

3. **Chronic, life-threatening**: Progressive mortality risk over months-years
   - Examples: Diabetes (DKA possible but not immediate), Hypertension, CKD, COPD
   - Most chronic diseases belong here

4. **Chronic, non-life-threatening**: Long-term discomfort, NO significant mortality
   - Examples: Osteoarthritis, Mild hypothyroidism, GERD

CRITICAL GUIDELINES:
- Type 2 Diabetes = Chronic, life-threatening (NOT acute unless actively in DKA)
- Hypertension = Chronic, life-threatening (NOT acute unless hypertensive crisis)
- CKD/Renal impairment = Chronic, life-threatening
- If disease takes months-years to cause death → Chronic, life-threatening
- If disease causes death in hours-days without treatment → Acute, life-threatening
{"- Consider patient's age, immunosuppression status, and comorbidities when assessing severity" if patient_data else ""}

DISEASE: {disease}

Provide SHORT, CONCISE consequences (max 3-4 bullet points, 10-15 words each).
NO paragraphs. ONLY key outcomes.

JSON FORMAT:
{{
  "disease": "{disease}",
  "classifications": [
    {{
      "category": "Choose ONLY ONE from above 4 categories",
      "timeframe": "Immediate/short-term" OR "Long-term/progressive",
      "consequences_if_untreated": "• Outcome 1\\n• Outcome 2\\n• Outcome 3",
      "severity": "Match category",
      "specific_outcomes": ["outcome1", "outcome2", "outcome3"],
      "reliable_sources_used": ["CDC", "WHO"]{"," if patient_data else ""}
      {"\"patient_specific_notes\": \"How patient's age/immunosuppression affects severity\"" if patient_data else ""}
    }}
  ]
}}

Rules:
- Keep consequences_if_untreated to 3-4 bullet points MAX
- Each bullet point: 10-15 words
- Be concise, direct, factual
{"- Include patient_specific_notes if patient context is provided" if patient_data else ""}
- Return ONLY JSON

JSON:"""

        try:
            # Generate content using new API
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            response_text = response.text.strip()
            
            # Clean up response - remove markdown code blocks if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON for {disease}: {str(e)}")
                print(f"Response text: {response_text[:500]}")
                
                # Fallback: Create basic structure
                return {
                    "disease": disease,
                    "classifications": [
                        {
                            "category": "Unable to determine",
                            "timeframe": "Unknown",
                            "consequences_if_untreated": f"Unable to analyze consequences for {disease}",
                            "severity": "Unknown",
                            "specific_outcomes": [],
                            "reliable_sources_used": []
                        }
                    ]
                }
            
        except Exception as e:
            print(f"Error analyzing {disease}: {str(e)}")
            return {
                "disease": disease,
                "classifications": [
                    {
                        "category": "Error",
                        "timeframe": "Unknown",
                        "consequences_if_untreated": f"Error analyzing: {str(e)}",
                        "severity": "Unknown",
                        "specific_outcomes": [],
                        "reliable_sources_used": []
                    }
                ]
            }
    
    # ============================================================================
    # PART 3: GENERATE FACTOR 2.6 OUTPUT
    # ============================================================================
    
    def analyze_patient(
        self,
        patient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main function: Analyze all diagnoses for a patient
        """
        
        print("\n" + "=" * 80)
        print("FACTOR 2.6: CONSEQUENCES OF NON-TREATMENT ANALYSIS")
        print("=" * 80 + "\n")
        
        # Extract diagnoses
        diagnoses = self.extract_diagnoses(patient_data)
        
        if not diagnoses:
            print("⚠️  No diagnoses found in patient data")
            return {
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'patient': patient_data.get('patient', {}),
                'factor_2_6': {},
                'total_diagnoses_analyzed': 0
            }
        
        print(f"Found {len(diagnoses)} diagnosis/diagnoses to analyze:")
        for i, d in enumerate(diagnoses, 1):
            print(f"  {i}. {d}")
        
        print("\nAnalyzing consequences with patient context...\n")
        
        factor_2_6_results = {}
        
        for i, disease in enumerate(diagnoses, 1):
            print(f"[{i}/{len(diagnoses)}] Analyzing: {disease}")
            
            # Analyze with Gemini (passing patient_data for context-aware analysis)
            result = self.analyze_consequences(disease, patient_data)
            
            # Store result
            factor_2_6_results[disease] = result
            
            # Print summary
            if result.get('classifications'):
                for classification in result['classifications']:
                    print(f"  → Category: {classification.get('category')}")
                    print(f"     Timeframe: {classification.get('timeframe')}")
                    print(f"     Severity: {classification.get('severity')}")
                    if 'patient_specific_notes' in classification:
                        print(f"     Patient Note: {classification.get('patient_specific_notes')}")
            
            print()
            
            # Rate limiting (1 second between calls)
            if i < len(diagnoses):
                time.sleep(1)
        
        # Generate final output
        output = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': patient_data.get('patient', {}),
            'diagnoses_analyzed': diagnoses,
            'factor_2_6_consequences_of_non_treatment': factor_2_6_results,
            'total_diagnoses_analyzed': len(diagnoses)
        }
        
        return output
    
    def print_report(self, results: Dict[str, Any]):
        """Print formatted report"""
        
        print("\n" + "=" * 80)
        print("FACTOR 2.6: CONSEQUENCES OF NON-TREATMENT REPORT")
        print("=" * 80)
        
        patient = results.get('patient', {})
        print(f"\nPatient: {patient.get('age')}y {patient.get('gender')}")
        print(f"Total Diagnoses Analyzed: {results.get('total_diagnoses_analyzed', 0)}")
        
        factor_2_6 = results.get('factor_2_6_consequences_of_non_treatment', {})
        
        if not factor_2_6:
            print("\n✓ No diagnoses to analyze")
            print("=" * 80 + "\n")
            return
        
        print("\n" + "=" * 80)
        
        for disease, data in factor_2_6.items():
            print(f"\n📋 DISEASE: {disease.upper()}")
            print("-" * 80)
            
            classifications = data.get('classifications', [])
            
            for i, classification in enumerate(classifications, 1):
                if len(classifications) > 1:
                    print(f"\nClassification {i}:")
                
                category = classification.get('category', 'Unknown')
                timeframe = classification.get('timeframe', 'Unknown')
                consequences = classification.get('consequences_if_untreated', 'Unknown')
                severity = classification.get('severity', 'Unknown')
                outcomes = classification.get('specific_outcomes', [])
                sources = classification.get('reliable_sources_used', [])
                patient_notes = classification.get('patient_specific_notes', '')
                
                print(f"\n  Category: {category}")
                print(f"  Timeframe: {timeframe}")
                print(f"  Severity: {severity}")
                print(f"\n  Consequences if Untreated:")
                print(f"    {consequences}")
                
                if patient_notes:
                    print(f"\n  Patient-Specific Considerations:")
                    print(f"    {patient_notes}")
                
                if outcomes:
                    print(f"\n  Specific Outcomes:")
                    for outcome in outcomes:
                        print(f"    • {outcome}")
                
                if sources:
                    print(f"\n  Sources:")
                    for source in sources:
                        print(f"    • {source}")
        
        print("\n" + "=" * 80 + "\n")


# ============================================================================
# NEW: START FUNCTION FOR SYSTEM INTEGRATION
# ============================================================================

def start(scoring_system=None) -> Dict[str, Any]:
    """
    Main entry point for consequences analysis (called by the system)
    
    Args:
        scoring_system: Scoring system object that contains patient_data
    
    Returns:
        Dictionary with consequences analysis results and scoring data
    """
    
    try:
        # Initialize analyzer
        analyzer = Factor_2_6_Consequences_Analyzer()
    except ValueError as e:
        print(f"❌ {str(e)}")
        return {
            'error': str(e),
            'factor_2_6_consequences_of_non_treatment': {},
            'consequences_score': None
        }
    
    # Load patient input
    patient_input_file = '../adrs_input.json'
    
    try:
        with open(patient_input_file, 'r') as f:
            patient_data = json.load(f)
    except FileNotFoundError:
        print(f"\n❌ Error: {patient_input_file} not found!")
        print("Please create patient_input.json with patient diagnosis information.")
        return
    except json.JSONDecodeError:
        print(f"\n❌ Error: Invalid JSON in {patient_input_file}")
        return
    
    # Analyze patient
    results = analyzer.analyze_patient(patient_data)
    print(f"result of consequences {results} ")
    # -------------------------------
    # Consequences scoring (if scoring_system provided)
    # -------------------------------
    if scoring_system:
        try:
            from scoring.benefit_factor import get_consequences_data
            
            consequences_score = get_consequences_data(
                consequences_data=results.get('consequences.json', {}),
                scoring_system=scoring_system
            )
        except ImportError:
            print("⚠️  scoring.consequences_factor module not found - skipping scoring")
            consequences_score = None
        except Exception as e:
            print(f"⚠️  Error in consequences scoring: {str(e)}")
            consequences_score = None
    else:
        consequences_score = None
    
    # Add scoring to results
    results['consequences_score'] = consequences_score
    
    return results