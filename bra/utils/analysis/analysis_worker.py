"""
utils/analysis/analysis_worker.py
Worker functions for drug-diagnosis analysis
UPDATED: Fixed contraindication to exclude treating diagnosis
"""
from adrs.app import start as adrs_start
from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from contraindication.app import start as contra_start  # Use fixed version
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
        full_patient_data: Full patient data including currentDiagnoses, chiefComplaints
        
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

        # 4. Contraindications - FIXED: Pass diagnosis to exclude it from contraindication check
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

        # 6. ADRs Analysis
        print(f"[{prefix} {thread_id}] → ADRs analysis...")
        adrs_res = adrs_start(drug, scoring)
        has_lt_adrs = adrs_res.get("has_life_threatening_adrs", False)
        has_serious_adrs = adrs_res.get("has_serious_adrs", False)
        has_drug_interactions = adrs_res.get("has_drug_interactions", False)

# 7. RRM and Consequences
        try:
            from rrm.rrm import start as rrm_start
            print(f"[{prefix} {thread_id}] → RRM analysis...")
            # RRM table generation (used for clinical reporting)
            rrm_table = rrm_start()
        except Exception as e:
            print(f"[{prefix} {thread_id}] ⚠️  RRM not available: {e}")
            rrm_table = []

        try:
            from consequences.consequences import start as cons_start
            print(f"[{prefix} {thread_id}] → Consequences analysis...")
            # NEW: Passing 'scoring' triggers internal get_consequences_data()
            conn_data = cons_start(scoring_system=scoring)
        except Exception as e:
            print(f"[{prefix} {thread_id}] ⚠️  Consequences not available: {e}")
            conn_data = {}

        # 8. Risk Mitigation Feasibility (Factor 3.4)
        try:
            from risk_mitigation_feasability.rmf import start as rmf_start
            print(f"[{prefix} {thread_id}] → Mitigation feasibility analysis...")
            # NEW: Passing 'scoring' triggers internal get_mitigation_feasibility_data()
            rmf_data = rmf_start(scoring_system=scoring)
        except Exception as e:
            print(f"[{prefix} {thread_id}] ⚠️  Mitigation analysis not available: {e}")
            rmf_data = {}
        brr_data = scoring.calculate_brr()

        # 8. RRM and Consequences (if available)
        

        # 9. Score aggregation
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
            "rmf":rmf_data
        })

        output_file = scoring.save_to_json()
        
        print(f"[{prefix} {thread_id}] ✓ Complete - BRR: {brr_data['brr']} ({brr_data['interpretation']})")
        # print(f'has drug interation is {has_drug_interactions},has contraindicatio is {has_contraindication},has life threatining adrs{has_lt_adrs} has serius adrs{has_serious_adrs}')
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
    Main analysis function - analyzes drug and finds alternatives if contraindicated
    
    Args:
        drug: Medication name
        diagnosis: Diagnosis name
        patient: Patient information (patientInfo)
        email: Email for PubMed
        thread_id: Thread identifier
        duplication_result: Pre-computed duplication result
        has_duplication_check: Whether duplication was checked
        full_patient_data: Full patient data including currentDiagnoses, chiefComplaints
    
    Returns:
        Dictionary with primary analysis and alternative analyses (if applicable)
    """
    
    # Analyze the primary drug
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
    
    # Check if we need to find alternatives
    if not primary_result.get("success"):
        return primary_result
    
    has_contraindication = primary_result.get("has_contraindication", False)
    
    alternative_analyses = []
    
    if has_contraindication:
        print(f"\n[Thread {thread_id}] ⚠️  CONTRAINDICATION DETECTED - Searching for alternatives...")
        
        try:
            # Find alternatives using FDA API
            finder = FDAAlternativesFinder()
            alternatives = finder.get_top_alternatives(drug, diagnosis, top_n=3)
            
            if alternatives:
                print(f"[Thread {thread_id}] ✓ Found {len(alternatives)} alternatives - Running full analysis...")
                
                # Perform FULL analysis on each alternative
                for idx, alt in enumerate(alternatives, 1):
                    alt_name = alt['Active_Moiety']
                    print(f"\n[Thread {thread_id}] Analyzing Alternative {idx}/{len(alternatives)}: {alt_name}")
                    
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
                    
                    # Add alternative metadata and link to primary drug
                    if alt_result.get("success"):
                        alt_result['alternative_info'] = {
                            'brand_name': alt.get('Brand_Name', 'Unknown'),
                            'generic_name': alt.get('Generic_Name', 'Unknown'),
                            'manufacturer': alt.get('Manufacturer', 'Unknown'),
                            'route': alt.get('Route', 'Unknown'),
                            'alternative_rank': idx,
                            'primary_drug': drug,
                            'primary_diagnosis': diagnosis
                        }
                        alternative_analyses.append(alt_result)
                
                print(f"[Thread {thread_id}] ✓ Completed analysis for {len(alternative_analyses)} alternatives")
            else:
                print(f"[Thread {thread_id}] ⚠️  No alternatives found in FDA database")
                
        except Exception as e:
            print(f"[Thread {thread_id}] ✗ Error finding/analyzing alternatives: {e}")
            import traceback
            traceback.print_exc()
    
    # Return comprehensive result with alternatives attached
    return {
        **primary_result,
        "alternatives_analyzed": len(alternative_analyses) > 0,
        "alternatives_count": len(alternative_analyses),
        "alternative_analyses": alternative_analyses
    }