import json
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import Dict, List, Any, Optional
import google.generativeai as genai


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
        genai.configure(api_key=self.gemini_api_key)
        self.model_name = "gemini-2.0-flash-exp"
        self.model = genai.GenerativeModel(self.model_name)



        print(f"✓ Gemini model initialized ({self.model_name})")


    
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
    # PART 2: ANALYZE CONSEQUENCES WITH GEMINI
    # ============================================================================
    
    def analyze_consequences(
        self,
        disease: str
    ) -> Dict[str, Any]:
        """
        Use Gemini to analyze consequences of non-treatment
        """
        
        prompt = f"""You are a medical expert analyzing the consequences of untreated medical conditions. Use your knowledge of medical literature and current clinical guidelines to provide accurate information.

DISEASE/CONDITION: {disease}

TASK: Determine what happens if this disease/condition is NOT treated or medication is NOT administered. Base your analysis on information from reliable medical sources such as:
- CDC (Centers for Disease Control and Prevention)
- WHO (World Health Organization)
- StatPearls/NCBI/NIH (National Library of Medicine)
- FDA (Food and Drug Administration)
- Mayo Clinic
- Johns Hopkins Medicine
- UpToDate
- Medical textbooks and peer-reviewed journals

CLASSIFICATION CRITERIA:

1. **Acute, life-threatening condition**
   - Timeframe: Immediate/short-term (minutes to days)
   - Consequences: Death or irreversible organ damage
   - Example: Untreated ventricular fibrillation → cardiac arrest and death within minutes

2. **Acute, non-life-threatening**
   - Timeframe: Short-term (days to weeks)
   - Consequences: Acute worsening or complications BUT no immediate mortality risk
   - Example: Untreated UTI → severe pain, kidney infection, but not immediately fatal

3. **Chronic, life-threatening**
   - Timeframe: Long-term/progressive (months to years)
   - Consequences: Progressive disease worsening AND increased mortality risk over time
   - Example: Untreated hypertension → stroke, heart attack, kidney failure over years

4. **Chronic, non-life-threatening**
   - Timeframe: Long-term (months to years)
   - Consequences: Illness, disability, reduced quality of life BUT no significant mortality risk
   - Example: Untreated mild osteoarthritis → chronic pain, reduced mobility

IMPORTANT:
- If a disease has BOTH acute and chronic consequences, list BOTH classifications
- For example, untreated diabetes:
  * Acute, life-threatening: Diabetic ketoacidosis (DKA) can occur within days → coma/death
  * Chronic, life-threatening: Long-term complications (retinopathy, nephropathy, neuropathy, CVD) → increased mortality

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "disease": "{disease}",
  "classifications": [
    {{
      "category": "Acute, life-threatening condition" OR "Acute, non-life-threatening" OR "Chronic, life-threatening" OR "Chronic, non-life-threatening",
      "timeframe": "Immediate/short-term" OR "Long-term/progressive",
      "consequences_if_untreated": "Detailed description of what happens",
      "severity": "Death or irreversible organ damage" OR "Acute worsening/complications but no immediate mortality" OR "Increased mortality risk over time" OR "Reduced quality of life but no significant mortality risk",
      "specific_outcomes": ["outcome 1", "outcome 2", "outcome 3"],
      "reliable_sources_used": ["source domain 1", "source domain 2"]
    }}
  ]
}}

CRITICAL RULES:
1. Use your comprehensive medical knowledge to provide accurate, evidence-based information
2. Base your analysis on information consistent with CDC, WHO, NCBI/NIH, FDA, and major academic medical centers
3. If disease has both acute AND chronic consequences, include BOTH in the classifications array
4. Be medically accurate and evidence-based
5. Return ONLY valid JSON, no additional text

Your JSON response:"""

        try:
            # Generate content using new API
            response = self.model.generate_content(prompt)

            
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
        
        print("\nAnalyzing consequences...\n")
        
        factor_2_6_results = {}
        
        for i, disease in enumerate(diagnoses, 1):
            print(f"[{i}/{len(diagnoses)}] Analyzing: {disease}")
            
            # Analyze with Gemini
            result = self.analyze_consequences(disease)
            
            # Store result
            factor_2_6_results[disease] = result
            
            # Print summary
            if result.get('classifications'):
                for classification in result['classifications']:
                    print(f"  → Category: {classification.get('category')}")
                    print(f"     Timeframe: {classification.get('timeframe')}")
                    print(f"     Severity: {classification.get('severity')}")
            
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
                
                print(f"\n  Category: {category}")
                print(f"  Timeframe: {timeframe}")
                print(f"  Severity: {severity}")
                print(f"\n  Consequences if Untreated:")
                print(f"    {consequences}")
                
                if outcomes:
                    print(f"\n  Specific Outcomes:")
                    for outcome in outcomes:
                        print(f"    • {outcome}")
                
                if sources:
                    print(f"\n  Sources:")
                    for source in sources:
                        print(f"    • {source}")
        
        print("\n" + "=" * 80 + "\n")


def main():
    """Main execution"""
    
    print("\n" + "=" * 80)
    print("FACTOR 2.6: CONSEQUENCES OF NON-TREATMENT ANALYZER")
    print(f"Powered by {analyzer.model_name}")
    print("=" * 80)
    
    # Initialize analyzer
    try:
        analyzer = Factor_2_6_Consequences_Analyzer()
    except ValueError as e:
        print(f"\n❌ {str(e)}")
        print("Please add GEMINI_API_KEY to your .env file")
        return
    
    # Load patient input
    patient_input_file = 'patient_input.json'
    
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
    
    # Print report
    analyzer.print_report(results)
    
    # Save to JSON
    output_file = f"factor_2_6_consequences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Results saved to: {output_file}\n")


if __name__ == "__main__":
    main()