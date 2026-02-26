"""
utils/analysis/analysis_worker.py
Worker functions for drug-diagnosis analysis
UPDATED: Mandatory alternatives analysis for ALL medications (no threshold)
"""
from adrs.app import start as adrs_start
from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from contraindication.app import start as contra_start
from scoring.scoring_sytem import ScoringSystem
from alternatives.fda_finder import FDAAlternativesFinder
from typing import Dict, List


def analyze_single_drug(
    drug: str,
    diagnosis: str,
    patient: dict,
    email: str,
    thread_id: int,
    duplication_result: dict | None = None,
    has_duplication_check: bool = False,
    is_alternative: bool = False,
    full_patient_data: dict = None
) -> Dict:
    """
    Perform complete analysis for a single drug-diagnosis pair
    
    Args:
        drug: Medication name
        diagnosis: Diagnosis name
        patient: Patient information (patientInfo)
        email: Email for PubMed
        thread_id: Thread ID for logging
        duplication_result: Pre-computed duplication result
        has_duplication_check: Whether duplication was checked
        is_alternative: Whether this is an alternative medication
        full_patient_data: Full patient data including currentDiagnoses, MedicalHistory
        
    Returns:
        Complete analysis result dictionary
    """
    prefix = "ALT" if is_alternative else "Thread"
    print(f"\n[{prefix} {thread_id}] {'='*60}")
    print(f"[{prefix} {thread_id}] Drug: {drug}")
    print(f"[{prefix} {thread_id}] Diagnosis: {diagnosis}")
    print(f"[{prefix} {thread_id}] {'='*60}")

    # Create result filename - mark alternatives clearly
    if is_alternative:
        result_file = f"results/ALT_{drug}_{diagnosis.replace(' ', '_').replace('/', '_')}_result.json"
    else:
        result_file = f"results/{drug}_{diagnosis.replace(' ', '_').replace('/', '_')}_result.json"
    
    scoring = ScoringSystem(result_file)
    
    # Attach patient data to scoring system for context-aware modules
    if full_patient_data:
        scoring.patient_data = full_patient_data

    try:
        # 1. Regulatory indication (Benefit Factor)
        print(f"[{prefix} {thread_id}] → Regulatory analysis...")
        regulatory_result = bedrock_start(drug, diagnosis, scoring)

        # 2. Market experience
        print(f"[{prefix} {thread_id}] → Market experience analysis...")
        fda_result = fda_start(drug, scoring)

        # 3. PubMed evidence
        print(f"[{prefix} {thread_id}] → PubMed analysis...")
        pubmed_result = pubmed_start(drug, diagnosis, email, scoring)
        rct_count = pubmed_result.get("rct_count", 0)

        # 4. Contraindications - Pass full patient data with MedicalHistory
        print(f"[{prefix} {thread_id}] → Contraindication analysis...")
        contra_patient_data = full_patient_data if full_patient_data else {"patient": patient}
        contra_res = contra_start(drug, diagnosis, contra_patient_data, scoring)
        has_contraindication = contra_res.get("has_contraindication", False)
        
        print(f"[{prefix} {thread_id}] → Contraindication detected: {has_contraindication}")

        # 5. Therapeutic Duplication
        if has_duplication_check and duplication_result:
            print(f"[{prefix} {thread_id}] → Adding therapeutic duplication result")
            scoring.add_analysis("therapeutic_duplication", duplication_result)
        else:
            scoring.add_analysis(
                "therapeutic_duplication",
                {
                    "status": "not_applicable",
                    "reason": "Single medication for this condition - no duplication check needed"
                }
            )

        # 6. ADRs Analysis (with pregnancy and medical history context)
        print(f"[{prefix} {thread_id}] → ADRs analysis...")
        adrs_res = adrs_start(drug, scoring)
        has_lt_adrs = adrs_res.get("has_life_threatening_adrs", False)
        has_serious_adrs = adrs_res.get("has_serious_adrs", False)
        has_drug_interactions = adrs_res.get("has_drug_interactions", False)

        # 7. Risk Mitigation Feasibility (Factor 3.4) - with patient context
        try:
            from risk_mitigation_feasability.rmf import start as rmf_start
            print(f"[{prefix} {thread_id}] → Mitigation feasibility analysis...")
            rmf_data = rmf_start(scoring_system=scoring)
        except Exception as e:
            print(f"[{prefix} {thread_id}] ⚠️  Mitigation analysis not available: {e}")
            rmf_data = {}

        # 8. Consequences - with patient context
        try:
            from consequences.consequences import start as cons_start
            print(f"[{prefix} {thread_id}] → Consequences analysis...")
            conn_data = cons_start(scoring_system=scoring)
        except Exception as e:
            print(f"[{prefix} {thread_id}] ⚠️  Consequences not available: {e}")
            conn_data = {}

        # 9. RMM - with pregnancy and medical history context
        try:
            from rrm.rrm import start as rrm_start
            print(f"[{prefix} {thread_id}] → RRM analysis...")
            rrm_table = rrm_start(scoring_system=scoring)
        except Exception as e:
            print(f"[{prefix} {thread_id}] ⚠️  RRM not available: {e}")
            rrm_table = []

        # Calculate BRR
        brr_data = scoring.calculate_brr()

        # Score aggregation
        total_weighted_score = sum(scoring.benefit_scores) + sum(scoring.risk_scores)
        
        score_breakdown = {}
        for key, src in [
            ("benefit_factor", regulatory_result.get("benefit_score")),
            ("market_experience", fda_result.get("mme_score")),
            ("pubmed_evidence", pubmed_result.get("evidence_score")),
            ("contraindication_risk", contra_res.get("contra_score")),
        ]:
            if src and isinstance(src, dict) and "weighted_score" in src:
                score_breakdown[key] = src

        if has_duplication_check and duplication_result:
            dup_score = duplication_result.get("duplication_score")
            if dup_score and isinstance(dup_score, dict) and "weighted_score" in dup_score:
                score_breakdown["therapeutic_duplication"] = dup_score

        # Store complete analysis summary
        scoring.add_analysis("summary", {
            "drug": drug,
            "diagnosis": diagnosis,
            "total_weighted_score": total_weighted_score,
            "total_benefit_score": brr_data['total_benefit_score'],
            "total_risk_score": brr_data['total_risk_score'],
            "brr": brr_data['brr'],
            "brr_interpretation": brr_data['interpretation'],
            "score_breakdown": score_breakdown,
            "therapeutic_duplication_performed": has_duplication_check,
            "rct_count": rct_count,
            "has_contraindication": has_contraindication,
            "has_life_threatening_adrs": has_lt_adrs,
            "has_serious_adrs": has_serious_adrs,
            "has_drug_interactions": has_drug_interactions,
            "rmm": rrm_table,
            "consequence": conn_data,
            "rmf": rmf_data
        })

        output_file = scoring.save_to_json()
        
        print(f"[{prefix} {thread_id}] ✓ Complete - BRR: {brr_data['brr']} ({brr_data['interpretation']})")
        
        return {
            "success": True,
            "drug": drug,
            "diagnosis": diagnosis,
            "total_score": total_weighted_score,
            "total_benefit_score": brr_data['total_benefit_score'],
            "total_risk_score": brr_data['total_risk_score'],
            "brr": brr_data['brr'],
            "brr_interpretation": brr_data['interpretation'],
            "output_file": output_file,
            "duplication_checked": has_duplication_check,
            "rct_count": rct_count,
            "has_contraindication": has_contraindication,
            "has_life_threatening_adrs": has_lt_adrs,
            "has_serious_adrs": has_serious_adrs,
            "has_drug_interactions": has_drug_interactions
        }

    except Exception as e:
        print(f"[{prefix} {thread_id}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "drug": drug,
            "diagnosis": diagnosis,
            "error": str(e)
        }


