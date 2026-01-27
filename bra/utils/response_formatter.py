# ================================
# utils/response_formatter.py (NEW FILE)
# ================================

"""
Response Formatter - Creates clean, concise API responses
"""

from typing import Dict, List, Any


def format_drug_result(result: Dict) -> Dict:
    """
    Format a single drug analysis result to include only essential fields
    
    Args:
        result: Full analysis result from worker
        
    Returns:
        Clean, concise result dictionary
    """
    if not result.get("success"):
        return {
            "drug": result.get("drug"),
            "diagnosis": result.get("diagnosis"),
            "status": "failed",
            "error": result.get("error")
        }
    
    # Extract only essential data
    return {
        "drug": result.get("drug"),
        "diagnosis": result.get("diagnosis"),
        "status": "completed",
        "scores": {
            "total_benefit": result.get("total_benefit_score", 0),
            "total_risk": result.get("total_risk_score", 0),
            "brr": result.get("brr"),
            "brr_interpretation": result.get("brr_interpretation")
        },
        "rct_count": result.get("rct_count", 0),
        "has_contraindication": result.get("has_contraindication", False),
        "duplication_checked": result.get("duplication_checked", False)
    }


def format_alternative_result(alt_result: Dict) -> Dict:
    """
    Format alternative medication analysis result
    
    Args:
        alt_result: Full alternative analysis result
        
    Returns:
        Clean alternative result
    """
    if not alt_result.get("success"):
        return {
            "drug": alt_result.get("drug"),
            "status": "failed",
            "error": alt_result.get("error")
        }
    
    alt_info = alt_result.get("alternative_info", {})
    
    return {
        "drug": alt_result.get("drug"),
        "brand_name": alt_info.get("brand_name"),
        "rank": alt_info.get("alternative_rank"),
        "scores": {
            "total_benefit": alt_result.get("total_benefit_score", 0),
            "total_risk": alt_result.get("total_risk_score", 0),
            "brr": alt_result.get("brr"),
            "brr_interpretation": alt_result.get("brr_interpretation")
        },
        "rct_count": alt_result.get("rct_count", 0),
        "has_contraindication": alt_result.get("has_contraindication", False)
    }


def format_complete_response(results: List[Dict]) -> Dict:
    """
    Format complete analysis response with all medications
    NOTE: Results already contain alternatives attached to their primary drugs
    
    Args:
        results: List of analysis results from workers (already grouped)
        
    Returns:
        Clean, structured response
    """
    medications = []
    
    for result in results:
        if not result.get("success"):
            medications.append({
                "primary": format_drug_result(result),
                "alternatives": []
            })
            continue
        
        # Format primary medication
        primary = format_drug_result(result)
        
        # Format alternatives if present (already in result from worker)
        alternatives = []
        alt_analyses = result.get("alternative_analyses", [])
        for alt in alt_analyses:
            alternatives.append(format_alternative_result(alt))
        
        medications.append({
            "primary": primary,
            "alternatives": alternatives if alternatives else None
        })
    
    # Calculate summary statistics
    successful = [r for r in results if r.get("success")]
    total_meds = len(results)
    contraindicated = sum(1 for r in successful if r.get("has_contraindication"))
    alternatives_found = sum(1 for r in successful if r.get("alternatives_count", 0) > 0)
    
    # Find highest and lowest BRR (only from primary medications)
    brr_values = []
    for r in successful:
        brr = r.get("brr")
        if brr and brr != "Infinity":
            brr_values.append({
                "drug": r.get("drug"),
                "diagnosis": r.get("diagnosis"),
                "brr": brr
            })
    
    highest_brr = max(brr_values, key=lambda x: x["brr"]) if brr_values else None
    lowest_brr = min(brr_values, key=lambda x: x["brr"]) if brr_values else None
    
    return {
        "summary": {
            "total_medications": total_meds,
            "successful_analyses": len(successful),
            "medications_with_contraindication": contraindicated,
            "alternatives_provided": alternatives_found,
            "highest_brr": highest_brr,
            "lowest_brr": lowest_brr
        },
        "medications": medications
    }


# ================================
# utils/queue_manager/queue_manager.py (UPDATED _collect_results)
# ================================

