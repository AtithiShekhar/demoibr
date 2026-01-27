# ================================
# scoring/config.py
# ================================

"""
Centralized Scoring Configuration
All scoring matrices and rules in one place
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ScoreEntry:
    """Individual score entry with weight and score"""
    description: str
    weight: int
    score: int
    
    @property
    def weighted_score(self) -> int:
        return self.weight * self.score


class ScoringConfig:
    """Centralized scoring configuration for all analysis components"""
    
    # ========================================
    # BENEFIT SCORING MATRIX
    # ========================================
    
    INDICATION_STRENGTH = {
        'established': ScoreEntry(
            description="Established indication (>5Y, approved widely)",
            weight=90,
            score=5
        ),
        'new': ScoreEntry(
            description="New indication (<5Y, limited approval)",
            weight=60,
            score=4
        ),
        'non_first_line': ScoreEntry(
            description="Non-first line treatment",
            weight=40,
            score=3
        ),
        'prophylaxis': ScoreEntry(
            description="Prophylaxis",
            weight=30,
            score=2
        ),
        'off_label': ScoreEntry(
            description="Off label",
            weight=10,
            score=1
        )
    }
    
    EVIDENCE_STRENGTH = {
        'high': ScoreEntry(
            description="High evidence (multiple RCTs, broad authorization)",
            weight=100,
            score=5
        ),
        'low': ScoreEntry(
            description="Low evidence (limited data, uncertain)",
            weight=30,
            score=1
        )
    }
    
    THERAPEUTIC_DUPLICATION = {
        'unique': ScoreEntry(
            description="Unique role, no overlap",
            weight=90,
            score=5
        ),
        'some_overlap': ScoreEntry(
            description="Some overlap but with rationale",
            weight=60,
            score=3
        ),
        'redundant': ScoreEntry(
            description="Redundant/duplicate prescription",
            weight=10,
            score=1
        )
    }
    
    ALTERNATIVES = {
        'no_alternative': ScoreEntry(
            description="No alternative existed",
            weight=100,
            score=5
        ),
        'same_efficacy': ScoreEntry(
            description="Alternative with same efficacy/safety",
            weight=50,
            score=3
        ),
        'safer_available': ScoreEntry(
            description="Safer alternatives available",
            weight=20,
            score=1
        )
    }
    
    MEDICAL_NEED_SEVERITY = {
        'acute_life_threatening': ScoreEntry(
            description="Acute, life-threatening condition",
            weight=100,
            score=5
        ),
        'acute_non_life_threatening': ScoreEntry(
            description="Acute, non-life-threatening",
            weight=60,
            score=4
        ),
        'chronic_life_threatening': ScoreEntry(
            description="Chronic, life-threatening",
            weight=90,
            score=4
        ),
        'chronic_non_life_threatening': ScoreEntry(
            description="Chronic, non-life-threatening",
            weight=50,
            score=3
        )
    }
    
    QUALITY_OF_LIFE = {
        'improvement': ScoreEntry(
            description="Quality of life improvement",
            weight=40,
            score=3
        )
    }
    
    # ========================================
    # RISK SCORING MATRIX
    # ========================================
    
    CONTRAINDICATION = {
        'absolute': ScoreEntry(
            description="Absolute contraindication/completely restricted",
            weight=100,
            score=5
        ),
        'boxed_warning': ScoreEntry(
            description="Boxed warning present",
            weight=100,
            score=5
        ),
        'pregnancy_warning': ScoreEntry(
            description="Pregnancy warning/contraindication",
            weight=100,
            score=5
        ),
        'warning': ScoreEntry(
            description="No absolute contraindication, but with warning/precaution",
            weight=10,
            score=1
        ),
        'safe': ScoreEntry(
            description="Safe - no contraindication",
            weight=0,
            score=0
        ),
        'no_data': ScoreEntry(
            description="No FDA data available",
            weight=0,
            score=0
        )
    }
    
    LT_ADRS = {
        'with_risk_factors': ScoreEntry(
            description="Life-threatening ADRs + risk factors",
            weight=90,
            score=5
        ),
        'no_risk_factors': ScoreEntry(
            description="Life-threatening ADRs, no risk factors",
            weight=70,
            score=3
        ),
        'none': ScoreEntry(
            description="No life-threatening ADRs",
            weight=10,
            score=1
        )
    }
    
    SERIOUS_ADRS = {
        'with_risk_factors': ScoreEntry(
            description="Serious ADRs + risk factors/interactions",
            weight=80,
            score=4
        ),
        'no_risk_factors': ScoreEntry(
            description="Serious ADRs, no risk factors/no interactions",
            weight=60,
            score=2
        ),
        'none': ScoreEntry(
            description="No serious ADRs / no interactions",
            weight=20,
            score=1
        )
    }
    
    DRUG_INTERACTIONS = {
        'present': ScoreEntry(
            description="Drug interactions present",
            weight=70,
            score=4
        ),
        'none': ScoreEntry(
            description="No drug interactions",
            weight=0,
            score=0
        )
    }
    
    RISK_MITIGATION = {
        'easily_manageable': ScoreEntry(
            description="ADRs easily manageable/reversible",
            weight=30,
            score=1
        ),
        'strict_measures': ScoreEntry(
            description="Strict preventive measures needed",
            weight=60,
            score=3
        ),
        'no_mitigation': ScoreEntry(
            description="No feasible mitigation measures",
            weight=100,
            score=5
        )
    }
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    @classmethod
    def get_score_entry(cls, category: str, key: str) -> Dict[str, Any]:
        """
        Get score entry for any category and key
        
        Args:
            category: Category name (e.g., 'EVIDENCE_STRENGTH')
            key: Key within category (e.g., 'high')
            
        Returns:
            Dictionary with score details
        """
        matrix = getattr(cls, category, None)
        if not matrix or key not in matrix:
            raise ValueError(f"Invalid category '{category}' or key '{key}'")
        
        entry = matrix[key]
        return {
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score
        }
    
    @classmethod
    def calculate_market_experience_score(cls, years_in_market: int) -> Dict[str, Any]:
        """
        Calculate market experience score based on years
        Maps to INDICATION_STRENGTH matrix
        """
        if years_in_market >= 5:
            entry = cls.INDICATION_STRENGTH['established']
        else:
            entry = cls.INDICATION_STRENGTH['new']
        
        return {
            'experience_sub_factor': entry.description,
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'years_in_market': years_in_market
        }
    
    @classmethod
    def calculate_pubmed_evidence_score(cls, rct_count: int) -> Dict[str, Any]:
        """
        Calculate PubMed evidence score based on RCT count
        Maps to EVIDENCE_STRENGTH matrix
        """
        # Threshold for high evidence
        if rct_count >= 100:
            entry = cls.EVIDENCE_STRENGTH['high']
        else:
            entry = cls.EVIDENCE_STRENGTH['low']
        
        return {
            'evidence_sub_factor': entry.description,
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'rct_count': rct_count
        }
    
    @classmethod
    def calculate_benefit_factor_score(cls, cdsco_approved: bool, usfda_approved: bool) -> Dict[str, Any]:
        """
        Calculate benefit factor score based on regulatory approval
        Maps to INDICATION_STRENGTH matrix
        """
        if cdsco_approved and usfda_approved:
            entry = cls.INDICATION_STRENGTH['established']
            benefit_type = "Approved Use"
        elif cdsco_approved:
            entry = cls.INDICATION_STRENGTH['new']
            benefit_type = "Approved Use (CDSCO only)"
        elif usfda_approved:
            entry = cls.INDICATION_STRENGTH['new']
            benefit_type = "Approved Use (USFDA only)"
        else:
            entry = cls.INDICATION_STRENGTH['off_label']
            benefit_type = "Off label"
        
        return {
            'benefit_sub_factor': benefit_type,
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'cdsco_approved': cdsco_approved,
            'usfda_approved': usfda_approved
        }
    
    @classmethod
    def calculate_contraindication_score(cls, status: str) -> Dict[str, Any]:
        """
        Calculate contraindication score based on status
        
        Args:
            status: One of 'absolute', 'boxed_warning', 'pregnancy_warning', 'warning', 'safe', 'no_data'
        """
        if status not in cls.CONTRAINDICATION:
            status = 'safe'  # Default to safe if unknown
        
        entry = cls.CONTRAINDICATION[status]
        return {
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'status': status
        }
    
    @classmethod
    def calculate_duplication_score(cls, overlaps: int, redundant: int) -> Dict[str, Any]:
        """
        Calculate therapeutic duplication score
        
        Args:
            overlaps: Number of overlapping medications
            redundant: Number of redundant medications
        """
        if redundant > 0:
            entry = cls.THERAPEUTIC_DUPLICATION['redundant']
            category = "High Risk - Redundant Medications"
        elif overlaps > 0:
            entry = cls.THERAPEUTIC_DUPLICATION['some_overlap']
            category = "Moderate Risk - Some Overlap"
        else:
            entry = cls.THERAPEUTIC_DUPLICATION['unique']
            category = "No Risk - Unique Medications"
        
        return {
            'duplication_category': category,
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'overlaps_found': overlaps,
            'redundant_found': redundant
        }