def find_and_analyze_alternatives(
    drug: str,
    diagnosis: str,
    patient: dict,
    email: str,
    thread_id: int,
    full_patient_data: dict = None,
    top_n: int = 5
) -> List[Dict]:
    """
    Find and perform COMPLETE analysis on 4-5 alternative medications
    
    UPDATED: Always called for ALL medications (no threshold checking)
    
    Args:
        drug: Current medication name
        diagnosis: Diagnosis/indication
        patient: Patient information
        email: Email for PubMed
        thread_id: Thread ID for logging
        full_patient_data: Full patient data with MedicalHistory
        top_n: Number of alternatives to analyze (default 5)
        
    Returns:
        List of complete analysis results for alternatives
    """
    print(f"\n[Thread {thread_id}] 🔍 SEARCHING FOR ALTERNATIVES FOR {drug}...")
    print(f"[Thread {thread_id}] No threshold check - analyzing alternatives for ALL medications")
    
    alternative_analyses = []
    
    try:
        # Find alternatives using FDA API
        finder = FDAAlternativesFinder()
        alternatives = finder.get_top_alternatives(drug, diagnosis, top_n=top_n)
        
        if not alternatives:
            print(f"[Thread {thread_id}] ⚠️  No alternatives found in FDA database for {drug}")
            return []
        
        print(f"[Thread {thread_id}] ✓ Found {len(alternatives)} alternatives")
        print(f"[Thread {thread_id}] Running COMPLETE analysis on each alternative...")
        
        # Perform FULL analysis on each alternative
        for idx, alt in enumerate(alternatives, 1):
            alt_name = alt['Active_Moiety']
            print(f"\n[Thread {thread_id}] {'='*60}")
            print(f"[Thread {thread_id}] Alternative {idx}/{len(alternatives)}: {alt_name}")
            print(f"[Thread {thread_id}] {'='*60}")
            
            # Run complete analysis for alternative
            alt_result = analyze_single_drug(
                drug=alt_name,
                diagnosis=diagnosis,
                patient=patient,
                email=email,
                thread_id=f"{thread_id}-ALT{idx}",
                duplication_result=None,
                has_duplication_check=False,
                is_alternative=True,
                full_patient_data=full_patient_data
            )
            
            # Add alternative metadata
            if alt_result.get("success"):
                alt_result['alternative_info'] = {
                    'brand_name': alt.get('Brand_Name', 'Unknown'),
                    'generic_name': alt.get('Generic_Name', 'Unknown'),
                    'manufacturer': alt.get('Manufacturer', 'Unknown'),
                    'route': alt.get('Route', 'Unknown'),
                    'alternative_rank': idx,
                    'primary_drug': drug,
                    'primary_diagnosis': diagnosis,
                    'analysis_reason': 'Mandatory alternative analysis (no threshold)'
                }
                
                # Add comparison to primary drug
                alt_result['comparison_to_primary'] = {
                    'primary_drug': drug,
                    'primary_brr': None,  # Will be filled by calling function
                    'alternative_brr': alt_result.get('brr'),
                    'brr_difference': None  # Will be calculated later
                }
                
                alternative_analyses.append(alt_result)
                
                print(f"[Thread {thread_id}] ✓ Alternative {idx} analyzed - BRR: {alt_result.get('brr')}")
            else:
                print(f"[Thread {thread_id}] ✗ Alternative {idx} analysis failed")
        
        print(f"\n[Thread {thread_id}] ✓ Completed analysis for {len(alternative_analyses)}/{len(alternatives)} alternatives")
        
    except Exception as e:
        print(f"[Thread {thread_id}] ✗ Error in alternatives analysis: {e}")
        import traceback
        traceback.print_exc()
    
    return alternative_analyses


