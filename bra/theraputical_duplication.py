import json
import requests
from typing import Dict, List, Any, Optional, Tuple
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from itertools import combinations

# Load environment variables
load_dotenv()

class TherapeuticDuplicationChecker:
    """
    Therapeutic Duplication Analyzer - Simplified 3-Category Approach
    Category 1: Redundant/Duplicate Prescription (CRITICAL)
    Category 2: Unique role, no overlap (SAFE)
    Category 3: Some overlap but with rationale (CAUTION)
    """
    
    def __init__(self):
        """Initialize with FDA API key"""
        self.fda_api_key = os.getenv("FDA_API_KEY", "")
        self.fda_base_url = "https://api.fda.gov/drug/label.json"
        
        # Known drug class groupings (for strict duplication detection)
        self.drug_classes = {
            # Statins (HMG-CoA Reductase Inhibitors)
            'statins': ['atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin', 'lovastatin', 'fluvastatin', 'pitavastatin'],
            
            # NSAIDs
            'nsaids': ['ibuprofen', 'naproxen', 'diclofenac', 'celecoxib', 'indomethacin', 'ketorolac', 'meloxicam', 'piroxicam'],
            
            # Beta Blockers
            'beta_blockers': ['metoprolol', 'atenolol', 'propranolol', 'carvedilol', 'bisoprolol', 'labetalol', 'nebivolol'],
            
            # ACE Inhibitors
            'ace_inhibitors': ['lisinopril', 'enalapril', 'ramipril', 'benazepril', 'captopril', 'fosinopril', 'quinapril'],
            
            # ARBs (Angiotensin Receptor Blockers)
            'arbs': ['losartan', 'valsartan', 'irbesartan', 'telmisartan', 'candesartan', 'olmesartan'],
            
            # Calcium Channel Blockers
            'calcium_blockers': ['amlodipine', 'nifedipine', 'diltiazem', 'verapamil', 'felodipine', 'nicardipine'],
            
            # PPIs (Proton Pump Inhibitors)
            'ppis': ['omeprazole', 'pantoprazole', 'esomeprazole', 'lansoprazole', 'rabeprazole', 'dexlansoprazole'],
            
            # H2 Blockers
            'h2_blockers': ['ranitidine', 'famotidine', 'cimetidine', 'nizatidine'],
            
            # Loop Diuretics
            'loop_diuretics': ['furosemide', 'bumetanide', 'torsemide', 'ethacrynic'],
            
            # Thiazide Diuretics
            'thiazide_diuretics': ['hydrochlorothiazide', 'chlorthalidone', 'indapamide', 'metolazone'],
            
            # Potassium-Sparing Diuretics
            'k_sparing_diuretics': ['spironolactone', 'eplerenone', 'amiloride', 'triamterene'],
            
            # SSRIs
            'ssris': ['sertraline', 'fluoxetine', 'paroxetine', 'citalopram', 'escitalopram', 'fluvoxamine'],
            
            # SNRIs
            'snris': ['venlafaxine', 'duloxetine', 'desvenlafaxine', 'levomilnacipran'],
            
            # Benzodiazepines
            'benzos': ['alprazolam', 'lorazepam', 'diazepam', 'clonazepam', 'temazepam', 'midazolam'],
            
            # Sulfonylureas
            'sulfonylureas': ['glipizide', 'glyburide', 'glimepiride'],
            
            # DPP-4 Inhibitors
            'dpp4_inhibitors': ['sitagliptin', 'saxagliptin', 'linagliptin', 'alogliptin'],
            
            # GLP-1 Agonists
            'glp1_agonists': ['liraglutide', 'semaglutide', 'dulaglutide', 'exenatide'],
            
            # SGLT2 Inhibitors
            'sglt2_inhibitors': ['empagliflozin', 'dapagliflozin', 'canagliflozin', 'ertugliflozin'],
            
            # Opioids
            'opioids': ['morphine', 'oxycodone', 'hydrocodone', 'codeine', 'tramadol', 'fentanyl', 'hydromorphone'],
            
            # Respiratory - Inhaled Corticosteroids (ICS)
            'ics': ['fluticasone', 'budesonide', 'beclomethasone', 'mometasone', 'ciclesonide'],
            
            # Respiratory - Long-Acting Beta Agonists (LABA)
            'laba': ['salmeterol', 'formoterol', 'vilanterol', 'indacaterol', 'olodaterol'],
            
            # Respiratory - Short-Acting Beta Agonists (SABA)
            'saba': ['albuterol', 'levalbuterol', 'pirbuterol'],
            
            # Respiratory - Long-Acting Muscarinic Antagonists (LAMA)
            'lama': ['tiotropium', 'umeclidinium', 'aclidinium', 'glycopyrrolate', 'revefenacin'],
            
            # Respiratory - Short-Acting Muscarinic Antagonists (SAMA)
            'sama': ['ipratropium'],
            
            # Anticoagulants - Direct Oral
            'doacs': ['apixaban', 'rivaroxaban', 'edoxaban', 'dabigatran'],
            
            # Penicillins
            'penicillins': ['amoxicillin', 'ampicillin', 'penicillin', 'amoxicillin-clavulanate', 'piperacillin'],
            
            # Cephalosporins
            'cephalosporins': ['cephalexin', 'cefuroxime', 'ceftriaxone', 'cefdinir', 'cefixime'],
            
            # Macrolides
            'macrolides': ['azithromycin', 'clarithromycin', 'erythromycin'],
            
            # Fluoroquinolones
            'fluoroquinolones': ['ciprofloxacin', 'levofloxacin', 'moxifloxacin', 'ofloxacin'],
        }
        
        # Appropriate combinations (won't be marked as redundant even if same class)
        self.appropriate_combinations = [
            ('spironolactone', 'furosemide'),  # K-sparing + loop for cirrhosis
            ('hydrochlorothiazide', 'spironolactone'),  # Thiazide + K-sparing
            ('aspirin', 'clopidogrel'),  # DAPT
            ('metformin', 'glipizide'),  # Different mechanisms
            ('metformin', 'sitagliptin'),  # Biguanide + DPP-4 inhibitor
            ('metformin', 'empagliflozin'),  # Biguanide + SGLT2 inhibitor
            ('metformin', 'insulin'),  # Oral + injectable
            ('sitagliptin', 'insulin'),  # DPP-4 + insulin
            ('empagliflozin', 'insulin'),  # SGLT2 + insulin
            ('lisinopril', 'amlodipine'),  # ACE-I + CCB
            ('albuterol', 'fluticasone'),  # Rescue + maintenance
            
            # GINA Guidelines - Asthma (ICS + LABA combinations)
            ('fluticasone', 'salmeterol'),  # ICS + LABA
            ('budesonide', 'formoterol'),  # ICS + LABA
            ('beclomethasone', 'formoterol'),  # ICS + LABA
            ('mometasone', 'formoterol'),  # ICS + LABA
            ('fluticasone', 'vilanterol'),  # ICS + LABA
            ('albuterol', 'ipratropium'),  # SABA + SAMA (rescue)
            
            # GOLD Guidelines - COPD (LABA + LAMA, Triple therapy)
            ('tiotropium', 'salmeterol'),  # LAMA + LABA
            ('tiotropium', 'formoterol'),  # LAMA + LABA
            ('umeclidinium', 'vilanterol'),  # LAMA + LABA
            ('aclidinium', 'formoterol'),  # LAMA + LABA
            ('glycopyrrolate', 'formoterol'),  # LAMA + LABA
            ('glycopyrrolate', 'indacaterol'),  # LAMA + LABA
            # Triple therapy (ICS + LABA + LAMA)
            ('fluticasone', 'umeclidinium'),  # ICS + LAMA (part of triple)
            ('budesonide', 'glycopyrrolate'),  # ICS + LAMA (part of triple)
        ]
        
        # Indication-based overlaps (different drug classes, same therapeutic indication)
        # These will be flagged as Category 2 (Overlap with Rationale)
        self.indication_overlaps = [
            # GERD/Acid Reflux - PPIs + H2 Blockers
            {
                'group1': ['omeprazole', 'pantoprazole', 'esomeprazole', 'lansoprazole', 'rabeprazole', 'dexlansoprazole'],
                'group2': ['ranitidine', 'famotidine', 'cimetidine', 'nizatidine'],
                'reason': 'Both treat acid reflux/GERD with different mechanisms (PPI vs H2 blocker)',
                'clinical_note': 'Usually PPI alone is sufficient; combination rarely indicated'
            },
            # Depression - SSRIs + SNRIs
            {
                'group1': ['sertraline', 'fluoxetine', 'paroxetine', 'citalopram', 'escitalopram', 'fluvoxamine'],
                'group2': ['venlafaxine', 'duloxetine', 'desvenlafaxine', 'levomilnacipran'],
                'reason': 'Both treat depression with overlapping mechanisms (serotonin pathways)',
                'clinical_note': 'Combination increases serotonin syndrome risk; usually not recommended'
            },
            # Hypertension - ACE-I + ARBs
            {
                'group1': ['lisinopril', 'enalapril', 'ramipril', 'benazepril', 'captopril', 'fosinopril', 'quinapril'],
                'group2': ['losartan', 'valsartan', 'irbesartan', 'telmisartan', 'candesartan', 'olmesartan'],
                'reason': 'Both affect renin-angiotensin system (ACE inhibitor vs ARB)',
                'clinical_note': 'Combination not recommended due to increased adverse effects without added benefit'
            },
            # Pain - NSAIDs + COX-2 Inhibitors
            {
                'group1': ['ibuprofen', 'naproxen', 'diclofenac', 'indomethacin', 'ketorolac', 'meloxicam'],
                'group2': ['celecoxib'],
                'reason': 'Both are anti-inflammatory agents (non-selective vs COX-2 selective)',
                'clinical_note': 'Combination increases GI and cardiovascular risks; not recommended'
            },
            # Diabetes - Sulfonylureas + Meglitinides
            {
                'group1': ['glipizide', 'glyburide', 'glimepiride'],
                'group2': ['repaglinide', 'nateglinide'],
                'reason': 'Both stimulate insulin secretion (different mechanisms but same effect)',
                'clinical_note': 'Combination increases hypoglycemia risk; usually redundant'
            },
            # Anticoagulation - Warfarin + DOACs
            {
                'group1': ['warfarin'],
                'group2': ['apixaban', 'rivaroxaban', 'edoxaban', 'dabigatran'],
                'reason': 'Both are anticoagulants (vitamin K antagonist vs direct oral anticoagulant)',
                'clinical_note': 'NEVER combine - significantly increases bleeding risk'
            },
            # Benzodiazepines + Z-drugs (sleep)
            {
                'group1': ['alprazolam', 'lorazepam', 'diazepam', 'clonazepam', 'temazepam'],
                'group2': ['zolpidem', 'zaleplon', 'eszopiclone'],
                'reason': 'Both are sedative-hypnotics acting on GABA receptors',
                'clinical_note': 'Combination increases sedation and fall risk; not recommended'
            },
            # Opioids + Benzodiazepines (dangerous combo)
            {
                'group1': ['morphine', 'oxycodone', 'hydrocodone', 'codeine', 'tramadol', 'fentanyl', 'hydromorphone'],
                'group2': ['alprazolam', 'lorazepam', 'diazepam', 'clonazepam', 'temazepam'],
                'reason': 'Opioid + Benzodiazepine combination',
                'clinical_note': 'BLACK BOX WARNING: Increases risk of respiratory depression, coma, and death'
            },
            # Opioids + Z-drugs
            {
                'group1': ['morphine', 'oxycodone', 'hydrocodone', 'codeine', 'tramadol', 'fentanyl', 'hydromorphone'],
                'group2': ['zolpidem', 'zaleplon', 'eszopiclone'],
                'reason': 'Opioid + Z-drug combination',
                'clinical_note': 'Increases CNS depression and respiratory depression risk; use with extreme caution'
            },
            # Multiple antibiotics for same infection (macrolide + fluoroquinolone)
            {
                'group1': ['azithromycin', 'clarithromycin', 'erythromycin'],
                'group2': ['ciprofloxacin', 'levofloxacin', 'moxifloxacin', 'ofloxacin'],
                'reason': 'Both are broad-spectrum antibiotics (macrolide + fluoroquinolone)',
                'clinical_note': 'Dual antibiotic therapy - verify indication; usually monotherapy sufficient for CAP'
            },
            # Macrolide + Penicillin
            {
                'group1': ['azithromycin', 'clarithromycin', 'erythromycin'],
                'group2': ['amoxicillin', 'ampicillin', 'penicillin', 'amoxicillin-clavulanate'],
                'reason': 'Both are antibiotics treating bacterial infections (macrolide + penicillin)',
                'clinical_note': 'Combination therapy - verify indication for dual coverage'
            },
            # Fluoroquinolone + Penicillin
            {
                'group1': ['ciprofloxacin', 'levofloxacin', 'moxifloxacin', 'ofloxacin'],
                'group2': ['amoxicillin', 'ampicillin', 'penicillin', 'amoxicillin-clavulanate'],
                'reason': 'Both are antibiotics treating bacterial infections (fluoroquinolone + penicillin)',
                'clinical_note': 'Combination therapy - verify indication for dual coverage'
            },
            # GINA/GOLD - Respiratory combinations that need verification
            # ICS + ICS (redundant)
            {
                'group1': ['fluticasone', 'budesonide', 'beclomethasone', 'mometasone', 'ciclesonide'],
                'group2': ['fluticasone', 'budesonide', 'beclomethasone', 'mometasone', 'ciclesonide'],
                'reason': 'Multiple inhaled corticosteroids detected',
                'clinical_note': 'Using multiple ICS products is redundant - consolidate to single ICS or ICS/LABA combination'
            },
            # LABA + LABA (redundant unless part of different combinations)
            {
                'group1': ['salmeterol', 'formoterol', 'vilanterol', 'indacaterol', 'olodaterol'],
                'group2': ['salmeterol', 'formoterol', 'vilanterol', 'indacaterol', 'olodaterol'],
                'reason': 'Multiple long-acting beta agonists detected',
                'clinical_note': 'Multiple LABAs may be redundant unless in fixed-dose ICS/LABA combinations - verify'
            },
            # LAMA + LAMA (redundant)
            {
                'group1': ['tiotropium', 'umeclidinium', 'aclidinium', 'glycopyrrolate', 'revefenacin'],
                'group2': ['tiotropium', 'umeclidinium', 'aclidinium', 'glycopyrrolate', 'revefenacin'],
                'reason': 'Multiple long-acting muscarinic antagonists detected',
                'clinical_note': 'Multiple LAMAs are redundant - use only one LAMA'
            },
            # SABA + SABA (redundant)
            {
                'group1': ['albuterol', 'levalbuterol', 'pirbuterol'],
                'group2': ['albuterol', 'levalbuterol', 'pirbuterol'],
                'reason': 'Multiple short-acting beta agonists detected',
                'clinical_note': 'Multiple SABAs are redundant - use only one rescue inhaler'
            },
            # CRITICAL GINA 2024: SABA-only treatment for asthma (CONTRAINDICATED)
            {
                'group1': ['albuterol', 'levalbuterol', 'pirbuterol'],
                'group2': [],  # Empty group2 means we're checking for SABA without ICS
                'reason': 'SABA-only treatment detected for asthma patient',
                'clinical_note': 'CRITICAL GINA VIOLATION: SABA alone is contraindicated for asthma. Patient MUST receive ICS-containing treatment (ICS alone or ICS+LABA combination)'
            },
        ]
        
        # Critical single-drug warnings (need special handling)
        self.critical_monotherapy_warnings = {
            'asthma_saba_only': {
                'drugs': ['albuterol', 'levalbuterol', 'pirbuterol'],
                'required_with': ['fluticasone', 'budesonide', 'beclomethasone', 'mometasone', 'ciclesonide'],
                'diagnosis_keywords': ['asthma'],
                'warning': 'CRITICAL GINA 2024 VIOLATION: SABA-only treatment is CONTRAINDICATED for asthma. Patient must receive ICS-containing controller therapy.'
            }
        }
    
    # ============================================================================
    # PART 1: EXTRACT THERAPEUTIC DATA FROM FDA
    # ============================================================================
    
    def extract_therapeutic_data(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Extract Mechanism of Action, Indication, and Pharmacologic Class"""
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
            
            # Extract therapeutic information
            therapeutic_info = {
                'drug_name': medicine_name,
                'mechanism_of_action': self._extract_text(label_data, 'mechanism_of_action'),
                'indications_and_usage': self._extract_text(label_data, 'indications_and_usage'),
                'pharmacologic_class': self._extract_pharmacologic_class(label_data),
                'drug_interactions': self._extract_text(label_data, 'drug_interactions')
            }
            
            return therapeutic_info
            
        except Exception as e:
            print(f"Error extracting data for {medicine_name}: {str(e)}")
            return None
    
    def _extract_text(self, label_data: Dict[str, Any], field_name: str) -> Optional[str]:
        """Helper to extract text from FDA label field"""
        field_data = label_data.get(field_name, [])
        if field_data and len(field_data) > 0:
            text = "\n\n".join(field_data)
            return text[:500] if len(text) > 500 else text
        return None
    
    def _extract_pharmacologic_class(self, label_data: Dict[str, Any]) -> Optional[str]:
        """Extract pharmacologic class from openfda section"""
        openfda = label_data.get('openfda', {})
        
        # Try multiple fields
        pharm_class = openfda.get('pharm_class_epc', [])
        if not pharm_class:
            pharm_class = openfda.get('pharm_class_moa', [])
        if not pharm_class:
            pharm_class = openfda.get('pharm_class_cs', [])
        
        if pharm_class and len(pharm_class) > 0:
            return ", ".join(pharm_class[:3])
        return None
    
    def extract_all_medicines(self, medicine_list: List[str]) -> Dict[str, Any]:
        """Extract therapeutic data for all medicines"""
        print("\n" + "=" * 80)
        print("PART 1: EXTRACTING THERAPEUTIC DATA FROM FDA")
        print("=" * 80 + "\n")
        
        extracted_data = {}
        
        for i, medicine in enumerate(medicine_list, 1):
            print(f"[{i}/{len(medicine_list)}] Extracting: {medicine}...")
            data = self.extract_therapeutic_data(medicine)
            
            if data:
                found = []
                if data['mechanism_of_action']: found.append("MoA")
                if data['indications_and_usage']: found.append("Indication")
                if data['pharmacologic_class']: found.append("Pharm Class")
                
                print(f"  ✓ Found: {', '.join(found) if found else 'no data'}")
                if data['pharmacologic_class']:
                    print(f"    Class: {data['pharmacologic_class'][:80]}...")
                extracted_data[medicine] = data
            else:
                print(f"  ✗ No FDA data found")
                extracted_data[medicine] = None
            
            time.sleep(0.3)
        
        print("\n" + "=" * 80)
        print(f"Extraction complete: {len(extracted_data)} medicines")
        print("=" * 80 + "\n")
        
        return extracted_data
    
    # ============================================================================
    # PART 2: IDENTIFY DUPLICATIONS - SIMPLIFIED 3-CATEGORY APPROACH
    # ============================================================================
    
    def identify_duplications(
        self,
        extracted_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compare medicines using simplified 3-category approach"""
        print("\n" + "=" * 80)
        print("PART 2: IDENTIFYING THERAPEUTIC DUPLICATIONS")
        print("=" * 80 + "\n")
        
        results = []
        
        # Get valid medicines
        valid_medicines = {name: data for name, data in extracted_data.items() if data is not None}
        
        if len(valid_medicines) < 2:
            print("Less than 2 medicines with valid FDA data to compare.\n")
            return results
        
        # Compare each pair
        medicine_pairs = list(combinations(valid_medicines.keys(), 2))
        
        for med1, med2 in medicine_pairs:
            print(f"Comparing: {med1} vs {med2}")
            
            result = self._categorize_pair(
                med1, 
                valid_medicines[med1],
                med2,
                valid_medicines[med2]
            )
            
            results.append(result)
            
            if result['category'] == 'redundant':
                print(f"  ❌ REDUNDANT/DUPLICATE")
            elif result['category'] == 'overlap':
                print(f"  ⚠️  OVERLAP WITH RATIONALE")
            else:
                print(f"  ✓ UNIQUE ROLES")
            print()
        
        print("=" * 80)
        redundant = len([r for r in results if r['category'] == 'redundant'])
        overlap = len([r for r in results if r['category'] == 'overlap'])
        unique = len([r for r in results if r['category'] == 'unique'])
        print(f"Summary: {redundant} redundant, {overlap} overlap, {unique} unique")
        print("=" * 80 + "\n")
        
        return results
    
    def _categorize_pair(
        self,
        med1_name: str,
        med1_data: Dict[str, Any],
        med2_name: str,
        med2_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Categorize medicine pair into 3 categories:
        1. Redundant/Duplicate - Same exact class, high duplication
        2. Overlap with Rationale - Some overlap but may be appropriate
        3. Unique - No significant overlap
        """
        
        med1_lower = med1_name.lower().strip()
        med2_lower = med2_name.lower().strip()
        
        print(f"  DEBUG: Checking {med1_lower} vs {med2_lower}")
        
        # STEP 1: Check if medicines are in same predefined class (STRICT CHECK)
        same_class_name = None
        med1_class = None
        med2_class = None
        
        # Find which class each medicine belongs to
        for class_name, drug_list in self.drug_classes.items():
            for drug in drug_list:
                if med1_lower in drug.lower() or drug.lower() in med1_lower:
                    med1_class = class_name
                    print(f"  DEBUG: {med1_lower} matched to class: {class_name}")
                if med2_lower in drug.lower() or drug.lower() in med2_lower:
                    med2_class = class_name
                    print(f"  DEBUG: {med2_lower} matched to class: {class_name}")
        
        # Check if both diuretics (special handling for diuretic subclasses)
        is_diuretic_combo = False
        if med1_class and med2_class:
            if 'diuretic' in med1_class and 'diuretic' in med2_class:
                is_diuretic_combo = True
                same_class_name = 'diuretics_combined'
                print(f"  DEBUG: Both are diuretics! {med1_class} + {med2_class}")
            elif med1_class == med2_class:
                same_class_name = med1_class
                print(f"  DEBUG: Same class detected: {same_class_name}")
        
        if same_class_name:
            # Check if this is an appropriate combination
            is_appropriate = self._is_appropriate_combination(med1_lower, med2_lower)
            
            if is_appropriate:
                # Category 2: Overlap with Rationale
                return {
                    'medicine_1': med1_name,
                    'medicine_2': med2_name,
                    'category': 'overlap',
                    'reason': f'Both are from {same_class_name.replace("_", " ")} class but combination is clinically recognized',
                    'recommendation': f'✓ Appropriate combination - verify indication and dosing',
                    'evidence': f'Class: {same_class_name.replace("_", " ")}'
                }
            else:
                # Category 1: Redundant/Duplicate
                return {
                    'medicine_1': med1_name,
                    'medicine_2': med2_name,
                    'category': 'redundant',
                    'reason': f'Both belong to same drug class: {same_class_name.replace("_", " ")}',
                    'recommendation': f'⚠️ REDUNDANT - Review if both are necessary. Consider discontinuing one.',
                    'evidence': f'Class: {same_class_name.replace("_", " ")}'
                }
        
        # STEP 2: Check for indication-based overlaps (different classes, same indication)
        indication_overlap = self._check_indication_overlap(med1_lower, med2_lower)
        if indication_overlap:
            return {
                'medicine_1': med1_name,
                'medicine_2': med2_name,
                'category': 'overlap',
                'reason': indication_overlap['reason'],
                'recommendation': f'⚠️ {indication_overlap["clinical_note"]}',
                'evidence': 'Different drug classes but overlapping therapeutic indication'
            }
        # STEP 3: Check pharmacologic class from FDA (BROADER CHECK)
        pharm1 = (med1_data.get('pharmacologic_class') or '').lower()
        pharm2 = (med2_data.get('pharmacologic_class') or '').lower()
        
        if pharm1 and pharm2:
            # Check for class similarity
            class_overlap = self._check_class_overlap(pharm1, pharm2)
            
            if class_overlap:
                # Category 2: Overlap with Rationale
                return {
                    'medicine_1': med1_name,
                    'medicine_2': med2_name,
                    'category': 'overlap',
                    'reason': f'Similar pharmacologic classes detected',
                    'recommendation': f'⚠️ Verify clinical rationale for combination. Check guidelines.',
                    'evidence': f'Class 1: {pharm1[:60]}... | Class 2: {pharm2[:60]}...'
                }
        
        # STEP 4: Check Mechanism of Action (MODERATE CHECK)
        moa1 = (med1_data.get('mechanism_of_action') or '').lower()
        moa2 = (med2_data.get('mechanism_of_action') or '').lower()
        
        if moa1 and moa2 and len(moa1) > 50 and len(moa2) > 50:
            moa_similar = self._check_moa_overlap(moa1, moa2)
            
            if moa_similar:
                # Category 2: Overlap with Rationale
                return {
                    'medicine_1': med1_name,
                    'medicine_2': med2_name,
                    'category': 'overlap',
                    'reason': f'Similar mechanisms of action detected',
                    'recommendation': f'ℹ️ Review mechanism overlap. May be appropriate depending on indication.',
                    'evidence': f'Both have similar molecular mechanisms'
                }
        
        # STEP 5: Default to Unique (no significant overlap found)
        return {
            'medicine_1': med1_name,
            'medicine_2': med2_name,
            'category': 'unique',
            'reason': 'No significant overlap detected',
            'recommendation': '✓ Medications appear to have unique therapeutic roles',
            'evidence': 'Different classes and mechanisms'
        }
    
    def _is_appropriate_combination(self, med1: str, med2: str) -> bool:
        """Check if combination is in appropriate list"""
        for combo in self.appropriate_combinations:
            if (combo[0] in med1 and combo[1] in med2) or \
               (combo[1] in med1 and combo[0] in med2):
                return True
        return False
    
    def _check_indication_overlap(self, med1: str, med2: str) -> Optional[Dict[str, str]]:
        """Check if medicines have overlapping therapeutic indications (different classes)"""
        for overlap in self.indication_overlaps:
            group1_match = any(drug in med1 or med1 in drug for drug in overlap['group1'])
            group2_match = any(drug in med2 or med2 in drug for drug in overlap['group2'])
            
            # Check both directions (group1 vs group2)
            if (group1_match and group2_match):
                return {
                    'reason': overlap['reason'],
                    'clinical_note': overlap['clinical_note']
                }
            
            # Also check reverse direction (group2 vs group1)
            group1_match_rev = any(drug in med2 or med2 in drug for drug in overlap['group1'])
            group2_match_rev = any(drug in med1 or med1 in drug for drug in overlap['group2'])
            
            if (group1_match_rev and group2_match_rev):
                return {
                    'reason': overlap['reason'],
                    'clinical_note': overlap['clinical_note']
                }
            
            # Special case: Check if BOTH medicines are in the SAME group (redundancy)
            # This handles cases like ICS + ICS, LABA + LABA
            both_in_group1 = (any(drug in med1 or med1 in drug for drug in overlap['group1']) and 
                             any(drug in med2 or med2 in drug for drug in overlap['group1']))
            both_in_group2 = (any(drug in med1 or med1 in drug for drug in overlap['group2']) and 
                             any(drug in med2 or med2 in drug for drug in overlap['group2']))
            
            if both_in_group1 or both_in_group2:
                return {
                    'reason': overlap['reason'],
                    'clinical_note': overlap['clinical_note']
                }
        
        return None
    
    def _check_class_overlap(self, class1: str, class2: str) -> bool:
        """Check if pharmacologic classes overlap - STRICT matching"""
        
        # Remove FDA classification codes that appear in all drugs
        class1_clean = class1.replace('[epc]', '').replace('[moa]', '').replace('[cs]', '').strip()
        class2_clean = class2.replace('[epc]', '').replace('[moa]', '').replace('[cs]', '').strip()
        
        # Key terms that indicate same class (specific drug classes only)
        class_indicators = [
            'statin', 'hmg-coa reductase inhibitor',
            'nsaid', 'nonsteroidal anti-inflammatory',
            'beta blocker', 'beta-adrenergic blocker',
            'ace inhibitor', 'angiotensin converting enzyme inhibitor',
            'arb', 'angiotensin receptor blocker', 'angiotensin ii receptor antagonist',
            'calcium channel blocker', 'calcium channel antagonist',
            'proton pump inhibitor',
            'h2 receptor antagonist', 'histamine h2 receptor antagonist',
            'ssri', 'selective serotonin reuptake inhibitor',
            'snri', 'serotonin norepinephrine reuptake inhibitor',
            'loop diuretic',
            'thiazide diuretic',
            'potassium-sparing diuretic', 'aldosterone antagonist',
            'sulfonylurea',
            'dpp-4 inhibitor',
            'sglt2 inhibitor',
            'glp-1 agonist', 'glucagon-like peptide-1 receptor agonist',
            'benzodiazepine',
            'opioid agonist',
            'direct oral anticoagulant', 'factor xa inhibitor', 'thrombin inhibitor',
            'penicillin',
            'cephalosporin',
            'macrolide',
            'fluoroquinolone',
        ]
        
        # Check if both contain the SAME specific class indicator
        for indicator in class_indicators:
            if indicator in class1_clean.lower() and indicator in class2_clean.lower():
                return True
        
        # Check for substantial meaningful word overlap (at least 3 words, each >5 chars)
        class1_words = set(class1_clean.lower().split())
        class2_words = set(class2_clean.lower().split())
        
        # Filter out common/generic terms
        stopwords = {
            'and', 'or', 'the', 'a', 'an', 'in', 'of', 'for', 'to', 'with', 'by', 'as', 'is', 'at',
            'agent', 'drug', 'class', 'inhibitor', 'antagonist', 'agonist', 'receptor', 'blocker'
        }
        
        meaningful1 = {w for w in class1_words if len(w) > 5} - stopwords
        meaningful2 = {w for w in class2_words if len(w) > 5} - stopwords
        common = meaningful1.intersection(meaningful2)
        
        # Require at least 3 meaningful common words for a match
        return len(common) >= 3
    
    def _check_moa_overlap(self, moa1: str, moa2: str) -> bool:
        """Check if mechanisms overlap - STRICT matching for specific mechanisms"""
        
        # Specific mechanism patterns (not just generic keywords)
        specific_mechanisms = [
            # Enzyme inhibition (specific enzymes)
            'hmg-coa reductase',
            'ace inhibit',  # angiotensin converting enzyme
            'cox-1',
            'cox-2',
            'cyclooxygenase',
            'proton pump',
            'dpp-4',
            'mao inhibit',
            'phosphodiesterase',
            'aromatase',
            
            # Receptor interactions (specific receptors)
            'beta-1 adrenergic',
            'beta-2 adrenergic',
            'beta adrenergic receptor',
            'alpha-1 adrenergic',
            'alpha-2 adrenergic',
            'serotonin reuptake',
            'norepinephrine reuptake',
            'dopamine reuptake',
            'angiotensin ii receptor',
            'histamine h1 receptor',
            'histamine h2 receptor',
            'opioid receptor',
            'gaba receptor',
            'nmda receptor',
            
            # Ion channels
            'calcium channel',
            'sodium channel',
            'potassium channel',
            
            # Transport/reuptake
            'serotonin transporter',
            'norepinephrine transporter',
            'dopamine transporter',
            
            # Other specific mechanisms
            'dihydrofolate reductase',
            'thrombin inhibit',
            'factor xa inhibit',
            'platelet aggregation',
        ]
        
        # Find specific mechanism matches
        moa1_specific = [m for m in specific_mechanisms if m in moa1]
        moa2_specific = [m for m in specific_mechanisms if m in moa2]
        
        # Check for common SPECIFIC mechanisms
        common_specific = set(moa1_specific).intersection(set(moa2_specific))
        
        # Require at least 1 SPECIFIC mechanism match (not just generic keywords)
        return len(common_specific) >= 1
    
    def _check_critical_monotherapy(self, patient_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        CRITICAL: Check for dangerous monotherapy patterns (e.g., SABA-only for asthma)
        Returns list of critical warnings
        """
        warnings = []
        medicines = [m.lower().strip() for m in patient_data.get('prescription', [])]
        
        # Get patient diagnosis
        diagnosis = patient_data.get('patient', {}).get('diagnosis', '').lower()
        condition = patient_data.get('patient', {}).get('condition', '').lower()
        patient_info = f"{diagnosis} {condition}"
        
        # Check SABA-only for asthma (CRITICAL GINA 2024)
        saba_warning = self.critical_monotherapy_warnings['asthma_saba_only']
        
        # Check if patient has asthma
        has_asthma = any(keyword in patient_info for keyword in saba_warning['diagnosis_keywords'])
        
        if has_asthma:
            # Check if patient is on any SABA
            has_saba = any(saba in med or med in saba for med in medicines for saba in saba_warning['drugs'])
            
            # Check if patient has any ICS (controller)
            has_ics = any(ics in med or med in ics for med in medicines for ics in saba_warning['required_with'])
            
            # CRITICAL: SABA without ICS
            if has_saba and not has_ics:
                warnings.append({
                    'severity': 'CRITICAL',
                    'type': 'SABA_ONLY_ASTHMA',
                    'message': saba_warning['warning'],
                    'guideline': 'GINA 2024',
                    'action_required': 'Add ICS-containing controller therapy immediately'
                })
        
        return warnings
    
    # ============================================================================
    # PART 3: GENERATE REPORT
    # ============================================================================
    
    def generate_report(
        self,
        patient_data: Dict[str, Any],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate simplified report"""
        
        total_medicines = len(patient_data.get('prescription', []))
        
        # Categorize
        redundant = [r for r in results if r['category'] == 'redundant']
        overlap = [r for r in results if r['category'] == 'overlap']
        unique = [r for r in results if r['category'] == 'unique']
        
        # Summary
        if redundant:
            summary = f"❌ CRITICAL: {len(redundant)} redundant/duplicate prescription(s) found"
        elif overlap:
            summary = f"⚠️ CAUTION: {len(overlap)} medication pair(s) with overlap detected"
        else:
            summary = f"✓ All {len(unique)} medication pair(s) have unique roles"
        
        report = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'patient': {
                'age': patient_data['patient'].get('age'),
                'gender': patient_data['patient'].get('gender'),
                'diagnosis': patient_data['patient'].get('diagnosis'),
                'condition': patient_data['patient'].get('condition')
            },
            'total_medications_reviewed': total_medicines,
            'summary': summary,
            'redundant_duplicate': redundant,
            'overlap_with_rationale': overlap,
            'unique_no_overlap': unique
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """Print simplified report"""
        print("\n" + "=" * 80)
        print("THERAPEUTIC DUPLICATION REPORT")
        print("=" * 80)
        print(f"\nPatient: {report['patient']['age']}y {report['patient']['gender']}")
        print(f"Diagnosis: {report['patient']['diagnosis']}")
        print(f"Condition: {report['patient']['condition']}")
        print(f"Total Medications: {report['total_medications_reviewed']}")
        
        print(f"\n{report['summary']}")
        print("=" * 80)
        
        # Category 1: Redundant/Duplicate
        if report['redundant_duplicate']:
            print("\n❌ CATEGORY 1: REDUNDANT/DUPLICATE PRESCRIPTION\n")
            for item in report['redundant_duplicate']:
                print(f"  ❌ {item['medicine_1']} + {item['medicine_2']}")
                print(f"     Reason: {item['reason']}")
                print(f"     Evidence: {item['evidence']}")
                print(f"     {item['recommendation']}")
                print()
        
        # Category 2: Overlap with Rationale
        if report['overlap_with_rationale']:
            print("\n⚠️  CATEGORY 2: SOME OVERLAP BUT WITH RATIONALE\n")
            for item in report['overlap_with_rationale']:
                print(f"  ⚠️  {item['medicine_1']} + {item['medicine_2']}")
                print(f"     Reason: {item['reason']}")
                print(f"     {item['recommendation']}")
                print()
        
        # Category 3: Unique
        if report['unique_no_overlap']:
            print("\n✓ CATEGORY 3: UNIQUE ROLE, NO OVERLAP\n")
            for item in report['unique_no_overlap']:
                print(f"  ✓ {item['medicine_1']} + {item['medicine_2']}")
                print(f"     {item['recommendation']}")
        
        print("\n" + "=" * 80 + "\n")
    
    # ============================================================================
    # MAIN WORKFLOW
    # ============================================================================
    
    def analyze(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main workflow"""
        medicines = patient_data.get('prescription', [])
        
        if len(medicines) < 2:
            print("\n⚠️  Need at least 2 medications to check for duplications.\n")
            return {
                'summary': 'Not enough medications to analyze',
                'redundant_duplicate': [],
                'overlap_with_rationale': [],
                'unique_no_overlap': []
            }
        
        # Extract data
        extracted_data = self.extract_all_medicines(medicines)
        
        # Identify duplications
        results = self.identify_duplications(extracted_data)
        
        # Generate report
        report = self.generate_report(patient_data, results)
        
        return report


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("THERAPEUTIC DUPLICATION CHECKER - SIMPLIFIED 3-CATEGORY APPROACH")
    print("Category 1: Redundant/Duplicate | Category 2: Overlap | Category 3: Unique")
    print("=" * 80)
    
    # Load patient input
    try:
        with open('patient_input.json', 'r') as f:
            patient_input = json.load(f)
    except FileNotFoundError:
        print("\n❌ Error: patient_input.json not found!")
        return
    except json.JSONDecodeError:
        print("\n❌ Error: Invalid JSON in patient_input.json")
        return
    
    # Initialize checker
    checker = TherapeuticDuplicationChecker()
    
    # Run analysis
    report = checker.analyze(patient_input)
    
    # Print report
    checker.print_report(report)
    
    # Save report
    output_file = f"therapeutic_duplication_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Detailed report saved to: {output_file}\n")


if __name__ == "__main__":
    main()
