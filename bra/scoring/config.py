# ================================
# scoring/config.py
# ================================

"""
Centralized Scoring Configuration
All scoring matrices and rules in one place
"""

from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum


class ScoreType(Enum):
    """Enum to identify if a score is benefit or risk"""
    BENEFIT = "benefit"
    RISK = "risk"


@dataclass
class ScoreEntry:
    """Individual score entry with weight and score"""
    description: str
    weight: int
    score: int
    score_type: ScoreType  # NEW: Identify if this is benefit or risk
    
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
            score=5,
            score_type=ScoreType.BENEFIT
        ),
        'new': ScoreEntry(
            description="New indication (<5Y, limited approval)",
            weight=60,
            score=4,
            score_type=ScoreType.BENEFIT
        ),
        'non_first_line': ScoreEntry(
            description="Non-first line treatment",
            weight=40,
            score=3,
            score_type=ScoreType.BENEFIT
        ),
        'prophylaxis': ScoreEntry(
            description="Prophylaxis",
            weight=30,
            score=2,
            score_type=ScoreType.BENEFIT
        ),
        'off_label': ScoreEntry(
            description="Off label",
            weight=10,
            score=1,
            score_type=ScoreType.BENEFIT
        )
    }
    
    EVIDENCE_STRENGTH = {
        'high': ScoreEntry(
            description="High evidence (multiple RCTs, broad authorization)",
            weight=100,
            score=5,
            score_type=ScoreType.BENEFIT
        ),
        'low': ScoreEntry(
            description="Low evidence (limited data, uncertain)",
            weight=30,
            score=1,
            score_type=ScoreType.BENEFIT
        )
    }
    
    THERAPEUTIC_DUPLICATION = {
        'unique': ScoreEntry(
            description="Unique role, no overlap",
            weight=90,
            score=5,
            score_type=ScoreType.BENEFIT
        ),
        'some_overlap': ScoreEntry(
            description="Some overlap but with rationale",
            weight=60,
            score=3,
            score_type=ScoreType.BENEFIT
        ),
        'redundant': ScoreEntry(
            description="Redundant/duplicate prescription",
            weight=10,
            score=1,
            score_type=ScoreType.BENEFIT
        )
    }
    
    ALTERNATIVES = {
        'no_alternative': ScoreEntry(
            description="No alternative existed",
            weight=100,
            score=5,
            score_type=ScoreType.BENEFIT
        ),
        'same_efficacy': ScoreEntry(
            description="Alternative with same efficacy/safety",
            weight=50,
            score=3,
            score_type=ScoreType.BENEFIT
        ),
        'safer_available': ScoreEntry(
            description="Safer alternatives available",
            weight=20,
            score=1,
            score_type=ScoreType.BENEFIT
        )
    }
    
    MEDICAL_NEED_SEVERITY = {
        'acute_life_threatening': ScoreEntry(
            description="Acute, life-threatening condition",
            weight=100,
            score=5,
            score_type=ScoreType.BENEFIT
        ),
        'acute_non_life_threatening': ScoreEntry(
            description="Acute, non-life-threatening",
            weight=60,
            score=4,
            score_type=ScoreType.BENEFIT
        ),
        'chronic_life_threatening': ScoreEntry(
            description="Chronic, life-threatening",
            weight=90,
            score=4,
            score_type=ScoreType.BENEFIT
        ),
        'chronic_non_life_threatening': ScoreEntry(
            description="Chronic, non-life-threatening",
            weight=50,
            score=3,
            score_type=ScoreType.BENEFIT
        )
    }
    
    QUALITY_OF_LIFE = {
        'improvement': ScoreEntry(
            description="Quality of life improvement",
            weight=40,
            score=3,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # ========================================
    # RISK SCORING MATRIX
    # ========================================
    
    CONTRAINDICATION = {
        'absolute': ScoreEntry(
            description="Absolute contraindication/completely restricted",
            weight=100,
            score=5,
            score_type=ScoreType.RISK
        ),
        'boxed_warning': ScoreEntry(
            description="Boxed warning present",
            weight=100,
            score=5,
            score_type=ScoreType.RISK
        ),
        'pregnancy_warning': ScoreEntry(
            description="Pregnancy warning/contraindication",
            weight=100,
            score=5,
            score_type=ScoreType.RISK
        ),
        'warning': ScoreEntry(
            description="No absolute contraindication, but with warning/precaution",
            weight=10,
            score=1,
            score_type=ScoreType.RISK
        ),
        'safe': ScoreEntry(
            description="Safe - no contraindication",
            weight=0,
            score=0,
            score_type=ScoreType.RISK
        ),
        'no_data': ScoreEntry(
            description="No FDA data available",
            weight=0,
            score=0,
            score_type=ScoreType.RISK
        )
    }
    
    LT_ADRS = {
        'with_risk_factors': ScoreEntry(
            description="Life-threatening ADRs + risk factors",
            weight=90,
            score=5,
            score_type=ScoreType.RISK
        ),
        'no_risk_factors': ScoreEntry(
            description="Life-threatening ADRs, no risk factors",
            weight=70,
            score=3,
            score_type=ScoreType.RISK
        ),
        'none': ScoreEntry(
            description="No life-threatening ADRs",
            weight=10,
            score=1,
            score_type=ScoreType.RISK
        )
    }
    
    SERIOUS_ADRS = {
        'with_risk_factors': ScoreEntry(
            description="Serious ADRs + risk factors/interactions",
            weight=80,
            score=4,
            score_type=ScoreType.RISK
        ),
        'no_risk_factors': ScoreEntry(
            description="Serious ADRs, no risk factors/no interactions",
            weight=60,
            score=2,
            score_type=ScoreType.RISK
        ),
        'none': ScoreEntry(
            description="No serious ADRs / no interactions",
            weight=20,
            score=1,
            score_type=ScoreType.RISK
        )
    }
    
    DRUG_INTERACTIONS = {
        'present': ScoreEntry(
            description="Drug interactions present",
            weight=70,
            score=4,
            score_type=ScoreType.RISK
        ),
        'none': ScoreEntry(
            description="No drug interactions",
            weight=0,
            score=0,
            score_type=ScoreType.RISK
        )
    }
    
    RISK_MITIGATION = {
        'easily_manageable': ScoreEntry(
            description="ADRs easily manageable/reversible",
            weight=30,
            score=1,
            score_type=ScoreType.RISK
        ),
        'strict_measures': ScoreEntry(
            description="Strict preventive measures needed",
            weight=60,
            score=3,
            score_type=ScoreType.RISK
        ),
        'no_mitigation': ScoreEntry(
            description="No feasible mitigation measures",
            weight=100,
            score=5,
            score_type=ScoreType.RISK
        )
    }
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    @classmethod
    def calculate_market_experience_score(cls, years_in_market: int) -> Dict[str, Any]:
        """Calculate market experience score based on years"""
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
            'score_type': entry.score_type.value,
            'years_in_market': years_in_market
        }
    
    @classmethod
    def calculate_pubmed_evidence_score(cls, rct_count: int) -> Dict[str, Any]:
        """Calculate PubMed evidence score based on RCT count"""
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
            'score_type': entry.score_type.value,
            'rct_count': rct_count
        }
    
    @classmethod
    def calculate_benefit_factor_score(cls, cdsco_approved: bool, usfda_approved: bool) -> Dict[str, Any]:
        """Calculate benefit factor score based on regulatory approval"""
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
            'score_type': entry.score_type.value,
            'cdsco_approved': cdsco_approved,
            'usfda_approved': usfda_approved
        }
    
    @classmethod
    def calculate_contraindication_score(cls, status: str) -> Dict[str, Any]:
        """Calculate contraindication score based on status"""
        if status not in cls.CONTRAINDICATION:
            status = 'safe'
        
        entry = cls.CONTRAINDICATION[status]
        return {
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'status': status
        }
    
    @classmethod
    def calculate_duplication_score(cls, overlaps: int, redundant: int) -> Dict[str, Any]:
        """Calculate therapeutic duplication score"""
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
            'score_type': entry.score_type.value,
            'overlaps_found': overlaps,
            'redundant_found': redundant
        }
    
    @classmethod
    def calculate_brr(cls, benefit_scores: list, risk_scores: list) -> Dict[str, Any]:
        """
        Calculate Benefit-Risk Ratio (BRR)
        
        Args:
            benefit_scores: List of benefit weighted scores
            risk_scores: List of risk weighted scores
            
        Returns:
            Dictionary with BRR calculation details
        """
        total_benefit = sum(benefit_scores)
        total_risk = sum(risk_scores)
        
        # Avoid division by zero
        if total_risk == 0:
            brr = float('inf') if total_benefit > 0 else 0
            brr_interpretation = "No Risk Detected" if total_benefit > 0 else "No Benefit or Risk"
        else:
            brr = total_benefit / total_risk
            
            # Interpretation
            if brr >= 2.0:
                brr_interpretation = "Excellent - Benefits strongly outweigh risks"
            elif brr >= 1.5:
                brr_interpretation = "Good - Benefits outweigh risks"
            elif brr >= 1.0:
                brr_interpretation = "Acceptable - Benefits slightly outweigh risks"
            elif brr >= 0.5:
                brr_interpretation = "Caution - Risks approaching benefits"
            else:
                brr_interpretation = "High Risk - Risks outweigh benefits"
        
        return {
            'total_benefit_score': total_benefit,
            'total_risk_score': total_risk,
            'brr': round(brr, 3) if brr != float('inf') else "Infinity",
            'interpretation': brr_interpretation,
            'benefit_components': len(benefit_scores),
            'risk_components': len(risk_scores)
        }
