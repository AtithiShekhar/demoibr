"""
Response Formatter - Comprehensive Clinical Decision Support
Includes ALL analysis details: approval, MME, contraindication, alternatives, consequences, RRM, duplication, PubMed, BRR
"""

from typing import Dict, List, Any, Optional


def interpret_brr(brr: Any, has_contraindication: bool = False) -> Dict[str, Any]:
    """Interpret BRR value according to clinical thresholds"""
    if brr == "Infinity" or brr == float('inf'):
        return {
            "outcome": "✅ Favorable",
            "emoji": "🟢",
            "status": "Favorable",
            "clinical_action": "Benefits outweigh risks; monitor as standard",
            "recommendation": "Safe to use with routine monitoring",
            "color": "green",
            "alert_level": "none"
        }
    
    if not isinstance(brr, (int, float)):
        return {
            "outcome": "⚠️ Unknown",
            "emoji": "⚪",
            "status": "Unknown",
            "clinical_action": "Unable to assess benefit-risk ratio",
            "recommendation": "Requires clinical review",
            "color": "gray",
            "alert_level": "review"
        }
    
    if brr > 6:
        return {
            "outcome": "✅ Favorable",
            "emoji": "🟢",
            "status": "Favorable",
            "clinical_action": "Benefits outweigh risks; monitor as standard",
            "recommendation": "Excellent safety profile - safe to use",
            "color": "green",
            "alert_level": "none"
        }
    elif brr >= 2:
        return {
            "outcome": "⚠️ Conditional",
            "emoji": "🟡",
            "status": "Conditional",
            "clinical_action": "Benefits outweigh risks only with strict monitoring",
            "recommendation": "Use with caution - requires close monitoring",
            "color": "yellow",
            "alert_level": "caution"
        }
    else:
        return {
            "outcome": "❌ Unfavorable",
            "emoji": "🔴",
            "status": "Unfavorable",
            "clinical_action": "Risks outweigh benefits for this patient",
            "recommendation": "Not recommended - consider alternatives immediately",
            "color": "red",
            "alert_level": "critical"
        }


def format_evidence_level(rct_count: int) -> Dict[str, str]:
    """Format clinical evidence quality"""
    if rct_count >= 100:
        return {
            "level": "High Quality Evidence",
            "description": f"Extensively studied with {rct_count}+ clinical trials",
            "confidence": "High",
            "icon": "📊"
        }
    elif rct_count >= 50:
        return {
            "level": "Good Quality Evidence",
            "description": f"Well-studied with {rct_count} clinical trials",
            "confidence": "Good",
            "icon": "📊"
        }
    elif rct_count >= 10:
        return {
            "level": "Moderate Evidence",
            "description": f"Studied with {rct_count} clinical trials",
            "confidence": "Moderate",
            "icon": "📋"
        }
    elif rct_count > 0:
        return {
            "level": "Limited Evidence",
            "description": f"Only {rct_count} clinical trial(s) available",
            "confidence": "Limited",
            "icon": "📋"
        }
    else:
        return {
            "level": "Insufficient Evidence",
            "description": "No clinical trial data available",
            "confidence": "Very Limited",
            "icon": "⚠️"
        }


