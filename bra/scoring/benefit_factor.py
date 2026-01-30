
# ================================
# scoring/benefit_factor.py
# ================================

from typing import Dict,Any
from scoring.config import ScoringConfig


def get_benefit_factor_data(cdsco_approved: bool, usfda_approved: bool, scoring_system=None) -> Dict:
    """Calculate benefit factor score"""
    result = ScoringConfig.calculate_benefit_factor_score(cdsco_approved, usfda_approved)
    
    if scoring_system:
        scoring_system.add_analysis("benefit_factor", result)
    
    return result


def get_market_experience_data(years_in_market: int, scoring_system=None) -> Dict:
    """Calculate market experience score"""
    result = ScoringConfig.calculate_market_experience_score(years_in_market)
    
    if scoring_system:
        scoring_system.add_analysis("market_experience", result)
    
    return result


def get_pubmed_evidence_data(rct_count: int, scoring_system=None) -> Dict:
    """Calculate PubMed evidence score"""
    result = ScoringConfig.calculate_pubmed_evidence_score(rct_count)
    
    if scoring_system:
        scoring_system.add_analysis("pubmed_evidence", result)
    
    return result


def get_contraindication_data(status: str, scoring_system=None) -> Dict:
    """Calculate contraindication score"""
    result = ScoringConfig.calculate_contraindication_score(status)
    
    if scoring_system:
        scoring_system.add_analysis("contraindication", result)
    
    return result
def get_lt_adr_data(lt_adrs_data: Dict[str, Any], scoring_system=None) -> Dict:
    """
    Calculate and record Life-Threatening ADR score (Factor 3.2.1)
    """
    result = ScoringConfig.calculate_lt_adr_score(lt_adrs_data)
    
    if scoring_system:
        scoring_system.add_analysis("life_threatening_adrs", result)
    
    return result


def get_serious_adr_data(serious_adrs_data: Dict[str, Any], scoring_system=None) -> Dict:
    """
    Calculate and record Serious ADR score (Factor 3.2.2)
    """
    result = ScoringConfig.calculate_serious_adr_score(serious_adrs_data)
    
    if scoring_system:
        scoring_system.add_analysis("serious_adrs", result)
    
    return result


def get_drug_interaction_data(interactions_data: Dict[str, Any], scoring_system=None) -> Dict:
    """
    Calculate and record Drug Interaction score (Factor 3.3)
    """
    result = ScoringConfig.calculate_drug_interaction_score(interactions_data)
    
    if scoring_system:
        scoring_system.add_analysis("drug_interactions", result)
    
    return result


def get_consequences_data(consequences_data: Dict[str, Any], scoring_system=None) -> Dict:
    """
    Calculate and record Medical Need Severity score (Factor 2.6)
    Benefit side of the BRR equation
    """
    # Note: Extract the inner results dictionary if passing the full Gemini output
    raw_consequences = consequences_data.get('factor_2_6_consequences_of_non_treatment', consequences_data)
    result = ScoringConfig.calculate_consequences_score(raw_consequences)
    
    if scoring_system:
        scoring_system.add_analysis("medical_need_severity", result)
    
    return result


def get_mitigation_feasibility_data(rmf_data: Dict[str, Any], scoring_system=None) -> Dict:
    """
    Calculate and record Risk Mitigation Feasibility score (Factor 3.4)
    Evaluates Reversibility vs Preventability
    """
    result = ScoringConfig.calculate_mitigation_feasibility_score(rmf_data)
    
    if scoring_system:
        scoring_system.add_analysis("risk_mitigation_feasibility", result)
    
    return result


def get_therapeutic_duplication_data(overlaps: int, redundant: int, scoring_system=None) -> Dict:
    """
    Calculate and record Therapeutic Duplication score
    """
    result = ScoringConfig.calculate_duplication_score(overlaps, redundant)
    
    if scoring_system:
        scoring_system.add_analysis("therapeutic_duplication", result)
    
    return result