"""
scoring/scoring_system.py
Generalized Scoring System for Drug Indication Analysis
"""

import json
from typing import Dict, Any
from datetime import datetime


class ScoringSystem:
    """Generalized scoring system for all analysis components"""
    
    def __init__(self, output_file: str = "result.json"):
        self.output_file = output_file
        self.results = {}
    
    def add_analysis(self, analysis_name: str, data: Dict[str, Any]):
        """
        Add analysis results to the scoring system
        
        Args:
            analysis_name: Name of the analysis (e.g., "benefit_factor", "market_experience")
            data: Dictionary containing the analysis data
        """
        self.results[analysis_name] = data
    
    def save_to_json(self):
        """Save all results to JSON file"""
        output_data = {
            "analysis_timestamp": datetime.now().isoformat(),
            "analyses": self.results
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        return self.output_file


class BenefitFactorScorer:
    """Calculate benefit factor scores based on regulatory approval"""
    
    WEIGHTS = {
        'both_approved': 90,
        'single_approved': 50,
        'off_label': 10
    }
    
    SCORES = {
        'both_approved': 4,
        'cdsco_only': 3,
        'usfda_only': 3,
        'off_label': 1
    }
    
    def calculate_score(self, cdsco_approved: bool, usfda_approved: bool) -> Dict:
        """Calculate benefit factor weight and score"""
        if cdsco_approved and usfda_approved:
            benefit_type = "Approved Use"
            weight = self.WEIGHTS['both_approved']
            score = self.SCORES['both_approved']
        elif cdsco_approved:
            benefit_type = "Approved Use (CDSCO only)"
            weight = self.WEIGHTS['single_approved']
            score = self.SCORES['cdsco_only']
        elif usfda_approved:
            benefit_type = "Approved Use (USFDA only)"
            weight = self.WEIGHTS['single_approved']
            score = self.SCORES['usfda_only']
        else:
            benefit_type = "Off label"
            weight = self.WEIGHTS['off_label']
            score = self.SCORES['off_label']
        
        weighted_score = weight * score
        
        return {
            'benefit_sub_factor': benefit_type,
            'weight': weight,
            'score': score,
            'weighted_score': weighted_score,
            'cdsco_approved': cdsco_approved,
            'usfda_approved': usfda_approved
        }
    
    def format_output_table(self, result: Dict) -> str:
        """Format output as a table"""
        benefit_type = result['benefit_sub_factor']
        weight = result['weight']
        score = result['score']
        weighted_score = result['weighted_score']
        
        display_type = "Approved Use" if "Approved Use" in benefit_type else "Off label"
        
        output = []
        output.append("Benefit Sub-Factor\tWeight (10–100)\tScore (1–5)\tWeighted Score")
        output.append(f"{display_type}\t\t{weight}\t\t{score}\t\t{weighted_score}")
        
        return "\n".join(output)


class MarketExperienceScorer:
    """Calculate market experience scores based on approval years"""
    
    # Weight: 90 for established, 60 for new
    WEIGHTS = {
        'established': 90,  # >5 years
        'new': 60          # <5 years
    }
    
    # Score: 5 for established, 4 for new (out of 10 scale)
    SCORES = {
        'established': 5,
        'new': 4
    }
    
    def calculate_score(self, years_in_market: int) -> Dict:
        """
        Calculate market experience score based on years
        
        Args:
            years_in_market: Number of years drug has been in market
            
        Returns:
            Dictionary with experience type, weight, score, and weighted_score
        """
        if years_in_market >= 5:
            experience_type = "Established indication (>5Y, approved widely)"
            weight = self.WEIGHTS['established']
            score = self.SCORES['established']
        else:
            experience_type = "New indication (<5Y, limited approval)"
            weight = self.WEIGHTS['new']
            score = self.SCORES['new']
        
        weighted_score = weight * score
        
        return {
            'experience_sub_factor': experience_type,
            'weight': weight,
            'score': score,
            'weighted_score': weighted_score,
            'years_in_market': years_in_market
        }
    
    def format_output_table(self, result: Dict) -> str:
        """Format output as a table"""
        experience_type = result['experience_sub_factor']
        weight = result['weight']
        score = result['score']
        weighted_score = result['weighted_score']
        
        output = []
        output.append("Benefit Factor\t\t\t\t\tWeight (10–100)\tScore (1–10)\tWeighted Score")
        output.append(f"{experience_type}\t{weight}\t\t{score}\t\t{weighted_score}")
        
        return "\n".join(output)


class PubMedEvidenceScorer:
    """Calculate PubMed evidence scores based on RCT count"""
    
    # Weight: 100 for high evidence, 30 for low
    WEIGHTS = {
        'high_evidence': 100,  # Multiple RCTs
        'low_evidence': 30     # Limited data
    }
    
    # Score: 5 for high evidence, 1 for low
    SCORES = {
        'high_evidence': 5,
        'low_evidence': 1
    }
    
    # Thresholds for categorization
    HIGH_EVIDENCE_THRESHOLD = 100  # 10+ RCTs = high evidence
    
    def calculate_score(self, rct_count: int) -> Dict:
        """
        Calculate PubMed evidence score based on RCT count
        
        Args:
            rct_count: Number of RCTs found
            
        Returns:
            Dictionary with evidence type, weight, score, and weighted_score
        """
        if rct_count >= self.HIGH_EVIDENCE_THRESHOLD:
            evidence_type = "High evidence (multiple RCTs, broad authorization)"
            weight = self.WEIGHTS['high_evidence']
            score = self.SCORES['high_evidence']
        else:
            evidence_type = "Low evidence (limited data, uncertain)"
            weight = self.WEIGHTS['low_evidence']
            score = self.SCORES['low_evidence']
        
        weighted_score = weight * score
        
        return {
            'evidence_sub_factor': evidence_type,
            'weight': weight,
            'score': score,
            'weighted_score': weighted_score,
            'rct_count': rct_count
        }
    
    def format_output_table(self, result: Dict) -> str:
        """Format output as a table"""
        evidence_type = result['evidence_sub_factor']
        weight = result['weight']
        score = result['score']
        weighted_score = result['weighted_score']
        
        output = []
        output.append("Evidence Factor\t\t\t\t\tWeight (10–100)\tScore (1–5)\tWeighted Score")
        output.append(f"{evidence_type}\t{weight}\t\t{score}\t\t{weighted_score}")
        
        return "\n".join(output)


# ============================================================
# MAIN FUNCTIONS FOR USAGE
# ============================================================

def get_benefit_factor_data(cdsco_approved: bool, usfda_approved: bool, 
                           scoring_system: ScoringSystem = None) -> Dict:
    """
    Calculate benefit factor score
    
    Args:
        cdsco_approved: Whether approved by CDSCO
        usfda_approved: Whether approved by USFDA
        scoring_system: Optional ScoringSystem instance to add results to
    
    Returns:
        Dictionary with weight, score, and weighted_score
    """
    scorer = BenefitFactorScorer()
    result = scorer.calculate_score(cdsco_approved, usfda_approved)
    
    # Add to scoring system if provided
    if scoring_system:
        scoring_system.add_analysis("benefit_factor", result)
    
    return result


def get_market_experience_data(years_in_market: int, 
                               scoring_system: ScoringSystem = None) -> Dict:
    """
    Calculate market experience score
    
    Args:
        years_in_market: Number of years drug has been in market
        scoring_system: Optional ScoringSystem instance to add results to
    
    Returns:
        Dictionary with weight, score, and weighted_score
    """
    scorer = MarketExperienceScorer()
    result = scorer.calculate_score(years_in_market)
    
    # Add to scoring system if provided
    if scoring_system:
        scoring_system.add_analysis("market_experience", result)
    
    return result


def get_pubmed_evidence_data(rct_count: int,
                             scoring_system: ScoringSystem = None) -> Dict:
    """
    Calculate PubMed evidence score
    
    Args:
        rct_count: Number of RCTs found
        scoring_system: Optional ScoringSystem instance to add results to
    
    Returns:
        Dictionary with weight, score, and weighted_score
    """
    scorer = PubMedEvidenceScorer()
    result = scorer.calculate_score(rct_count)
    
    # Add to scoring system if provided
    if scoring_system:
        scoring_system.add_analysis("pubmed_evidence", result)
    
    return result


def format_benefit_score(cdsco_approved: bool, usfda_approved: bool) -> str:
    """Format benefit factor score as table"""
    scorer = BenefitFactorScorer()
    result = scorer.calculate_score(cdsco_approved, usfda_approved)
    return scorer.format_output_table(result)


def format_pubmed_evidence_score(rct_count: int) -> str:
    """Format PubMed evidence score as table"""
    scorer = PubMedEvidenceScorer()
    result = scorer.calculate_score(rct_count)
    return scorer.format_output_table(result)

