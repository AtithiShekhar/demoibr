"""
Centralized Scoring Configuration - EXACT VALUES FROM iBR MATRIX
All scoring matrices matching the official iBR scoring system
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
    weighted_score: int
    score_type: ScoreType
    
    @property
    def weight(self) -> int:
        """For backward compatibility"""
        return self.weighted_score
    
    @property
    def score(self) -> int:
        """For backward compatibility - return 1 for all"""
        return 1


class ScoringConfig:
    """Centralized scoring configuration matching official iBR matrix"""
    
    # ========================================
    # BENEFIT SCORING MATRIX (B1-B6)
    # ========================================
    
    # B1: Approval Status
    INDICATION_STRENGTH = {
        'approved': ScoreEntry(
            description="Approved Use",
            weighted_score=450,
            score_type=ScoreType.BENEFIT
        ),
        'off_label': ScoreEntry(
            description="Off label",
            weighted_score=240,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # B2: Molecule Market Experience (MME)
    MARKET_EXPERIENCE = {
        'established': ScoreEntry(
            description="Established indication (>5Y, approved widely)",
            weighted_score=120,
            score_type=ScoreType.BENEFIT
        ),
        'new': ScoreEntry(
            description="New indication (<5Y, limited approval)",
            weighted_score=60,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # B3: Strength of Evidence
    EVIDENCE_STRENGTH = {
        'high': ScoreEntry(
            description="High evidence (multiple RCTs, broad authorization)",
            weighted_score=500,
            score_type=ScoreType.BENEFIT
        ),
        'low': ScoreEntry(
            description="Low evidence (limited data, uncertain)",
            weighted_score=10,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # B4: Therapeutic Duplication
    THERAPEUTIC_DUPLICATION = {
        'unique': ScoreEntry(
            description="Unique role, no overlap",
            weighted_score=450,
            score_type=ScoreType.BENEFIT
        ),
        'some_overlap': ScoreEntry(
            description="Some overlap but with rationale",
            weighted_score=180,
            score_type=ScoreType.BENEFIT
        ),
        'redundant': ScoreEntry(
            description="Redundant/duplicate prescription",
            weighted_score=10,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # B5: Alternatives
    ALTERNATIVES = {
        'no_alternative': ScoreEntry(
            description="No alternative existed",
            weighted_score=500,
            score_type=ScoreType.BENEFIT
        ),
        'same_efficacy': ScoreEntry(
            description="Alternative with same efficacy/safety",
            weighted_score=240,
            score_type=ScoreType.BENEFIT
        ),
        'safer_available': ScoreEntry(
            description="Safer alternatives available",
            weighted_score=30,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # B6: Consequence of Non-Treatment / Severity of Disease
    MEDICAL_NEED_SEVERITY = {
        'acute_life_threatening': ScoreEntry(
            description="Acute, life-threatening condition",
            weighted_score=500,
            score_type=ScoreType.BENEFIT
        ),
        'acute_non_life_threatening': ScoreEntry(
            description="Acute, non-life-threatening",
            weighted_score=240,
            score_type=ScoreType.BENEFIT
        ),
        'chronic_life_threatening': ScoreEntry(
            description="Chronic, life-threatening",
            weighted_score=360,
            score_type=ScoreType.BENEFIT
        ),
        'chronic_non_life_threatening': ScoreEntry(
            description="Chronic, non-life-threatening",
            weighted_score=150,
            score_type=ScoreType.BENEFIT
        ),
        'quality_of_life': ScoreEntry(
            description="Quality of life improvement",
            weighted_score=120,
            score_type=ScoreType.BENEFIT
        ),
        'symptoms_only': ScoreEntry(
            description="Only signs & symptoms management",
            weighted_score=20,
            score_type=ScoreType.BENEFIT
        )
    }
    
    # ========================================
    # RISK SCORING MATRIX (R1-R6)
    # ========================================
    
    # R1: Contraindication Check
    CONTRAINDICATION = {
        'absolute': ScoreEntry(
            description="Absolute contraindication/completely restricted",
            weighted_score=500,
            score_type=ScoreType.RISK
        ),
        'warning': ScoreEntry(
            description="No absolute contraindication, but with warning/precaution",
            weighted_score=10,
            score_type=ScoreType.RISK
        ),
        'safe': ScoreEntry(
            description="No contraindication",
            weighted_score=0,
            score_type=ScoreType.RISK
        ),
        'boxed_warning': ScoreEntry(
            description="Boxed warning present",
            weighted_score=500,
            score_type=ScoreType.RISK
        ),
        'pregnancy_warning': ScoreEntry(
            description="Pregnancy warning/contraindication",
            weighted_score=500,
            score_type=ScoreType.RISK
        )
    }
    
    # R2: Interactions
    DRUG_INTERACTIONS = {
        'contraindicated': ScoreEntry(
            description="Contraindicated Interactions",
            weighted_score=500,
            score_type=ScoreType.RISK
        ),
        'life_threatening': ScoreEntry(
            description="Life threatening Interactions",
            weighted_score=450,
            score_type=ScoreType.RISK
        ),
        'serious': ScoreEntry(
            description="Serious interactions",
            weighted_score=320,
            score_type=ScoreType.RISK
        ),
        'non_serious': ScoreEntry(
            description="Non-serious interactions",
            weighted_score=120,
            score_type=ScoreType.RISK
        ),
        'none': ScoreEntry(
            description="No interactions",
            weighted_score=10,
            score_type=ScoreType.RISK
        )
    }
    
    # R3: Risk Severity (Life-Threatening ADRs)
    LT_ADRS = {
        'with_risk_factors': ScoreEntry(
            description="Life-threatening ADRs + risk factors present in the individual patient being treated",
            weighted_score=500,
            score_type=ScoreType.RISK
        ),
        'no_risk_factors': ScoreEntry(
            description="Life-threatening ADRs with no risk factors in the individual patient context",
            weighted_score=280,
            score_type=ScoreType.RISK
        ),
        'none': ScoreEntry(
            description="No life-threatening ADRs",
            weighted_score=30,
            score_type=ScoreType.RISK
        )
    }
    
    # R3: Risk Severity (Serious ADRs)
    SERIOUS_ADRS = {
        'with_risk_factors': ScoreEntry(
            description="Serious ADRs + risk factors present in the individual patient being treated",
            weighted_score=180,
            score_type=ScoreType.RISK
        ),
        'no_risk_factors': ScoreEntry(
            description="Serious ADRs with no risk factors in the individual patient context",
            weighted_score=20,
            score_type=ScoreType.RISK
        ),
        'none': ScoreEntry(
            description="No Serious ADRs",
            weighted_score=10,
            score_type=ScoreType.RISK
        )
    }
    
    # R4: Risk Preventability
    RISK_PREVENTABILITY = {
        'non_preventable': ScoreEntry(
            description="Non-preventable ADR",
            weighted_score=400,
            score_type=ScoreType.RISK
        ),
        'preventable': ScoreEntry(
            description="Preventable ADR",
            weighted_score=100,
            score_type=ScoreType.RISK
        )
    }
    
    # R5: Risk Reversibility
    RISK_REVERSIBILITY = {
        'irreversible': ScoreEntry(
            description="Irreversible ADR",
            weighted_score=500,
            score_type=ScoreType.RISK
        ),
        'reversible': ScoreEntry(
            description="Reversible ADR",
            weighted_score=300,
            score_type=ScoreType.RISK
        )
    }
    
    # R6: Risk Tolerability
    RISK_TOLERABILITY = {
        'tolerable': ScoreEntry(
            description="Tolerable ADR",
            weighted_score=200,
            score_type=ScoreType.RISK
        ),
        'non_tolerable': ScoreEntry(
            description="Non-Tolerable ADR",
            weighted_score=400,
            score_type=ScoreType.RISK
        )
    }
    
    # Combined RMF (R4 + R5 + R6) for Factor 3.4
    MITIGATION_FEASIBILITY = {
        'preventable_reversible': ScoreEntry(
            description="Preventable and Reversible ADR",
            weighted_score=100,  # R4: Preventable
            score_type=ScoreType.RISK
        ),
        'preventable_irreversible': ScoreEntry(
            description="Preventable but Irreversible ADR",
            weighted_score=100,  # R4: Preventable (higher risk due to irreversibility)
            score_type=ScoreType.RISK
        ),
        'non_preventable_reversible': ScoreEntry(
            description="Non-preventable but Reversible ADR",
            weighted_score=400,  # R4: Non-preventable
            score_type=ScoreType.RISK
        ),
        'non_preventable_irreversible': ScoreEntry(
            description="Non-preventable and Irreversible ADR",
            weighted_score=400,  # R4: Non-preventable (worst case)
            score_type=ScoreType.RISK
        )
    }
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    @classmethod
    def calculate_benefit_factor_score(cls, cdsco_approved: bool, usfda_approved: bool) -> Dict[str, Any]:
        """Calculate B1: Approval Status score"""
        if cdsco_approved or usfda_approved:
            entry = cls.INDICATION_STRENGTH['approved']
            benefit_type = "Approved Use"
        else:
            entry = cls.INDICATION_STRENGTH['off_label']
            benefit_type = "Off label"
        
        return {
            'benefit_sub_factor': benefit_type,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'cdsco_approved': cdsco_approved,
            'usfda_approved': usfda_approved
        }
    
    @classmethod
    def calculate_market_experience_score(cls, years_in_market: int) -> Dict[str, Any]:
        """Calculate B2: Market Experience score"""
        if years_in_market >= 5:
            entry = cls.MARKET_EXPERIENCE['established']
        else:
            entry = cls.MARKET_EXPERIENCE['new']
        
        return {
            'experience_sub_factor': entry.description,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'years_in_market': years_in_market
        }
    
    @classmethod
    def calculate_pubmed_evidence_score(cls, rct_count: int) -> Dict[str, Any]:
        """Calculate B3: Strength of Evidence score"""
        if rct_count >= 100:
            entry = cls.EVIDENCE_STRENGTH['high']
        else:
            entry = cls.EVIDENCE_STRENGTH['low']
        
        return {
            'evidence_sub_factor': entry.description,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'rct_count': rct_count
        }
    
    @classmethod
    def calculate_duplication_score(cls, overlaps: int, redundant: int) -> Dict[str, Any]:
        """Calculate B4: Therapeutic Duplication score"""
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
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'overlaps_found': overlaps,
            'redundant_found': redundant
        }
    
    @classmethod
    def calculate_consequences_score(cls, consequences_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate B6: Medical Need Severity / Consequences score"""
        if not consequences_data:
            entry = cls.MEDICAL_NEED_SEVERITY['chronic_non_life_threatening']
            category = "Unknown - Insufficient Data"
            severity_level = "unknown"
            return {
                'medical_need_category': category,
                'description': entry.description,
                'weight': entry.weighted_score,
                'score': 1,
                'weighted_score': entry.weighted_score,
                'score_type': entry.score_type.value,
                'severity_level': severity_level
            }
        
        # Analyze consequences to determine severity
        is_life_threatening = False
        is_acute = False
        
        for disease, data in consequences_data.items():
            classifications = data.get('classifications', [])
            for classification in classifications:
                category_text = classification.get('category', '').lower()
                
                if 'life-threatening' in category_text or 'life threatening' in category_text:
                    is_life_threatening = True
                if 'acute' in category_text:
                    is_acute = True
        
        # Determine category based on analysis
        if is_acute and is_life_threatening:
            entry = cls.MEDICAL_NEED_SEVERITY['acute_life_threatening']
            category = "Acute, Life-Threatening Condition"
            severity_level = "critical"
        elif is_acute and not is_life_threatening:
            entry = cls.MEDICAL_NEED_SEVERITY['acute_non_life_threatening']
            category = "Acute, Non-Life-Threatening Condition"
            severity_level = "high"
        elif not is_acute and is_life_threatening:
            entry = cls.MEDICAL_NEED_SEVERITY['chronic_life_threatening']
            category = "Chronic, Life-Threatening Condition"
            severity_level = "high"
        else:
            entry = cls.MEDICAL_NEED_SEVERITY['chronic_non_life_threatening']
            category = "Chronic, Non-Life-Threatening Condition"
            severity_level = "moderate"
        
        return {
            'medical_need_category': category,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'severity_level': severity_level,
            'is_life_threatening': is_life_threatening,
            'is_acute': is_acute
        }
    
    @classmethod
    def calculate_contraindication_score(cls, status: str) -> Dict[str, Any]:
        """Calculate R1: Contraindication score"""
        if status not in cls.CONTRAINDICATION:
            status = 'safe'
        
        entry = cls.CONTRAINDICATION[status]
        return {
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'status': status
        }
    
    @classmethod
    def calculate_drug_interaction_score(cls, interactions_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate R2: Drug Interaction score"""
        contraindicated_count = len(interactions_data.get('contraindicated', []))
        lt_interaction_count = len(interactions_data.get('lt_interactions', []))
        serious_interaction_count = len(interactions_data.get('serious_interactions', []))
        non_serious_count = len(interactions_data.get('non_serious_interactions', []))
        
        # Priority: contraindicated > life-threatening > serious > non-serious > none
        if contraindicated_count > 0:
            entry = cls.DRUG_INTERACTIONS['contraindicated']
            category = "Contraindicated Drug Interactions"
        elif lt_interaction_count > 0:
            entry = cls.DRUG_INTERACTIONS['life_threatening']
            category = "Life-Threatening Drug Interactions"
        elif serious_interaction_count > 0:
            entry = cls.DRUG_INTERACTIONS['serious']
            category = "Serious Drug Interactions"
        elif non_serious_count > 0:
            entry = cls.DRUG_INTERACTIONS['non_serious']
            category = "Non-Serious Drug Interactions"
        else:
            entry = cls.DRUG_INTERACTIONS['none']
            category = "No Drug Interactions"
        
        return {
            'interaction_category': category,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'contraindicated_count': contraindicated_count,
            'lt_interaction_count': lt_interaction_count,
            'serious_interaction_count': serious_interaction_count,
            'non_serious_count': non_serious_count
        }
    
    @classmethod
    def calculate_lt_adr_score(cls, lt_adrs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate R3: Life-Threatening ADR score"""
        has_with_risk_factors = len(lt_adrs_data.get('with_risk_factors', [])) > 0
        has_without_risk_factors = len(lt_adrs_data.get('without_risk_factors', [])) > 0
        
        if has_with_risk_factors:
            entry = cls.LT_ADRS['with_risk_factors']
            category = "Critical Risk - LT ADRs with patient risk factors"
            adr_count = len(lt_adrs_data.get('with_risk_factors', []))
        elif has_without_risk_factors:
            entry = cls.LT_ADRS['no_risk_factors']
            category = "High Risk - LT ADRs without specific risk factors"
            adr_count = len(lt_adrs_data.get('without_risk_factors', []))
        else:
            entry = cls.LT_ADRS['none']
            category = "Low Risk - No life-threatening ADRs detected"
            adr_count = 0
        
        return {
            'lt_adr_category': category,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'adr_count': adr_count,
            'has_risk_factors': has_with_risk_factors
        }
    
    @classmethod
    def calculate_serious_adr_score(cls, serious_adrs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate R3: Serious ADR score"""
        has_with_risk_factors = len(serious_adrs_data.get('with_risk_factors', [])) > 0
        has_without_risk_factors = len(serious_adrs_data.get('without_risk_factors', [])) > 0
        
        if has_with_risk_factors:
            entry = cls.SERIOUS_ADRS['with_risk_factors']
            category = "Moderate-High Risk - Serious ADRs with risk factors"
            adr_count = len(serious_adrs_data.get('with_risk_factors', []))
        elif has_without_risk_factors:
            entry = cls.SERIOUS_ADRS['no_risk_factors']
            category = "Moderate Risk - Serious ADRs without specific risk factors"
            adr_count = len(serious_adrs_data.get('without_risk_factors', []))
        else:
            entry = cls.SERIOUS_ADRS['none']
            category = "Low Risk - No serious ADRs detected"
            adr_count = 0
        
        return {
            'serious_adr_category': category,
            'description': entry.description,
            'weight': entry.weighted_score,
            'score': 1,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'adr_count': adr_count,
            'has_risk_factors': has_with_risk_factors
        }
    
    @classmethod
    def calculate_mitigation_feasibility_score(cls, rmf_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate R4+R5+R6: Mitigation Feasibility (Preventability + Reversibility + Tolerability)
        Returns the worst-case scenario across all ADRs
        """
        reversibility_map = rmf_data.get('risk_reversibility_risk_tolerability', {})
        preventability_map = rmf_data.get('risk_preventability', {})
        
        # Start with best case
        highest_entry = cls.MITIGATION_FEASIBILITY['preventable_reversible']
        worst_category = "Manageable"
        
        # Get all ADR keys
        all_adr_keys = set(reversibility_map.keys()) | set(preventability_map.keys())
        
        for key in all_adr_keys:
            rev_info = reversibility_map.get(key, {})
            prev_info = preventability_map.get(key, {})
            
            is_reversible = rev_info.get('classification') == 'Reversible ADR'
            is_preventable = prev_info.get('classification') == 'Preventable ADR'
            
            # Determine quadrant
            if is_preventable and is_reversible:
                current_entry = cls.MITIGATION_FEASIBILITY['preventable_reversible']
            elif is_preventable and not is_reversible:
                current_entry = cls.MITIGATION_FEASIBILITY['preventable_irreversible']
            elif not is_preventable and is_reversible:
                current_entry = cls.MITIGATION_FEASIBILITY['non_preventable_reversible']
            else:
                current_entry = cls.MITIGATION_FEASIBILITY['non_preventable_irreversible']
            
            # Keep highest risk
            if current_entry.weighted_score > highest_entry.weighted_score:
                highest_entry = current_entry
                worst_category = f"Highest Risk: {key}"
        
        return {
            'mitigation_sub_factor': highest_entry.description,
            'worst_case_adr': worst_category,
            'description': highest_entry.description,
            'weight': highest_entry.weighted_score,
            'score': 1,
            'weighted_score': highest_entry.weighted_score,
            'score_type': highest_entry.score_type.value
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
            
            # Interpretation based on iBR thresholds
            if brr >= 6:
                brr_interpretation = "Excellent - Benefits strongly outweigh risks"
            elif brr >= 2:
                brr_interpretation = "Acceptable - Benefits outweigh risks with monitoring"
            elif brr >= 1:
                brr_interpretation = "Marginal - Benefits slightly outweigh risks"
            else:
                brr_interpretation = "Unfavorable - Risks outweigh benefits"
        
        return {
            'total_benefit_score': total_benefit,
            'total_risk_score': total_risk,
            'brr': round(brr, 2) if brr != float('inf') else "Infinity",
            'interpretation': brr_interpretation,
            'benefit_components': len(benefit_scores),
            'risk_components': len(risk_scores)
        }