def analyze_drug_diagnosis(
    drug: str,
    diagnosis: str,
    patient: dict,
    email: str,
    thread_id: int,
    duplication_result: dict | None = None,
    has_duplication_check: bool = False,
    full_patient_data: dict = None
) -> dict:
    """
    Main analysis function - analyzes drug AND ALWAYS finds alternatives
    
    UPDATED: Alternatives analyzed for ALL medications (no threshold)
    
    Args:
        drug: Medication name
        diagnosis: Diagnosis name
        patient: Patient information (patientInfo)
        email: Email for PubMed
        thread_id: Thread identifier
        duplication_result: Pre-computed duplication result
        has_duplication_check: Whether duplication was checked
        full_patient_data: Full patient data including currentDiagnoses, MedicalHistory
    
    Returns:
        Dictionary with primary analysis and alternative analyses
    """
    
    # Analyze the primary drug
    print(f"\n[Thread {thread_id}] {'='*80}")
    print(f"[Thread {thread_id}] PRIMARY DRUG ANALYSIS: {drug} for {diagnosis}")
    print(f"[Thread {thread_id}] {'='*80}")
    
    primary_result = analyze_single_drug(
        drug=drug,
        diagnosis=diagnosis,
        patient=patient,
        email=email,
        thread_id=thread_id,
        duplication_result=duplication_result,
        has_duplication_check=has_duplication_check,
        is_alternative=False,
        full_patient_data=full_patient_data
    )
    
    if not primary_result.get("success"):
        print(f"[Thread {thread_id}] ✗ Primary drug analysis failed")
        return primary_result
    
    primary_brr = primary_result.get("brr", 0)
    
    # ALWAYS find and analyze alternatives (no threshold check)
    print(f"\n[Thread {thread_id}] {'='*80}")
    print(f"[Thread {thread_id}] ALTERNATIVES ANALYSIS (Mandatory for all medications)")
    print(f"[Thread {thread_id}] Primary Drug BRR: {primary_brr}")
    print(f"[Thread {thread_id}] {'='*80}")
    
    alternative_analyses = find_and_analyze_alternatives(
        drug=drug,
        diagnosis=diagnosis,
        patient=patient,
        email=email,
        thread_id=thread_id,
        full_patient_data=full_patient_data,
        top_n=5  # Analyze 4-5 alternatives
    )
    
    # Add primary BRR comparison to each alternative
    for alt in alternative_analyses:
        if 'comparison_to_primary' in alt:
            alt['comparison_to_primary']['primary_brr'] = primary_brr
            alt_brr = alt['comparison_to_primary']['alternative_brr']
            if alt_brr is not None:
                alt['comparison_to_primary']['brr_difference'] = alt_brr - primary_brr
                alt['comparison_to_primary']['is_better'] = alt_brr > primary_brr
    
    # Sort alternatives by BRR (best first)
    alternative_analyses.sort(
        key=lambda x: x.get('brr', 0) if x.get('brr') != float('inf') else 999,
        reverse=True
    )
    
    # Return comprehensive result
    result = {
        **primary_result,
        "alternatives_analyzed": len(alternative_analyses) > 0,
        "alternatives_count": len(alternative_analyses),
        "alternative_analyses": alternative_analyses,
        "alternatives_analysis_reason": "Mandatory analysis for all medications (no threshold)"
    }
    
    # Summary statistics
    if alternative_analyses:
        best_alternative = alternative_analyses[0]
        result['alternatives_summary'] = {
            'total_analyzed': len(alternative_analyses),
            'best_alternative': best_alternative.get('drug'),
            'best_alternative_brr': best_alternative.get('brr'),
            'better_alternatives_count': sum(1 for alt in alternative_analyses 
                                            if alt.get('brr', 0) > primary_brr),
            'primary_vs_best_alternative': {
                'primary_drug': drug,
                'primary_brr': primary_brr,
                'best_alternative_drug': best_alternative.get('drug'),
                'best_alternative_brr': best_alternative.get('brr'),
                'improvement': best_alternative.get('brr', 0) - primary_brr
            }
        }
    
    print(f"\n[Thread {thread_id}] {'='*80}")
    print(f"[Thread {thread_id}] ANALYSIS COMPLETE")
    print(f"[Thread {thread_id}] Primary: {drug} (BRR: {primary_brr})")
    print(f"[Thread {thread_id}] Alternatives analyzed: {len(alternative_analyses)}")
    if alternative_analyses:
        print(f"[Thread {thread_id}] Best alternative: {best_alternative.get('drug')} (BRR: {best_alternative.get('brr')})")
    print(f"[Thread {thread_id}] {'='*80}")
    
    return result


