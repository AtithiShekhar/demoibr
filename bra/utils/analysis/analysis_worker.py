"""
utils/analysis_worker.py
Worker functions for parallel drug-diagnosis analysis
"""

from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from contraindication.app import start as contra_start
from duplication.checker import start as duplication_start
from scoring.benefit_factor import ScoringSystem


def analyze_drug_diagnosis(drug: str, diagnosis: str, patient: dict, email: str, thread_id: int, full_patient_data: dict = None) -> dict:
    """
    Analyze a single drug-diagnosis combination
    
    Args:
        drug: Medicine name
        diagnosis: Diagnosis condition
        patient: Patient information dictionary
        email: Email for PubMed API
        thread_id: Thread identifier for logging
        
    Returns:
        Dictionary with analysis results
    """
    print(f"\n[Thread {thread_id}] {'='*80}")
    print(f"[Thread {thread_id}] ANALYZING: {drug} for {diagnosis}")
    print(f"[Thread {thread_id}] {'='*80}")
    
    result_file = f"results/{drug}_{diagnosis.replace(' ', '_').replace('/', '_')}_result.json"
    scoring = ScoringSystem(result_file)
    
    try:
        # ============================================================
        # 1. REGULATORY INDICATION (CDSCO + USFDA)
        # ============================================================
        print(f"[Thread {thread_id}] === REGULATORY INDICATION ===")
        regulatory_result = bedrock_start(drug, diagnosis, scoring)
        print(f"[Thread {thread_id}] {regulatory_result['output']}")
        
        # ============================================================
        # 2. USFDA MARKET EXPERIENCE (MME)
        # ============================================================
        print(f"[Thread {thread_id}] === USFDA MARKET EXPERIENCE ===")
        fda_result = fda_start(drug, scoring)
        print(f"[Thread {thread_id}] {fda_result['output']}")
        
        # ============================================================
        # 3. PUBMED EVIDENCE
        # ============================================================
        print(f"[Thread {thread_id}] === PUBMED EVIDENCE ===")
        pubmed_result = pubmed_start(drug, diagnosis, email, scoring)
        print(f"[Thread {thread_id}] {pubmed_result['output']}")
        
        # ============================================================
        # 4. FDA CONTRAINDICATION ANALYSIS
        # ============================================================
        print(f"[Thread {thread_id}] === FDA CONTRAINDICATION CHECK ===")
        contra_res = contra_start(drug, {"patient": patient}, scoring)
        print(f"[Thread {thread_id}] {contra_res['output']}")
        if contra_res.get('ibr_text'):
            print(f"[Thread {thread_id}] iBR: {contra_res['ibr_text']}")
        
        # ============================================================
        # 5. THERAPEUTIC DUPLICATION CHECK (runs once per patient, not per drug)
        # ============================================================
        duplication_res = None
        if ( full_patient_data
            # and isinstance(full_patient_data, dict)
            # and isinstance(full_patient_data.get("prescription"), list)
            # and len(full_patient_data["prescription"]) > 1
            ):
            print(f"[Thread {thread_id}] === THERAPEUTIC DUPLICATION CHECK ===")
            duplication_res = duplication_start(full_patient_data, scoring)
            print(f"[Thread {thread_id}] {duplication_res['output']}")
        
        # ============================================================
        # 6. CALCULATE TOTAL WEIGHTED SCORE
        # ============================================================
        total_weighted_score = 0
        score_breakdown = {}
        
        # 1. Regulatory Indication
        if regulatory_result.get('benefit_score'):
            w = regulatory_result['benefit_score']['weighted_score']
            total_weighted_score += w
            score_breakdown['benefit_factor'] = regulatory_result['benefit_score']
        
        # 2. Market Experience
        if fda_result.get('mme_score'):
            w = fda_result['mme_score']['weighted_score']
            total_weighted_score += w
            score_breakdown['market_experience'] = fda_result['mme_score']
        
        # 3. PubMed Evidence
        if pubmed_result.get('evidence_score'):
            w = pubmed_result['evidence_score']['weighted_score']
            total_weighted_score += w
            score_breakdown['pubmed_evidence'] = pubmed_result['evidence_score']
        
        # 4. Contraindication
        if contra_res.get('contra_score'):
            w = contra_res['contra_score']['weighted_score']
            total_weighted_score += w
            score_breakdown['contraindication_risk'] = contra_res['contra_score']
        
        # 5. Therapeutic Duplication
        if duplication_res and duplication_res.get('duplication_score'):
            w = duplication_res['duplication_score']['weighted_score']
            total_weighted_score += w
            score_breakdown['therapeutic_duplication'] = duplication_res['duplication_score']
        
        # Add summary to scoring system
        scoring.add_analysis("summary", {
            "drug": drug,
            "diagnosis": diagnosis,
            "total_weighted_score": total_weighted_score,
            "score_breakdown": score_breakdown
        })
        
        # Save results
        output_file = scoring.save_to_json()
        
        print(f"[Thread {thread_id}] {'='*80}")
        print(f"[Thread {thread_id}] SCORING SUMMARY:")
        print(f"[Thread {thread_id}] Total Weighted Score: {total_weighted_score}")
        
        for component, scores in score_breakdown.items():
            print(
                f"[Thread {thread_id}]   {component}: {scores['weighted_score']} "
                f"(Weight: {scores['weight']}, Score: {scores['score']})"
            )
        
        print(f"[Thread {thread_id}] Results saved to: {output_file}")
        print(f"[Thread {thread_id}] {'='*80}\n")
        
        return {
            'success': True,
            'drug': drug,
            'diagnosis': diagnosis,
            'total_score': total_weighted_score,
            'output_file': output_file
        }
        
    except Exception as e:
        print(f"[Thread {thread_id}] ERROR analyzing {drug} for {diagnosis}: {e}")
        return {
            'success': False,
            'drug': drug,
            'diagnosis': diagnosis,
            'error': str(e)
        }