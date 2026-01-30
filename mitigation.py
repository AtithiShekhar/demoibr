import json
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from typing import Dict, List, Any, Optional
from google import genai

# Load environment variables
load_dotenv()

class Factor_3_4_Risk_Mitigation_Feasibility:
    """
    Factor 3.4: Risk Mitigation Feasibility
    Classifies ADRs based on:
    - Risk Reversibility/Tolerability (Irreversible, Reversible, Tolerable)
    - Risk Preventability (Non-Tolerable, Non-preventable, Preventable)
    """
    
    def __init__(self):
        """Initialize with Gemini API and FDA sections"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables!")
        
        # Configure Gemini client
        self.client = genai.Client(api_key=self.gemini_api_key)
        
        # Keywords for classification
        self.irreversible_keywords = [
            'irreversible', 'permanent', 'may not be reversible', 
            'persistent after discontinuation', 'long-term impairment',
            'cumulative and irreversible', 'progressive', 'did not resolve',
            'chronic', 'fibrosis', 'degeneration', 'organ failure',
            'structural damage', 'malformation', 'teratogenic', 'carcinogenic',
            'cardiomyopathy', 'neuropathy', 'ototoxicity'
        ]
        
        self.reversible_keywords = [
            'reversible', 'resolved after discontinuation', 
            'improved after stopping treatment', 'transient', 'self-limited',
            'dose-related', 'resolved in most patients', 'decreased after dose reduction',
            'normalized', 'temporary', 'returned to baseline',
            'reversible upon interruption', 'mild to moderate and reversible',
            'resolved during follow-up'
        ]
        
        self.preventable_keywords = [
            'monitor', 'avoid', 'baseline', 'periodic', 'lab test',
            'dose reduction', 'contraindicated', 'screening',
            'early detection', 'proactive', 'warning signs'
        ]
        
        self.non_preventable_keywords = [
            'idiosyncratic', 'unpredictable', 'sudden', 
            'no known risk factors', 'difficult to predict',
            'no specific lab test', 'rare reaction'
        ]
        
        # Strict rules for specific ADRs
        self.strict_irreversible = [
            'stevens-johnson syndrome', 'stevens johnson', 'sjs',
            'toxic epidermal necrolysis', 'ten',
            'hearing loss', 'ototoxicity',
            'pulmonary fibrosis', 'hepatic fibrosis',
            'cardiomyopathy', 'optic neuropathy', 'peripheral neuropathy',
            'teratogenicity', 'congenital malformations',
            'aplastic anemia', 'agranulocytosis',
            'acute liver failure', 'hepatic failure'
        ]
        
        self.strict_non_preventable = [
            'stevens-johnson syndrome', 'stevens johnson', 'sjs',
            'toxic epidermal necrolysis', 'ten',
            'anaphylaxis', 'anaphylactic',
            'idiosyncratic reaction'
        ]
        
        print(f"✓ Factor 3.4 Analyzer initialized")
    
    # ============================================================================
    # PART 1: LOAD FACTOR 3.2 OUTPUT
    # ============================================================================
    
    def load_factor_3_2_output(self, factor_3_2_file: str) -> Dict[str, Any]:
        """Load Factor 3.2 output JSON"""
        try:
            with open(factor_3_2_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Error: {factor_3_2_file} not found!")
            return {}
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON in {factor_3_2_file}")
            return {}
    
    def extract_all_adrs(self, factor_3_2_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all ADRs from Factor 3.2 output"""
        all_adrs = []
        
        # Extract LT ADRs
        lt_adrs = factor_3_2_data.get('factor_3_2', {}).get('LT_ADRs', {})
        for medicine, data in lt_adrs.items():
            for adr in data.get('with_risk_factors', []) + data.get('without_risk_factors', []):
                all_adrs.append({
                    'medicine': medicine,
                    'adr_name': adr['adr_name'],
                    'adr_type': 'LT/Fatal ADR',
                    'section': adr['section'],
                    'fda_context': adr.get('fda_context', '')
                })
        
        # Extract Serious ADRs
        serious_adrs = factor_3_2_data.get('factor_3_2', {}).get('Serious_ADRs', {})
        for medicine, data in serious_adrs.items():
            for adr in data.get('with_risk_factors', []) + data.get('without_risk_factors', []):
                all_adrs.append({
                    'medicine': medicine,
                    'adr_name': adr['adr_name'],
                    'adr_type': 'Serious ADR',
                    'section': adr['section'],
                    'fda_context': adr.get('fda_context', '')
                })
        
        return all_adrs
    
    # ============================================================================
    # PART 2: CLASSIFY RISK REVERSIBILITY/TOLERABILITY
    # ============================================================================
    
    def classify_reversibility_tolerability(
        self,
        adr: Dict[str, Any],
        fda_sections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify ADR as: Irreversible, Reversible, or Tolerable
        """
        
        adr_name = adr['adr_name']
        medicine = adr['medicine']
        adr_lower = adr_name.lower()
        
        # STRICT RULES: Check if ADR is in strict irreversible list
        for strict_adr in self.strict_irreversible:
            if strict_adr in adr_lower:
                return {
                    'classification': 'Irreversible ADR',
                    'reasoning': f'{adr_name} is a known irreversible condition with permanent consequences',
                    'fda_evidence': 'Documented as irreversible in medical literature',
                    'keywords_found': [strict_adr]
                }
        
        # Search FDA sections for keywords
        fda_text = ""
        if fda_sections:
            fda_text = f"{fda_sections.get('warnings_and_cautions', '')} {fda_sections.get('adverse_reactions', '')} {fda_sections.get('boxed_warning', '')}"
        
        fda_text_lower = fda_text.lower()
        
        # Count keyword matches
        irreversible_matches = [kw for kw in self.irreversible_keywords if kw in fda_text_lower]
        reversible_matches = [kw for kw in self.reversible_keywords if kw in fda_text_lower]
        
        # Use AI for classification
        prompt = f"""You are a medical expert analyzing adverse drug reactions (ADRs) for reversibility.

MEDICINE: {medicine}
ADR: {adr_name}

FDA USPI CONTEXT:
{fda_text[:3000] if fda_text else 'Limited FDA information available'}

TASK: Classify this ADR into ONE of these categories:

1. **Irreversible ADR**: 
   - The ADR is permanent, cannot be fully reversed even after drug discontinuation
   - Examples: Ototoxicity, Stevens-Johnson Syndrome, Pulmonary fibrosis, Cardiomyopathy, Neuropathy (no recovery), Teratogenicity

2. **Reversible ADR**: 
   - The ADR can be reversed or resolved with drug discontinuation, dose reduction, or treatment
   - Examples: QT prolongation (resolves after stopping drug), Elevated transaminases (normalize), Hypertension (controlled), Nausea (resolves)

3. **Tolerable ADR**: 
   - The ADR is tolerable in the context of disease severity requiring treatment
   - The benefit of treating the serious disease outweighs the ADR risk
   - Examples: Mild nausea with chemotherapy, Mild headache with antihypertensives

CLASSIFICATION CRITERIA:
- If ADR causes permanent damage → Irreversible
- If ADR resolves/improves after stopping drug → Reversible  
- If ADR is minor and disease is severe → Tolerable

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "classification": "Irreversible ADR" OR "Reversible ADR" OR "Tolerable ADR",
  "reasoning": "Brief explanation why",
  "fda_evidence": "Quote from FDA text or 'Based on medical knowledge'",
  "keywords_found": ["keyword1", "keyword2"]
}}

