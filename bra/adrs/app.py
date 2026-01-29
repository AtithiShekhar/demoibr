import json
from adrs.analyzer import Factor_3_2_3_3_Analyzer_Fixed

import json
import os

def start(drug, patient_data, scoring_system=None):
    """
    Analyzes ADRs for a patient and saves the result to a specific JSON file.
    """
    # Initialize the analyzer
    analyzer = Factor_3_2_3_3_Analyzer_Fixed()
    
    # Run the core analysis workflow
    results = analyzer.analyze(patient_data)
    
    # Define the output path in the parent directory
    output_path = os.path.join("..", "adrs_output.json")
    
    # Save the results to the specified file
    try:
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✓ Analysis results saved to: {output_path}")
    except Exception as e:
        print(f"❌ Failed to save results: {str(e)}")
        
    return results

if __name__ == "__main__":
    # Load the patient input from the parent directory
    input_path = os.path.join("..", "adrs_input.json")
    
    try:
        with open(input_path) as f:
            patient_data = json.load(f)
        
        # Execute the start function
        final_results = start(None, patient_data)
        
    except FileNotFoundError:
        print(f"❌ Error: {input_path} not found.")