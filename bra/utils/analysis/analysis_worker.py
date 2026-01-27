
# ================================
# utils/analysis/analysis_worker.py (UPDATED)
# ================================

from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from contraindication.app import start as contra_start
from scoring.scoring_sytem import ScoringSystem
from alternatives.fda_finder import FDAAlternativesFinder
from alternatives.analyzer import analyze_alternatives_rct

# RCT threshold for triggering alternative search
LOW_RCT_THRESHOLD = 100


def analyze_drug_diagnosis(
    drug: str,
    diagnosis: str,
    patient: dict,
    email: str,
    thread_id: int,
    duplication_result: dict | None = None,
    has_duplication_check: bool = False
) -> dict:
    """
    Analyze a single drug-diagnosis combination
    Now uses centralized scoring configuration
    """

    print(f"\n[Thread {thread_id}] {'='*60}")
    print(f"[Thread {thread_id}] Drug: {drug}")
    print(f"[Thread {thread_id}] Diagnosis: {diagnosis}")
    print(f"[Thread {thread_id}] {'='*60}")

    result_file = f"results/{drug}_{diagnosis.replace(' ', '_').replace('/', '_')}_result.json"
    scoring = ScoringSystem(result_file)

    try:
        # 1. Regulatory indication (Benefit Factor)
        print(f"[Thread {thread_id}] → Regulatory analysis...")
        regulatory_result = bedrock_start(drug, diagnosis, scoring)

        # 2. Market experience
        print(f"[Thread {thread_id}] → Market experience analysis...")
        fda_result = fda_start(drug, scoring)

        # 3. PubMed evidence
        print(f"[Thread {thread_id}] → PubMed analysis...")
        pubmed_result = pubmed_start(drug, diagnosis, email, scoring)

        # Get RCT count from pubmed_result
        rct_count = pubmed_result.get("rct_count", 0)
        
        # 4. Check if we need to find alternatives (low RCT count)
        alternatives_data = None
        if rct_count < LOW_RCT_THRESHOLD:
            print(f"[Thread {thread_id}] ⚠️  Low RCT count ({rct_count}) - searching for alternatives...")
            
            try:
                # Find top 3 alternatives
                finder = FDAAlternativesFinder()
                alternatives = finder.get_top_alternatives(drug, diagnosis, top_n=3)
                
                if alternatives:
                    # Analyze RCT counts for alternatives
                    alternative_results = analyze_alternatives_rct(alternatives, diagnosis, email)
                    
                    # Structure the alternatives data
                    alternatives_data = {
                        "trigger_reason": f"Low RCT count ({rct_count} < {LOW_RCT_THRESHOLD})",
                        "original_medicine": {
                            "name": drug,
                            "rct_count": rct_count
                        },
                        "alternatives_found": len(alternative_results),
                        "alternatives": alternative_results,
                        "summary": {
                            "best_alternative": max(alternative_results, key=lambda x: x['rct_count']) if alternative_results else None,
                            "alternatives_with_higher_rct": len([a for a in alternative_results if a['rct_count'] > rct_count])
                        }
                    }
                    
                    # Add to scoring system
                    scoring.add_analysis("alternative_medications", alternatives_data)
                    
                    print(f"[Thread {thread_id}] ✓ Found {len(alternatives)} alternatives")
                    print(f"[Thread {thread_id}]   {alternatives_data['summary']['alternatives_with_higher_rct']} have higher RCT counts")
                else:
                    print(f"[Thread {thread_id}] ⚠️  No alternatives found in FDA database")
                    
            except Exception as e:
                print(f"[Thread {thread_id}] ✗ Error finding alternatives: {e}")
                import traceback
                traceback.print_exc()

        # 5. Contraindications
        print(f"[Thread {thread_id}] → Contraindication analysis...")
        contra_res = contra_start(drug, {"patient": patient}, scoring)

        # 6. Therapeutic Duplication
        if has_duplication_check and duplication_result:
            print(f"[Thread {thread_id}] → Adding therapeutic duplication result")
            scoring.add_analysis("therapeutic_duplication", duplication_result)
        else:
            print(f"[Thread {thread_id}] → Skipping therapeutic duplication (N/A)")
            scoring.add_analysis(
                "therapeutic_duplication",
                {
                    "status": "not_applicable",
                    "reason": "Single medication for this condition - no duplication check needed"
                }
            )

        # 7. Score aggregation
        total_weighted_score = 0
        score_breakdown = {}

        for key, src in [
            ("benefit_factor", regulatory_result.get("benefit_score")),
            ("market_experience", fda_result.get("mme_score")),
            ("pubmed_evidence", pubmed_result.get("evidence_score")),
            ("contraindication_risk", contra_res.get("contra_score")),
        ]:
            if src and isinstance(src, dict) and "weighted_score" in src:
                total_weighted_score += src["weighted_score"]
                score_breakdown[key] = src

        # Add duplication score if applicable
        if has_duplication_check and duplication_result:
            dup_score = duplication_result.get("duplication_score")
            if dup_score and isinstance(dup_score, dict) and "weighted_score" in dup_score:
                total_weighted_score += dup_score["weighted_score"]
                score_breakdown["therapeutic_duplication"] = dup_score

        scoring.add_analysis("summary", {
            "drug": drug,
            "diagnosis": diagnosis,
            "total_weighted_score": total_weighted_score,
            "score_breakdown": score_breakdown,
            "therapeutic_duplication_performed": has_duplication_check,
            "alternatives_analyzed": alternatives_data is not None,
            "rct_count": rct_count
        })

        output_file = scoring.save_to_json()
        
        print(f"[Thread {thread_id}] ✓ Complete - Score: {total_weighted_score}")

        return {
            "success": True,
            "drug": drug,
            "diagnosis": diagnosis,
            "total_score": total_weighted_score,
            "output_file": output_file,
            "duplication_checked": has_duplication_check,
            "rct_count": rct_count,
            "alternatives_found": alternatives_data is not None,
            "alternatives_data": alternatives_data
        }

    except Exception as e:
        print(f"[Thread {thread_id}] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "drug": drug,
            "diagnosis": diagnosis,
            "error": str(e)
        }