Return ONLY valid JSON, no additional text.

Your JSON response:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            print(f"  Error classifying reversibility for {adr_name}: {str(e)}")
            
            # Fallback: Use keyword matching
            if irreversible_matches:
                return {
                    'classification': 'Irreversible ADR',
                    'reasoning': 'Based on irreversibility keywords in FDA text',
                    'fda_evidence': f"Keywords found: {', '.join(irreversible_matches[:3])}",
                    'keywords_found': irreversible_matches[:3]
                }
            elif reversible_matches:
                return {
                    'classification': 'Reversible ADR',
                    'reasoning': 'Based on reversibility keywords in FDA text',
                    'fda_evidence': f"Keywords found: {', '.join(reversible_matches[:3])}",
                    'keywords_found': reversible_matches[:3]
                }
            else:
                return {
                    'classification': 'Reversible ADR',
                    'reasoning': 'Default classification - insufficient information',
                    'fda_evidence': 'Limited FDA information available',
                    'keywords_found': []
                }
    
    # ============================================================================
    # PART 3: CLASSIFY RISK PREVENTABILITY
    # ============================================================================
    
    def classify_preventability(
        self,
        adr: Dict[str, Any],
        fda_sections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify ADR as: Non-Tolerable, Non-preventable, or Preventable
        """
        
        adr_name = adr['adr_name']
        medicine = adr['medicine']
        adr_lower = adr_name.lower()
        
        # STRICT RULES: Check if ADR is in strict non-preventable list
        for strict_adr in self.strict_non_preventable:
            if strict_adr in adr_lower:
                return {
                    'classification': 'Non-preventable ADR',
                    'reasoning': f'{adr_name} is an idiosyncratic/unpredictable reaction that cannot be prevented by routine monitoring',
                    'fda_evidence': 'Documented as unpredictable reaction',
                    'prevention_measures': []
                }
        
        # Search FDA sections for prevention keywords
        fda_text = ""
        if fda_sections:
            fda_text = f"{fda_sections.get('warnings_and_cautions', '')} {fda_sections.get('adverse_reactions', '')} {fda_sections.get('dosage_and_administration', '')}"
        
        fda_text_lower = fda_text.lower()
        
        # Count keyword matches
        preventable_matches = [kw for kw in self.preventable_keywords if kw in fda_text_lower]
        
        # Use AI for classification
        prompt = f"""You are a medical expert analyzing adverse drug reactions (ADRs) for preventability.

MEDICINE: {medicine}
ADR: {adr_name}

FDA USPI CONTEXT:
{fda_text[:3000] if fda_text else 'Limited FDA information available'}

TASK: Classify this ADR into ONE of these categories:

1. **Non-Tolerable ADR**: 
   - The ADR is NOT tolerable in the context of disease severity requiring treatment
   - The risk outweighs the benefit even for serious disease
   - Examples: Fatal anaphylaxis for mild condition

2. **Non-preventable ADR**: 
   - Difficult to prevent - no specific lab test or symptoms to monitor
   - Idiosyncratic, unpredictable reactions
   - Examples: Stevens-Johnson Syndrome, Anaphylaxis, Sudden reactions

3. **Preventable ADR**: 
   - Can be prevented with proactive actions:
     * Lab monitoring (baseline and periodic tests)
     * Dose reduction in high-risk populations
     * Avoiding interacting agents
     * Early symptom detection and reporting
   - Examples: Lactic acidosis (monitor renal function), Hepatotoxicity (monitor LFTs)

CLASSIFICATION CRITERIA:
- If ADR is unpredictable/idiosyncratic → Non-preventable
- If monitoring/dose adjustment can prevent → Preventable
- If ADR risk too high for disease benefit → Non-Tolerable

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "classification": "Non-Tolerable ADR" OR "Non-preventable ADR" OR "Preventable ADR",
  "reasoning": "Brief explanation why",
  "fda_evidence": "Quote from FDA text or 'Based on medical knowledge'",
  "prevention_measures": ["measure 1", "measure 2"]
}}

