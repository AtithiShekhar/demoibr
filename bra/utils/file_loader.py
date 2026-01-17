"""
utils/file_loader.py
Utility to load input.json file and helper functions
"""

import json
import os
import sys


def parse_diagnoses(diagnosis_str: str) -> list:
    """
    Parse comma-separated diagnosis string into list
    
    Args:
        diagnosis_str: Comma-separated diagnosis string
        
    Returns:
        List of individual diagnoses
    """
    return [d.strip() for d in diagnosis_str.split(',')]


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
            return None
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Validate structure - support both old and new format
        # New format: {"patient": {...}, "prescription": [...]}
        # Old format: {"Drug": "...", "Condition": "..."}
        
        # Check for new format (API format)
        if "patient" in data and "prescription" in data:
            # Validate patient structure
            patient = data.get("patient", {})
            if not isinstance(patient, dict):
                print("Error: 'patient' must be a dictionary")
                return None
            
            # Validate prescription structure
            prescription = data.get("prescription", [])
            if not isinstance(prescription, list) or len(prescription) == 0:
                print("Error: 'prescription' must be a non-empty list")
                return None
            
            return data
        
        # Check for old format (direct CLI usage)
        elif "Drug" in data and "Condition" in data:
            # Convert old format to new format
            return {
                "patient": {
                    "age": data.get("age"),
                    "gender": data.get("gender"),
                    "diagnosis": data.get("Condition", ""),
                    "condition": data.get("Condition", ""),
                    "date_of_assessment": data.get("date_of_assessment")
                },
                "prescription": [data.get("Drug")],
                "PubMed": data.get("PubMed", {})
            }
        
        else:
            print("Error: Input JSON must contain either:")
            print("  - New format: 'patient' and 'prescription' fields")
            print("  - Old format: 'Drug' and 'Condition' fields")
            return None
    
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