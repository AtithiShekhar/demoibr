
# ================================
# scoring/benefit_factor.py
# ================================

from typing import Dict
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