def _collect_results(self, results_dir: str, workspace_dir: str) -> Dict:
    """
    Collect and format results from results directory
    
    Args:
        results_dir: Path to results directory
        workspace_dir: Path to workspace directory
        
    Returns:
        Dictionary with formatted results
    """
    from utils.response_formatter import format_complete_response
    import json
    import os
    
    raw_results = []
    
    if not os.path.exists(results_dir):
        return None
    
    # Collect individual result files
    for filename in sorted(os.listdir(results_dir)):
        if filename.endswith(".json") and not filename.startswith("analysis_summary_"):
            file_path = os.path.join(results_dir, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Parse filename
                base_name = filename.replace("_result.json", "")
                parts = base_name.split("_")
                
                if len(parts) >= 2:
                    medicine_name = parts[0]
                    condition = "_".join(parts[1:]).replace("_", " ")
                else:
                    medicine_name = "Unknown"
                    condition = "Unknown"
                
                # Extract key data from analyses
                analyses = data.get("analyses", {})
                summary = analyses.get("summary", {})
                brr_data = data.get("benefit_risk_ratio", {})
                
                # Check for alternatives in the same directory
                alt_results = []
                alt_prefix = f"{medicine_name}_ALT"
                for alt_file in os.listdir(results_dir):
                    if alt_file.startswith(alt_prefix) and alt_file.endswith("_result.json"):
                        try:
                            alt_path = os.path.join(results_dir, alt_file)
                            with open(alt_path, "r") as af:
                                alt_data = json.load(af)
                            
                            alt_summary = alt_data.get("analyses", {}).get("summary", {})
                            alt_brr = alt_data.get("benefit_risk_ratio", {})
                            
                            # Extract alt name from filename
                            alt_base = alt_file.replace("_result.json", "")
                            alt_drug_name = alt_base.split("_ALT")[1].split("_")[0] if "_ALT" in alt_base else "Unknown"
                            
                            alt_results.append({
                                "success": True,
                                "drug": alt_drug_name,
                                "total_benefit_score": brr_data.get("total_benefit_score", 0),
                                "total_risk_score": brr_data.get("total_risk_score", 0),
                                "brr": brr_data.get("brr"),
                                "brr_interpretation": brr_data.get("interpretation"),
                                "rct_count": alt_summary.get("rct_count", 0),
                                "has_contraindication": alt_summary.get("has_contraindication", False),
                                "alternative_info": {
                                    "brand_name": alt_drug_name,
                                    "alternative_rank": len(alt_results) + 1
                                }
                            })
                        except Exception as e:
                            print(f"Error reading alternative {alt_file}: {e}")
                
                raw_results.append({
                    "success": True,
                    "drug": medicine_name,
                    "diagnosis": condition,
                    "total_benefit_score": brr_data.get("total_benefit_score", 0),
                    "total_risk_score": brr_data.get("total_risk_score", 0),
                    "brr": brr_data.get("brr"),
                    "brr_interpretation": brr_data.get("interpretation"),
                    "rct_count": summary.get("rct_count", 0),
                    "has_contraindication": summary.get("has_contraindication", False),
                    "duplication_checked": summary.get("therapeutic_duplication_performed", False),
                    "alternatives_count": len(alt_results),
                    "alternative_analyses": alt_results
                })
            
            except Exception as e:
                print(f"⚠ Error reading {filename}: {e}")
                continue
    
    # Format response using formatter
    return format_complete_response(raw_results)


# ================================
# Example Clean Response
# ================================

"""
{
  "summary": {
    "total_medications": 6,
    "successful_analyses": 6,
    "medications_with_contraindication": 0,
    "alternatives_provided": 0,
    "highest_brr": {
      "drug": "Amlodipine",
      "diagnosis": "Hypertension",
      "brr": "Infinity"
    },
    "lowest_brr": {
      "drug": "Atorvastatin",
      "diagnosis": "Hyperlipidemia",
      "brr": "Infinity"
    }
  },
  "medications": [
    {
      "primary": {
        "drug": "Amlodipine",
        "diagnosis": "Hypertension",
        "status": "completed",
        "scores": {
          "total_benefit": 1190,
          "total_risk": 0,
          "brr": "Infinity",
          "brr_interpretation": "No Risk Detected"
        },
        "rct_count": 954,
        "has_contraindication": false,
        "duplication_checked": true
      },
      "alternatives": null
    },
    {
      "primary": {
        "drug": "SomeContraindicatedDrug",
        "diagnosis": "Condition",
        "status": "completed",
        "scores": {
          "total_benefit": 500,
          "total_risk": 500,
          "brr": 1.0,
          "brr_interpretation": "Acceptable - Benefits slightly outweigh risks"
        },
        "rct_count": 50,
        "has_contraindication": true,
        "duplication_checked": false
      },
      "alternatives": [
        {
          "drug": "Alternative1",
          "brand_name": "AltBrand",
          "rank": 1,
          "scores": {
            "total_benefit": 800,
            "total_risk": 100,
            "brr": 8.0,
            "brr_interpretation": "Excellent - Benefits strongly outweigh risks"
          },
          "rct_count": 200,
          "has_contraindication": false
        }
      ]
    }
  ]
}
"""