def extract_full_analysis_details(result_file_path: str) -> Optional[Dict]:
    """Extract ALL analysis details from the result JSON file"""
    import json
    import os
    
    if not os.path.exists(result_file_path):
        return None
    
    try:
        with open(result_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analyses = data.get("analyses", {})
        
        return {
            "regulatory_approval": analyses.get("benefit_factor", {}),
            "market_experience": analyses.get("market_experience", {}),
            "pubmed_evidence": analyses.get("pubmed_evidence", {}),
            "contraindication": analyses.get("contraindication", {}),
            "therapeutic_duplication": analyses.get("therapeutic_duplication", {}),
            "adrs_analysis": analyses.get("adrs", {}),
            "summary": analyses.get("summary", {}),
            "brr_calculation": data.get("benefit_risk_ratio", {})
        }
    except Exception as e:
        print(f"Error extracting analysis details: {e}")
        return None


def format_drug_result(result: Dict, detailed_analysis: Optional[Dict] = None) -> Dict:
    """
    Format primary medication with FULL analysis details
    
    Args:
        result: Basic result from worker
        detailed_analysis: Full analysis details from JSON file
        
    Returns:
        Comprehensive medication analysis
    """
    if not result.get("success"):
        return {
            "medication_name": result.get("drug", "Unknown"),
            "indication": result.get("diagnosis", "Unknown"),
            "status": "❌ Analysis Failed",
            "message": "Unable to complete safety analysis",
            "requires_manual_review": True
        }
    
    brr = result.get("brr")
    has_contraindication = result.get("has_contraindication", False)
    brr_interpretation = interpret_brr(brr, has_contraindication)
    evidence = format_evidence_level(result.get("rct_count", 0))
    
    # Build clinical decision
    if has_contraindication:
        clinical_decision = {
            "decision": "⛔ NOT RECOMMENDED",
            "reason": "Contraindication detected for this patient",
            "action_required": "URGENT: Review and consider alternatives",
            "severity": "Critical"
        }
    else:
        if brr_interpretation["alert_level"] == "critical":
            clinical_decision = {
                "decision": "❌ NOT RECOMMENDED",
                "reason": "Risks outweigh benefits",
                "action_required": "Consider alternative medications",
                "severity": "High"
            }
        elif brr_interpretation["alert_level"] == "caution":
            clinical_decision = {
                "decision": "⚠️ USE WITH CAUTION",
                "reason": "Requires close monitoring",
                "action_required": "Monitor patient closely; watch for adverse effects",
                "severity": "Moderate"
            }
        else:
            clinical_decision = {
                "decision": "✅ APPROPRIATE",
                "reason": "Safe for use",
                "action_required": "Standard monitoring as per protocol",
                "severity": "Low"
            }
    
    # Base response structure
    formatted_result = {
        "medication_name": result.get("drug"),
        "indication": result.get("diagnosis"),
        "clinical_decision": clinical_decision,
        "safety_profile": {
            "outcome": brr_interpretation["outcome"],
            "status_emoji": brr_interpretation["emoji"],
            "overall_assessment": brr_interpretation["status"],
            "clinical_guidance": brr_interpretation["clinical_action"],
            "recommendation": brr_interpretation["recommendation"],
            "contraindication_detected": has_contraindication,
            "alert_level": brr_interpretation["alert_level"]
        },
        "benefit_risk_score": {
            "ratio_value": f"{brr:.2f}" if isinstance(brr, (int, float)) else str(brr),
            "benefit_points": result.get("total_benefit_score", 0),
            "risk_points": result.get("total_risk_score", 0),
            "interpretation": brr_interpretation["recommendation"]
        },
        "evidence_quality": {
            "strength": evidence["level"],
            "description": evidence["description"],
            "confidence": evidence["confidence"],
            "icon": evidence["icon"],
            "trial_count": result.get("rct_count", 0)
        }
    }
    
    # Add detailed analysis if available
    if detailed_analysis:
        # 1. Regulatory Approval Details
        reg_data = detailed_analysis.get("regulatory_approval", {})
        formatted_result["regulatory_approval"] = {
            "cdsco_approved": reg_data.get("cdsco_approved", False),
            "usfda_approved": reg_data.get("usfda_approved", False),
            "benefit_type": reg_data.get("benefit_sub_factor", "Unknown"),
            "approval_description": reg_data.get("description", ""),
            "score": {
                "weight": reg_data.get("weight", 0),
                "score": reg_data.get("score", 0),
                "weighted_score": reg_data.get("weighted_score", 0)
            }
        }
        
        # 2. Market Experience Details
        mme_data = detailed_analysis.get("market_experience", {})
        formatted_result["market_experience"] = {
            "years_in_market": mme_data.get("years_in_market", 0),
            "approval_date": mme_data.get("approval_date", "Unknown"),
            "generic_name": mme_data.get("generic_name", result.get("drug")),
            "experience_level": mme_data.get("experience_sub_factor", "Unknown"),
            "description": mme_data.get("description", ""),
            "score": {
                "weight": mme_data.get("weight", 0),
                "score": mme_data.get("score", 0),
                "weighted_score": mme_data.get("weighted_score", 0)
            }
        }
        
        # 3. PubMed Evidence Details
        pubmed_data = detailed_analysis.get("pubmed_evidence", {})
        formatted_result["pubmed_evidence"] = {
            "rct_count": pubmed_data.get("rct_count", 0),
            "evidence_level": pubmed_data.get("evidence_sub_factor", "Unknown"),
            "top_studies": pubmed_data.get("conclusions", []),
            "output_summary": pubmed_data.get("output", ""),
            "score": {
                "weight": pubmed_data.get("weight", 0),
                "score": pubmed_data.get("score", 0),
                "weighted_score": pubmed_data.get("weighted_score", 0)
            }
        }
        
        # 4. Contraindication Details
        contra_data = detailed_analysis.get("contraindication", {})
        formatted_result["contraindication_analysis"] = {
            "status": contra_data.get("status", "safe"),
            "contraindication_found": contra_data.get("found", False),
            "risk_identified": contra_data.get("risk", "None"),
            "reason": contra_data.get("reason", "No contraindications detected"),
            "clinical_explanation": contra_data.get("clinical_explanation", ""),
            "matched_conditions": contra_data.get("matched_conditions", []),
            "score": {
                "weight": contra_data.get("contra_score", {}).get("weight", 0),
                "score": contra_data.get("contra_score", {}).get("score", 0),
                "weighted_score": contra_data.get("contra_score", {}).get("weighted_score", 0)
            }
        }
        
        # 5. Therapeutic Duplication Details
        dup_data = detailed_analysis.get("therapeutic_duplication", {})
        formatted_result["therapeutic_duplication"] = {
            "status": dup_data.get("status", "not_applicable"),
            "category": dup_data.get("duplication_category", "N/A"),
            "overlaps_found": dup_data.get("overlaps_found", 0),
            "redundant_found": dup_data.get("redundant_found", 0),
            "description": dup_data.get("description", ""),
            "score": {
                "weight": dup_data.get("weight", 0),
                "score": dup_data.get("score", 0),
                "weighted_score": dup_data.get("weighted_score", 0)
            } if dup_data.get("weight") else None
        }
        
        # 6. ADRs Analysis Details
        adrs_data = detailed_analysis.get("adrs_analysis", {})
        if adrs_data:
            formatted_result["adverse_drug_reactions"] = {
                "life_threatening_adrs": adrs_data.get("life_threatening_adrs", []),
                "serious_adrs": adrs_data.get("serious_adrs", []),
                "drug_interactions": adrs_data.get("drug_interactions", []),
                "has_life_threatening": len(adrs_data.get("life_threatening_adrs", [])) > 0,
                "has_serious": len(adrs_data.get("serious_adrs", [])) > 0,
                "has_interactions": len(adrs_data.get("drug_interactions", [])) > 0
            }
    
    return formatted_result


def format_alternative_result(alt_result: Dict, detailed_analysis: Optional[Dict] = None) -> Dict:
    """Format alternative medication with full details"""
    if not alt_result.get("success"):
        return {
            "medication_name": alt_result.get("drug", "Unknown"),
            "status": "Analysis incomplete",
            "available": False
        }
    
    alt_info = alt_result.get("alternative_info", {})
    brr = alt_result.get("brr")
    has_contraindication = alt_result.get("has_contraindication", False)
    brr_interpretation = interpret_brr(brr, has_contraindication)
    evidence = format_evidence_level(alt_result.get("rct_count", 0))
    
    # Determine if better option
    if has_contraindication:
        comparison = "⚠️ Also contraindicated"
        is_better = False
    else:
        if brr_interpretation["alert_level"] == "none":
            comparison = "✅ Safer alternative"
            is_better = True
        elif brr_interpretation["alert_level"] == "caution":
            comparison = "⚠️ Requires monitoring"
            is_better = True
        else:
            comparison = "❌ Similar concerns"
            is_better = False
    
    formatted_alt = {
        "medication_name": alt_result.get("drug"),
        "brand_name": alt_info.get("brand_name"),
        "rank": alt_info.get("alternative_rank"),
        "comparison_to_original": comparison,
        "is_better_option": is_better,
        "safety_profile": {
            "outcome": brr_interpretation["outcome"],
            "status_emoji": brr_interpretation["emoji"],
            "assessment": brr_interpretation["status"],
            "guidance": brr_interpretation["clinical_action"],
            "contraindication_detected": has_contraindication
        },
        "benefit_risk_score": {
            "ratio_value": f"{brr:.2f}" if isinstance(brr, (int, float)) else str(brr),
            "benefit_points": alt_result.get("total_benefit_score", 0),
            "risk_points": alt_result.get("total_risk_score", 0)
        },
        "evidence_quality": {
            "strength": evidence["level"],
            "confidence": evidence["confidence"],
            "trial_count": alt_result.get("rct_count", 0)
        },
        "administration": {
            "route": alt_info.get("route", "Unknown"),
            "manufacturer": alt_info.get("manufacturer", "Unknown")
        }
    }
    
    # Add detailed analysis if available
    if detailed_analysis:
        # Add same detailed sections as primary drug
        formatted_alt.update({
            "regulatory_approval": detailed_analysis.get("regulatory_approval", {}),
            "market_experience": detailed_analysis.get("market_experience", {}),
            "pubmed_evidence": detailed_analysis.get("pubmed_evidence", {}),
            "contraindication_analysis": detailed_analysis.get("contraindication", {})
        })
    
    return formatted_alt


def format_complete_response(results: List[Dict], rmm_table: List = None, consequences_data: Dict = None) -> Dict:
    """
    Format complete analysis response with ALL details
    
    Args:
        results: List of analysis results from workers
        rmm_table: Aggregated RRM table
        consequences_data: Consequences of non-treatment data
        
    Returns:
        Comprehensive clinical response with all analysis details
    """
    medications_analysis = []
    critical_alerts = []
    warnings = []
    safe_medications = []
    
    for result in results:
        if not result.get("success"):
            medications_analysis.append({
                "medication": format_drug_result(result),
                "alternatives_available": False,
                "alternatives": []
            })
            continue
        
        # Extract full analysis details from result file
        output_file = result.get("output_file")
        detailed_analysis = extract_full_analysis_details(output_file) if output_file else None
        
        # Format primary medication with full details
        primary = format_drug_result(result, detailed_analysis)
        
        # Track alerts
        alert_level = primary["safety_profile"]["alert_level"]
        has_contraindication = primary["safety_profile"]["contraindication_detected"]
        
        if has_contraindication or alert_level == "critical":
            critical_alerts.append({
                "medication": result.get("drug"),
                "indication": result.get("diagnosis"),
                "issue": "Contraindication detected" if has_contraindication else "Unfavorable benefit-risk ratio"
            })
        elif alert_level == "caution":
            warnings.append({
                "medication": result.get("drug"),
                "indication": result.get("diagnosis"),
                "issue": "Requires strict monitoring"
            })
        else:
            safe_medications.append(result.get("drug"))
        
        # Format alternatives with full details
        alternatives = []
        alt_analyses = result.get("alternative_analyses", [])
        for alt in alt_analyses:
            alt_output_file = alt.get("output_file")
            alt_detailed = extract_full_analysis_details(alt_output_file) if alt_output_file else None
            alternatives.append(format_alternative_result(alt, alt_detailed))
        
        # Sort alternatives by safety
        alternatives.sort(key=lambda x: (
            not x.get("is_better_option", False),
            x.get("benefit_risk_score", {}).get("ratio_value", "0")
        ), reverse=True)
        
        medications_analysis.append({
            "medication": primary,
            "alternatives_available": len(alternatives) > 0,
            "alternatives_count": len(alternatives),
            "alternatives": alternatives if alternatives else []
        })
    
    # Calculate summary statistics
    successful = [r for r in results if r.get("success")]
    total_meds = len(results)
    
    # Build final response
    return {
        "clinical_summary": {
            "total_medications_reviewed": total_meds,
            "successful_analyses": len(successful),
            "failed_analyses": total_meds - len(successful),
            "critical_alerts_count": len(critical_alerts),
            "warnings_count": len(warnings),
            "safe_medications_count": len(safe_medications),
            "alternatives_provided_count": sum(1 for r in successful if r.get("alternatives_count", 0) > 0),
            "overall_status": (
                "🔴 URGENT REVIEW REQUIRED" if critical_alerts else
                "🟡 CAUTION ADVISED" if warnings else
                "🟢 ALL MEDICATIONS APPROPRIATE"
            )
        },
        "alerts": {
            "critical": critical_alerts if critical_alerts else None,
            "warnings": warnings if warnings else None,
            "safe_medications": safe_medications if safe_medications else None
        },
        "medication_analysis": medications_analysis,
        "action_items": generate_action_items(critical_alerts, warnings),
        "risk_mitigation_measures": rmm_table if rmm_table else [],
        "consequences_of_non_treatment": consequences_data if consequences_data else {}
    }


def generate_action_items(critical_alerts: List, warnings: List) -> List[str]:
    """Generate actionable recommendations for clinicians"""
    actions = []
    
    if critical_alerts:
        actions.append("🔴 IMMEDIATE ACTION: Review medications with critical alerts")
        for alert in critical_alerts:
            actions.append(f"   • {alert['medication']} for {alert['indication']}: {alert['issue']}")
        actions.append("   → Consider alternatives or discontinue use")
    
    if warnings:
        actions.append("🟡 MONITORING REQUIRED: Following medications need close supervision")
        for warning in warnings:
            actions.append(f"   • {warning['medication']} for {warning['indication']}")
        actions.append("   → Implement strict monitoring protocol")
    
    if not critical_alerts and not warnings:
        actions.append("🟢 NO IMMEDIATE ACTION: All medications within acceptable safety parameters")
        actions.append("   → Continue standard monitoring as per protocol")
    
    return actions