import json
from adrs.analyzer import Factor_3_2_3_3_Analyzer_Fixed

import json
import os
from scoring.benefit_factor import get_lt_adr_data, get_serious_adr_data, get_drug_interaction_data

def start(drug, scoring_system=None):
    analyzer = Factor_3_2_3_3_Analyzer_Fixed()
    
    with open("../adrs_input.json", 'r') as f:
        patient_data = json.load(f)
        results = analyzer.analyze(patient_data)
        
        # Calculate Scores
        lt_score = get_lt_adr_data(results, scoring_system)
        serious_score = get_serious_adr_data(results, scoring_system)
        interaction_score = get_drug_interaction_data(results, scoring_system)
        
        # Attach scores to the results object for the worker to see
        results['scoring'] = {
            'lt_adr_score': lt_score,
            'serious_adr_score': serious_score,
            'interaction_score': interaction_score
        }

        output_path = os.path.join("..", "adrs_output.json")
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        return results