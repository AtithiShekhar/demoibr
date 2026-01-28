# ================================
# utils/response_formatter.py
# ================================

"""
Response Formatter - Clinical Decision Support Format
Designed for healthcare professionals and non-technical staff
"""

from typing import Dict, List, Any


def interpret_brr(brr: Any, has_contraindication: bool = False) -> Dict[str, Any]:
    """
    Interpret BRR value according to clinical thresholds
    
    BRR Thresholds:
    - >6: ✅ Favorable (Benefits outweigh risks; monitor as standard)
    - 2-6: ⚠️ Conditional (Benefits outweigh risks only with strict monitoring)
    - <2: ❌ Unfavorable (Risks outweigh benefits for this patient)
    """
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
    """Format clinical evidence in user-friendly terms"""
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


def format_drug_result(result: Dict) -> Dict:
    """
    Format primary medication analysis for UI display
    
    Args:
        result: Full analysis result from worker
        
    Returns:
        User-friendly, clinically relevant result
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
    
    # Build clinical recommendation
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
    
    return {
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


def format_alternative_result(alt_result: Dict) -> Dict:
    """
    Format alternative medication for UI display
    
    Args:
        alt_result: Full alternative analysis result
        
    Returns:
        User-friendly alternative medication info
    """
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
    
    # Determine if this is a better option
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
    
    return {
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


def format_complete_response(results: List[Dict]) -> Dict:
    """
    Format complete analysis response - CLINICAL DECISION SUPPORT FORMAT
    
    Args:
        results: List of analysis results from workers
        
    Returns:
        User-friendly, actionable clinical response
    """
    medications_analysis = []
    
    # Categorize medications by alert level
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
        
        # Format primary medication
        primary = format_drug_result(result)
        
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
        
        # Format alternatives
        alternatives = []
        alt_analyses = result.get("alternative_analyses", [])
        for alt in alt_analyses:
            alternatives.append(format_alternative_result(alt))
        
        # Sort alternatives by safety (best first)
        alternatives.sort(key=lambda x: (
            not x.get("is_better_option", False),
            x.get("benefit_risk_score", {}).get("ratio_value", "0")
        ))
        
        medications_analysis.append({
            "medication": primary,
            "alternatives_available": len(alternatives) > 0,
            "alternatives": alternatives if alternatives else []
        })
    
    # Calculate summary statistics
    successful = [r for r in results if r.get("success")]
    total_meds = len(results)
    
    # Clinical Summary
    return {
        "clinical_summary": {
            "total_medications_reviewed": total_meds,
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
        "action_items": generate_action_items(critical_alerts, warnings)
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