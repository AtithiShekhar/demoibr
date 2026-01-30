"""
Centralized Scoring Configuration
All scoring matrices and rules in one place
UPDATED: Includes ADR, RMM, and Consequences scoring
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
    
    MITIGATION_FEASIBILITY = {
        'preventable_reversible': ScoreEntry(
            description="Preventable and Reversible ADR",
            weight=30,
            score=1,
            score_type=ScoreType.RISK
        ),
        'preventable_irreversible': ScoreEntry(
            description="Preventable but Irreversible ADR",
            weight=60,
            score=3,
            score_type=ScoreType.RISK
        ),
        'non_preventable_reversible': ScoreEntry(
            description="Non-preventable but Reversible ADR",
            weight=70,
            score=4,
            score_type=ScoreType.RISK
        ),
        'non_preventable_irreversible': ScoreEntry(
            description="Non-preventable and Irreversible ADR",
            weight=100,
            score=5,
            score_type=ScoreType.RISK
        )
    }
    
    # ========================================
    # HELPER METHODS
    # ========================================
    @classmethod
    def calculate_mitigation_feasibility_score(cls, rmf_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the score for Factor 3.4 based on Reversibility and Preventability.
        Logic: Prioritizes the most severe risk profile found in the ADR list.
        """
        reversibility_map = rmf_data.get('risk_reversibility_risk_tolerability', {})
        preventability_map = rmf_data.get('risk_preventability', {})
        
        # We look for the "Worst Case Scenario" across all detected ADRs
        highest_entry = cls.MITIGATION_FEASIBILITY['preventable_reversible']
        worst_category = "Manageable"
        
        # Set of all ADR unique keys (Medicine - ADR Name)
        all_adr_keys = set(reversibility_map.keys()) | set(preventability_map.keys())
        
        for key in all_adr_keys:
            rev_info = reversibility_map.get(key, {})
            prev_info = preventability_map.get(key, {})
            
            is_reversible = rev_info.get('classification') == 'Reversible ADR'
            is_preventable = prev_info.get('classification') == 'Preventable ADR'
            
            # Mapping logic for the 4 quadrants of Risk Mitigation
            if is_preventable and is_reversible:
                current_entry = cls.MITIGATION_FEASIBILITY['preventable_reversible']
            elif is_preventable and not is_reversible:
                current_entry = cls.MITIGATION_FEASIBILITY['preventable_irreversible']
            elif not is_preventable and is_reversible:
                current_entry = cls.MITIGATION_FEASIBILITY['non_preventable_reversible']
            else: # Non-preventable and Irreversible
                current_entry = cls.MITIGATION_FEASIBILITY['non_preventable_irreversible']
            
            # Keep the highest risk (highest weighted score)
            if current_entry.weighted_score > highest_entry.weighted_score:
                highest_entry = current_entry
                worst_category = f"Highest Risk: {key}"

        return {
            'mitigation_sub_factor': highest_entry.description,
            'worst_case_adr': worst_category,
            'description': highest_entry.description,
            'weight': highest_entry.weight,
            'score': highest_entry.score,
            'weighted_score': highest_entry.weighted_score,
            'score_type': highest_entry.score_type.value
    }
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
    def calculate_lt_adr_score(cls, lt_adrs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Life-Threatening ADR score from Factor 3.2.1 analysis
        
        Args:
            lt_adrs_data: LT ADRs data from Factor 3.2.1
            
        Returns:
            Dictionary with LT ADR scoring details
        """
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
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'adr_count': adr_count,
            'has_risk_factors': has_with_risk_factors
        }
    
    @classmethod
    def calculate_serious_adr_score(cls, serious_adrs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Serious ADR score from Factor 3.2.2 analysis
        
        Args:
            serious_adrs_data: Serious ADRs data from Factor 3.2.2
            
        Returns:
            Dictionary with Serious ADR scoring details
        """
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
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'adr_count': adr_count,
            'has_risk_factors': has_with_risk_factors
        }
    
    @classmethod
    def calculate_drug_interaction_score(cls, interactions_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Drug Interaction score from Factor 3.3 analysis
        
        Args:
            interactions_data: Drug interactions data from Factor 3.3
            
        Returns:
            Dictionary with interaction scoring details
        """
        contraindicated_count = len(interactions_data.get('contraindicated', []))
        lt_interaction_count = len(interactions_data.get('lt_interactions', []))
        serious_interaction_count = len(interactions_data.get('serious_interactions', []))
        
        total_critical = contraindicated_count + lt_interaction_count + serious_interaction_count
        
        if total_critical > 0:
            entry = cls.DRUG_INTERACTIONS['present']
            category = "Drug Interactions Detected"
        else:
            entry = cls.DRUG_INTERACTIONS['none']
            category = "No Drug Interactions"
        
        return {
            'interaction_category': category,
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'contraindicated_count': contraindicated_count,
            'lt_interaction_count': lt_interaction_count,
            'serious_interaction_count': serious_interaction_count,
            'total_critical_interactions': total_critical
        }
    
    @classmethod
    def calculate_rmm_score(cls, rmm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Risk Mitigation Measure score from RMM analysis
        
        Args:
            rmm_data: RMM table data from Step 4
            
        Returns:
            Dictionary with RMM scoring details
        """
        rmm_entries = rmm_data.get('rmm_table', [])
        
        if not rmm_entries:
            entry = cls.RISK_MITIGATION['easily_manageable']
            category = "Minimal Mitigation Required"
            mitigation_level = "low"
        else:
            # Analyze immediate actions to determine mitigation complexity
            discontinuation_count = 0
            strict_monitoring_count = 0
            
            for rmm_entry in rmm_entries:
                action = rmm_entry.get('immediate_actions_required', '').lower()
                
                if 'discontinuation' in action or 'contraindicated' in action:
                    discontinuation_count += 1
                elif 'strict' in action or 'close monitoring' in action:
                    strict_monitoring_count += 1
            
            if discontinuation_count > 0:
                entry = cls.RISK_MITIGATION['no_mitigation']
                category = "Critical - Discontinuation Required"
                mitigation_level = "critical"
            elif strict_monitoring_count > 0 or len(rmm_entries) >= 3:
                entry = cls.RISK_MITIGATION['strict_measures']
                category = "Strict Preventive Measures Required"
                mitigation_level = "strict"
            else:
                entry = cls.RISK_MITIGATION['easily_manageable']
                category = "Manageable with Standard Monitoring"
                mitigation_level = "manageable"
        
        return {
            'rmm_category': category,
            'description': entry.description,
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'rmm_entries_count': len(rmm_entries),
            'mitigation_level': mitigation_level
        }
    
    @classmethod
    def calculate_consequences_score(cls, consequences_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Medical Need Severity score from Factor 2.6 (Consequences) analysis
        
        Args:
            consequences_data: Consequences analysis data from Factor 2.6
            
        Returns:
            Dictionary with medical need severity scoring
        """
        if not consequences_data:
            entry = cls.MEDICAL_NEED_SEVERITY['chronic_non_life_threatening']
            category = "Unknown - Insufficient Data"
            severity_level = "unknown"
            return {
                'medical_need_category': category,
                'description': entry.description,
                'weight': entry.weight,
                'score': entry.score,
                'weighted_score': entry.weighted_score,
                'score_type': entry.score_type.value,
                'severity_level': severity_level
            }
        
        # Analyze consequences to determine severity
        # Look at all classifications across all diagnoses
        is_life_threatening = False
        is_acute = False
        
        for disease, data in consequences_data.items():
            classifications = data.get('classifications', [])
            for classification in classifications:
                category_text = classification.get('category', '').lower()
                
                if 'life-threatening' in category_text:
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
            'weight': entry.weight,
            'score': entry.score,
            'weighted_score': entry.weighted_score,
            'score_type': entry.score_type.value,
            'severity_level': severity_level,
            'is_life_threatening': is_life_threatening,
            'is_acute': is_acute
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