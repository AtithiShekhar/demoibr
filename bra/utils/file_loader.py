"""
utils/file_loader.py
Utility to load input.json file
"""

import json
import os
import sys


def load_input(filename: str = "input.json") -> dict:
    """
    Load input JSON file
    
    Args:
        filename: Path to input JSON file (default: input.json)
        
    Returns:
        Dictionary with input data or None if error
    """
    try:
        if not os.path.exists(filename):
            print(f"Error: Input file '{filename}' not found.")
            print(f"\nPlease create {filename} with the following format:")
            sample_data = {
                "Drug": "Amoxicillin",
                "Condition": "Bacterial Infection",
                "PubMed": {
                    "email": "your_email@example.com"
                }
            }
            print(json.dumps(sample_data, indent=2))
            
            # Create sample file
            try:
                with open(filename, 'w') as f:
                    json.dump(sample_data, f, indent=2)
                print(f"\nCreated sample {filename}. Please edit it with your data.")
            except Exception as e:
                print(f"Could not create sample file: {e}")
            
            return None
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Validate required fields
        required_fields = ["Drug", "Condition"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Error: Missing required fields in {filename}: {', '.join(missing_fields)}")
            return None
        
        # Validate data
        if not data["Drug"] or not data["Condition"]:
            print("Error: Drug and Condition cannot be empty")
            return None
        
        return data
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filename}: {e}")
        return None
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None


def load_input_with_defaults(filename: str = "input.json") -> dict:
    """
    Load input JSON with default values
    
    Returns:
        Dictionary with input data (with defaults for missing fields)
    """
    data = load_input(filename)
    if not data:
        sys.exit(1)
    
    # Set defaults for optional fields
    if "PubMed" not in data:
        data["PubMed"] = {}
    
    if "email" not in data["PubMed"]:
        data["PubMed"]["email"] = "your_email@example.com"
    
    return data