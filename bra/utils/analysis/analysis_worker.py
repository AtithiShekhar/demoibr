# ================================
# utils/analysis_worker.py
# ================================

from approvalstatus.app import start as bedrock_start
from mme.mme_checker import start as fda_start
from pubmed.searcher import start as pubmed_start
from contraindication.app import start as contra_start
from scoring.benefit_factor import ScoringSystem


def analyze_drug_diagnosis(
    drug: str,
    diagnosis: str,
    patient: dict,
    email: str,
    thread_id: int,
    duplication_result: dict | None = None
) -> dict:
    """Worker: drug x diagnosis (NO duplication logic here)"""

    # print(f"\n[Thread {thread_id}] {'='*80}")
    # print(f"[Thread {thread_id}] ANALYZING: {drug} for {diagnosis}")
    # print(f"[Thread {thread_id}] {'='*80}")

    result_file = f"results/{drug}_{diagnosis.replace(' ', '_').replace('/', '_')}_result.json"
    scoring = ScoringSystem(result_file)

    try:
        # 1. Regulatory indication
        regulatory_result = bedrock_start(drug, diagnosis, scoring)

        # 2. Market experience
        fda_result = fda_start(drug, scoring)

        # 3. PubMed evidence
        pubmed_result = pubmed_start(drug, diagnosis, email, scoring)

        # 4. Contraindications
        contra_res = contra_start(drug, {"patient": patient}, scoring)

        # 5. Inject duplication result (already computed once)
        if duplication_result:
            scoring.add_analysis("therapeutic_duplication", duplication_result)

        # 6. Score aggregation
        total_weighted_score = 0
        score_breakdown = {}

        for key, src in [
            ("benefit_factor", regulatory_result.get("benefit_score")),
            ("market_experience", fda_result.get("mme_score")),
            ("pubmed_evidence", pubmed_result.get("evidence_score")),
            ("contraindication_risk", contra_res.get("contra_score")),
            ("therapeutic_duplication", duplication_result.get("duplication_score") if duplication_result else None),
        ]:
            if src:
                total_weighted_score += src["weighted_score"]
                score_breakdown[key] = src

        scoring.add_analysis("summary", {
            "drug": drug,
            "diagnosis": diagnosis,
            "total_weighted_score": total_weighted_score,
            "score_breakdown": score_breakdown
        })

        output_file = scoring.save_to_json()

        return {
            "success": True,
            "drug": drug,
            "diagnosis": diagnosis,
            "total_score": total_weighted_score,
            "output_file": output_file
        }

    except Exception as e:
        return {
            "success": False,
            "drug": drug,
            "diagnosis": diagnosis,
            "error": str(e)
        }