Return ONLY valid JSON, no additional text.

Your JSON response:"""

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            print(f"  Error classifying preventability for {adr_name}: {str(e)}")
            
            # Fallback: Use keyword matching
            if preventable_matches:
                return {
                    'classification': 'Preventable ADR',
                    'reasoning': 'Prevention measures mentioned in FDA text',
                    'fda_evidence': f"Prevention keywords found: {', '.join(preventable_matches[:3])}",
                    'prevention_measures': preventable_matches[:3]
                }
            else:
                return {
                    'classification': 'Non-preventable ADR',
                    'reasoning': 'No specific prevention measures mentioned',
                    'fda_evidence': 'Limited preventability information',
                    'prevention_measures': []
                }
    
    # ============================================================================
    # PART 4: EXTRACT FDA SECTIONS (Reuse from Factor 3.2)
    # ============================================================================
    
    def extract_fda_sections(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extract FDA USPI sections (same as Factor 3.2)"""
        try:
            import requests
            
            fda_api_key = os.getenv("FDA_API_KEY", "")
            fda_base_url = "https://api.fda.gov/drug/label.json"
            
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
                if fda_api_key:
                    params['api_key'] = fda_api_key
                
                try:
                    response = requests.get(fda_base_url, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'results' in data and len(data['results']) > 0:
                        all_results.extend(data['results'])
                        break
                except:
                    continue
            
            if not all_results:
                return None
            
            label_data = all_results[0]
            
            sections = {
                'drug_name': medicine_name,
                'boxed_warning': self._extract_text(label_data, 'boxed_warning'),
                'warnings_and_cautions': self._extract_text(label_data, 'warnings_and_cautions'),
                'warnings': self._extract_text(label_data, 'warnings'),
                'adverse_reactions': self._extract_text(label_data, 'adverse_reactions'),
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
    # PART 5: MAIN ANALYSIS
    # ============================================================================
    
    def analyze(self, factor_3_2_file: str) -> Dict[str, Any]:
        """Main analysis workflow"""
        
        print("\n" + "=" * 80)
        print("FACTOR 3.4: RISK MITIGATION FEASIBILITY ANALYSIS")
        print("=" * 80 + "\n")
        
        # Load Factor 3.2 output
        factor_3_2_data = self.load_factor_3_2_output(factor_3_2_file)
        
        if not factor_3_2_data:
            return {}
        
        # Extract all ADRs
        all_adrs = self.extract_all_adrs(factor_3_2_data)
        
        if not all_adrs:
            print("⚠️  No ADRs found in Factor 3.2 output")
            return {}
        
        print(f"Found {len(all_adrs)} ADRs to analyze\n")
        
        # Extract FDA sections for unique medicines
        medicines = list(set([adr['medicine'] for adr in all_adrs]))
        fda_data = {}
        
        print("Extracting FDA sections...")
        for i, medicine in enumerate(medicines, 1):
            print(f"[{i}/{len(medicines)}] {medicine}...")
            fda_data[medicine] = self.extract_fda_sections(medicine)
            time.sleep(0.3)
        
        print("\nAnalyzing ADRs...\n")
        
        # Analyze each ADR
        reversibility_results = {}
        preventability_results = {}
        
        for i, adr in enumerate(all_adrs, 1):
            medicine = adr['medicine']
            adr_name = adr['adr_name']
            
            print(f"[{i}/{len(all_adrs)}] {medicine} - {adr_name}")
            
            fda_sections = fda_data.get(medicine)
            
            # Classify reversibility/tolerability
            reversibility = self.classify_reversibility_tolerability(adr, fda_sections)
            print(f"  → Reversibility: {reversibility['classification']}")
            
            # Classify preventability
            preventability = self.classify_preventability(adr, fda_sections)
            print(f"  → Preventability: {preventability['classification']}")
            
            # Store results
            key = f"{medicine} - {adr_name}"
            reversibility_results[key] = {
                'medicine': medicine,
                'adr_name': adr_name,
                'adr_type': adr['adr_type'],
                **reversibility
            }
            
            preventability_results[key] = {
                'medicine': medicine,
                'adr_name': adr_name,
                'adr_type': adr['adr_type'],
                **preventability
            }
            
            print()
            time.sleep(1)  # Rate limiting
        
        # Generate output
        output = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': factor_3_2_data.get('patient', {}),
            'medications': factor_3_2_data.get('medications', []),
            'total_adrs_analyzed': len(all_adrs),
            'factor_3_4_risk_mitigation_feasibility': {
                'risk_reversibility_risk_tolerability': reversibility_results,
                'risk_preventability': preventability_results
            }
        }
        
        return output
    
    def print_report(self, results: Dict[str, Any]):
        """Print formatted report"""
        
        print("\n" + "=" * 80)
        print("FACTOR 3.4: RISK MITIGATION FEASIBILITY REPORT")
        print("=" * 80)
        
        patient = results.get('patient', {})
        print(f"\nPatient: {patient.get('age')}y {patient.get('gender')}")
        print(f"Medications: {', '.join(results.get('medications', []))}")
        print(f"Total ADRs Analyzed: {results.get('total_adrs_analyzed', 0)}")
        
        factor_3_4 = results.get('factor_3_4_risk_mitigation_feasibility', {})
        
        # Table A: Risk Reversibility/Risk Tolerability
        print("\n" + "=" * 80)
        print("TABLE A: RISK REVERSIBILITY / RISK TOLERABILITY")
        print("=" * 80)
        
        reversibility_data = factor_3_4.get('risk_reversibility_risk_tolerability', {})
        
        for key, data in reversibility_data.items():
            print(f"\n{data['medicine']} - {data['adr_name']}")
            print(f"  Classification: {data['classification']}")
            print(f"  Reasoning: {data['reasoning']}")
            if data.get('fda_evidence'):
                print(f"  FDA Evidence: {data['fda_evidence'][:200]}...")
        
        # Table B: Risk Preventability
        print("\n" + "=" * 80)
        print("TABLE B: RISK PREVENTABILITY")
        print("=" * 80)
        
        preventability_data = factor_3_4.get('risk_preventability', {})
        
        for key, data in preventability_data.items():
            print(f"\n{data['medicine']} - {data['adr_name']}")
            print(f"  Classification: {data['classification']}")
            print(f"  Reasoning: {data['reasoning']}")
            if data.get('prevention_measures'):
                print(f"  Prevention Measures: {', '.join(data['prevention_measures'][:3])}")
        
        print("\n" + "=" * 80 + "\n")


def main():
    """Main execution"""
    
    print("\n" + "=" * 80)
    print("FACTOR 3.4: RISK MITIGATION FEASIBILITY ANALYZER")
    print("Powered by Gemini 2.0 Flash")
    print("=" * 80)
    
    # Initialize analyzer
    try:
        analyzer = Factor_3_4_Risk_Mitigation_Feasibility()
    except ValueError as e:
        print(f"\n❌ {str(e)}")
        print("Please add GEMINI_API_KEY to your .env file")
        return
    
    # Find Factor 3.2 output file
    import glob
    factor_3_2_files = glob.glob('factor_3_2_3_3_report*.json')
    
    if not factor_3_2_files:
        print("\n❌ No Factor 3.2 output file found!")
        print("Please run Factor 3.2 & 3.3 analysis first.")
        return
    
    # Use most recent file
    factor_3_2_file = max(factor_3_2_files, key=os.path.getmtime)
    print(f"\nUsing Factor 3.2 input: {factor_3_2_file}\n")
    
    # Analyze
    results = analyzer.analyze(factor_3_2_file)
    
    if not results:
        return
    
    # Print report
    analyzer.print_report(results)
    
    # Save to JSON
    output_file = f"factor_3_4_risk_mitigation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Results saved to: {output_file}\n")


if __name__ == "__main__":
    main()