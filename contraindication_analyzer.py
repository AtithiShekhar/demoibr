import json
import boto3
import google.generativeai as genai
from typing import Dict, List, Any
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ContraindicationAnalyzer:
    """
    Analyzes patient prescriptions against medicine knowledge base
    for contraindication detection using AWS Bedrock and Gemini AI
    """
    
    def __init__(self):
        """Initialize the analyzer with credentials from .env file"""
        self.kb_id = os.getenv("KB_ID")
        self.aws_region = os.getenv("AWS_REGION")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not all([self.kb_id, self.aws_region, gemini_api_key]):
            raise ValueError("Missing required environment variables. Check .env file.")
        
        # Initialize AWS Bedrock client
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if aws_access_key and aws_secret_key:
            self.bedrock_agent = boto3.client(
                'bedrock-agent-runtime',
                region_name=self.aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
        else:
            # Use default credentials (from aws configure or IAM role)
            self.bedrock_agent = boto3.client(
                'bedrock-agent-runtime',
                region_name=self.aws_region
            )
        
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
        
    def build_patient_context(self, patient_data: Dict[str, Any]) -> str:
        """Build comprehensive patient context from input JSON"""

        patient = patient_data.get('patient', {})
        prescription = patient_data.get('prescription', [])

        age = patient.get('age', 'unknown')
        gender = patient.get('gender', 'unknown')
        diagnosis = patient.get('diagnosis', 'unknown')
        condition = patient.get('condition', 'none reported')

        # Normalize condition text for clinical clarity
        condition_text = condition if condition else "none reported"

        prescription_text = (
            ", ".join(prescription) if prescription else "no medications listed"
        )

        context = f"""
        PATIENT PROFILE:
        - Age: {age}
        - Gender: {gender}

        CLINICAL DIAGNOSIS:
        - {diagnosis}

        RELEVANT MEDICAL CONDITION(S):
        - {condition_text}

        CURRENT PRESCRIPTION:
        - {prescription_text}

        INSTRUCTIONS:
        Evaluate contraindications STRICTLY based on FDA USPI labeling.
        Give priority to ABSOLUTE contraindications explicitly listed under the
        'CONTRAINDICATIONS' section of the USPI.
        """

        return context.strip()

    
    def query_bedrock_kb(self, medicine_name: str) -> str:
        """Query Amazon Bedrock Knowledge Base for medicine information"""
        try:
            query = f"What are the contraindications for {medicine_name}? Provide complete contraindication section from the USPI label."
            
            response = self.bedrock_agent.retrieve_and_generate(
                input={
                    'text': query
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.kb_id,
                        'modelArn': f'arn:aws:bedrock:{self.aws_region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
                    }
                }
            )
            
            return response['output']['text']
            
        except Exception as e:
            print(f"Error querying Bedrock for {medicine_name}: {str(e)}")
            return ""
    
    def analyze_contraindication(
        self, 
        patient_context: str, 
        medicine_name: str, 
        medicine_info: str
    ) -> Dict[str, Any]:
        """Use Gemini to analyze contraindications based on patient context"""
        prompt = f"""You are a clinical pharmacology expert analyzing contraindications.

PATIENT CONTEXT:
{patient_context}

MEDICINE INFORMATION FOR {medicine_name}:
{medicine_info}

ANALYSIS TASK:
Analyze if the patient has any contraindications for {medicine_name} based on:
1. Patient's age
2. Patient's gender
3. Patient's medical conditions/diagnosis
4. Patient's condition
5. Any other medications they're taking

CHECK SPECIFICALLY:
- Is there an ABSOLUTE contraindication mentioned in the CONTRAINDICATIONS section?
- Are there any warnings or precautions related to patient's specific conditions?

SCORING RULES:
- Absolute contraindication (completely restricted): Score = 500
- Warning/precaution (restricted use): Score = 10
- No contraindication: Score = 0

Return your analysis in the following JSON format:
{{
    "medicine_name": "{medicine_name}",
    "contraindication_found": true/false,
    "contraindication_type": "absolute" or "warning" or "none",
    "risk_score": 500 or 10 or 0,
    "risk_factor": "specific condition or factor identified",
    "output_text": "formatted output as per guidelines"
}}

IMPORTANT OUTPUT TEXT FORMATTING:
If absolute contraindication (score 500):
"Use of this {medicine_name} in patients having [specific risk factor], will cause more risks than benefits, which is not beneficial for the patient. Hence, use of this medicine is restricted as per scientific evidence and documentation in regulatory label."

If warning/precaution (score 10):
"Use of this {medicine_name} in patients with [specific condition] requires careful monitoring and may need dose adjustments. Caution is advised as per regulatory label."

If no contraindication (score 0):
"No specific contraindications identified for this patient with {medicine_name} based on available information."

Provide only valid JSON response, no additional text."""

        try:
            response = self.gemini_model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean up response if it has markdown code blocks
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            elif result_text.startswith('```'):
                result_text = result_text.replace('```', '').strip()
            
            result = json.loads(result_text)
            return result
            
        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini response for {medicine_name}: {str(e)}")
            return {
                "medicine_name": medicine_name,
                "contraindication_found": False,
                "contraindication_type": "error",
                "risk_score": 0,
                "risk_factor": "Analysis error",
                "output_text": f"Error analyzing {medicine_name}. Please review manually."
            }
        except Exception as e:
            print(f"Error in Gemini analysis for {medicine_name}: {str(e)}")
            return {
                "medicine_name": medicine_name,
                "contraindication_found": False,
                "contraindication_type": "error",
                "risk_score": 0,
                "risk_factor": "Analysis error",
                "output_text": f"Error analyzing {medicine_name}. Please review manually."
            }
    
    def generate_report(
        self, 
        patient_data: Dict[str, Any], 
        analysis_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate final contraindication report"""
        patient = patient_data.get('patient', {})
        
        report = {
            "assessment_date": datetime.now().strftime("%Y-%m-%d"),
            "patient_info": {
                "age": patient.get('age'),
                "gender": patient.get('gender'),
                "diagnosis": patient.get('diagnosis')
            },
            "prescribed_medicines": patient_data.get('prescription', []),
            "contraindication_analysis": analysis_results,
            "total_risk_score": sum(r['risk_score'] for r in analysis_results),
            "critical_contraindications": [
                r for r in analysis_results 
                if r['contraindication_type'] == 'absolute'
            ],
            "warnings": [
                r for r in analysis_results 
                if r['contraindication_type'] == 'warning'
            ],
            "summary": self._generate_summary(analysis_results)
        }
        
        return report
    
    def _generate_summary(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Generate executive summary of findings"""
        critical_count = sum(
            1 for r in analysis_results 
            if r['contraindication_type'] == 'absolute'
        )
        warning_count = sum(
            1 for r in analysis_results 
            if r['contraindication_type'] == 'warning'
        )
        safe_count = sum(
            1 for r in analysis_results 
            if r['contraindication_type'] == 'none'
        )
        
        summary = f"Contraindication Assessment Summary:\n"
        summary += f"- Critical Contraindications: {critical_count}\n"
        summary += f"- Warnings/Precautions: {warning_count}\n"
        summary += f"- Safe to Use: {safe_count}\n"
        
        if critical_count > 0:
            summary += "\n⚠️ IMMEDIATE ACTION REQUIRED: Critical contraindications detected. Review alternatives."
        elif warning_count > 0:
            summary += "\n⚠️ CAUTION: Warnings identified. Monitor patient closely."
        else:
            summary += "\n✓ No contraindications identified for prescribed medications."
        
        return summary
    
    def analyze_prescription(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to analyze entire prescription"""
        print("Starting contraindication analysis...")
        print(f"Patient: {patient_data['patient']['age']}y {patient_data['patient']['gender']}")
        print(f"Medicines to analyze: {len(patient_data['prescription'])}")
        print("-" * 80)
        
        patient_context = self.build_patient_context(patient_data)
        analysis_results = []
        
        for medicine in patient_data['prescription']:
            print(f"\nAnalyzing: {medicine}")
            
            print(f"  → Querying Bedrock Knowledge Base...")
            medicine_info = self.query_bedrock_kb(medicine)
            
            if not medicine_info:
                print(f"  ⚠️ No information found in knowledge base")
                analysis_results.append({
                    "medicine_name": medicine,
                    "contraindication_found": False,
                    "contraindication_type": "no_data",
                    "risk_score": 0,
                    "risk_factor": "No data available",
                    "output_text": f"No contraindication data available for {medicine} in knowledge base."
                })
                continue
            
            print(f"  → Analyzing with Gemini AI...")
            result = self.analyze_contraindication(
                patient_context, 
                medicine, 
                medicine_info
            )
            analysis_results.append(result)
            
            if result['contraindication_type'] == 'absolute':
                print(f"  ⚠️ CRITICAL: Absolute contraindication found!")
            elif result['contraindication_type'] == 'warning':
                print(f"  ⚠️ WARNING: Precaution required")
            else:
                print(f"  ✓ No contraindication")
        
        print("\n" + "=" * 80)
        print("Analysis complete. Generating report...")
        
        report = self.generate_report(patient_data, analysis_results)
        return report


def main():
    """Main execution function"""
    # Load patient input from JSON file
    try:
        with open('patient_input.json', 'r') as f:
            patient_input = json.load(f)
    except FileNotFoundError:
        print("Error: patient_input.json file not found!")
        print("Please create patient_input.json in the same directory.")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON in patient_input.json")
        return
    
    # Initialize analyzer
    try:
        analyzer = ContraindicationAnalyzer()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return
    
    # Run analysis
    report = analyzer.analyze_prescription(patient_input)
    
    # Print formatted report
    print("\n" + "=" * 80)
    print("CONTRAINDICATION ANALYSIS REPORT")
    print("=" * 80)
    print(json.dumps(report, indent=2))
    
    # Save to file
    output_filename = f"contraindication_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Report saved to: {output_filename}")
    
    # Print detailed output for each medicine
    print("\n" + "=" * 80)
    print("DETAILED FINDINGS")
    print("=" * 80)
    
    for result in report['contraindication_analysis']:
        print(f"\n{result['medicine_name']}:")
        print(f"  Type: {result['contraindication_type']}")
        print(f"  Risk Score: {result['risk_score']}")
        print(f"  Finding: {result['output_text']}")


if __name__ == "__main__":
    main()