def analyze_all_currentdiagnoses_medications(
    full_patient_data: dict,
    email: str
) -> Dict[str, List[Dict]]:
    """
    Analyze ALL medications in currentDiagnoses with alternatives
    
    NEW FUNCTION: Entry point for complete patient medication analysis
    
    Args:
        full_patient_data: Complete patient data with currentDiagnoses, MedicalHistory
        email: Email for PubMed
        
    Returns:
        Dictionary mapping each medication to its complete analysis + alternatives
    """
    from patient_data_parser import PatientDataParser
    
    # Parse patient data
    parser = PatientDataParser()
    normalized_data = parser.parse_patient_data(full_patient_data)
    
    patient = normalized_data.get("patient", {})
    current_medications = normalized_data.get("current_medications_detailed", [])
    
    print("\n" + "="*80)
    print("ANALYZING ALL CURRENT MEDICATIONS WITH ALTERNATIVES")
    print("="*80)
    print(f"Total medications to analyze: {len(current_medications)}")
    print("="*80 + "\n")
    
    all_results = {}
    
    for idx, med_detail in enumerate(current_medications, 1):
        drug = med_detail["name"]
        diagnosis = med_detail["indication"]
        
        print(f"\n{'#'*80}")
        print(f"# MEDICATION {idx}/{len(current_medications)}: {drug}")
        print(f"{'#'*80}\n")
        
        # Analyze medication with alternatives
        result = analyze_drug_diagnosis(
            drug=drug,
            diagnosis=diagnosis,
            patient=patient,
            email=email,
            thread_id=idx,
            duplication_result=None,
            has_duplication_check=False,
            full_patient_data=normalized_data
        )
        
        all_results[drug] = result
    
    print("\n" + "="*80)
    print("ALL MEDICATIONS ANALYZED")
    print("="*80)
    print(f"Total medications: {len(all_results)}")
    print(f"Total alternatives analyzed: {sum(r.get('alternatives_count', 0) for r in all_results.values())}")
    print("="*80 + "\n")
    
    return all_results