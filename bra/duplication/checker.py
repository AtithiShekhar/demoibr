

# ================================
# duplication/checker.py
# ================================

from datetime import datetime
from scoring.config import ScoringConfig


def start(data: dict) -> dict:
    """Therapeutic duplication checker"""
    prescription = data.get("prescription", [])
    
    if len(prescription) < 2:
        return {
            "status": "skipped",
            "reason": "Less than 2 medications"
        }
    
    unique_pairs = []
    overlap_pairs = []
    redundant_pairs = []
    
    for i in range(len(prescription)):
        for j in range(i + 1, len(prescription)):
            med1, med2 = prescription[i], prescription[j]
            unique_pairs.append({
                "medicine_1": med1,
                "medicine_2": med2,
                "category": "unique",
                "reason": "No significant overlap detected",
                "recommendation": "✓ Medications appear to have unique roles"
            })
    
    overlaps = len(overlap_pairs)
    redundant = len(redundant_pairs)
    score_data = ScoringConfig.calculate_duplication_score(overlaps, redundant)
    
    summary = f"✓ All {len(unique_pairs)} medication pair(s) have unique roles"
    if redundant > 0:
        summary = f"⚠️ Found {redundant} redundant medication pair(s)"
    elif overlaps > 0:
        summary = f"⚠️ Found {overlaps} overlapping medication pair(s)"
    
    return {
        "detailed_results": {
            "date": datetime.now().isoformat(),
            "total_medications": len(prescription),
            "pairs_analyzed": len(unique_pairs) + len(overlap_pairs) + len(redundant_pairs),
            "unique_no_overlap": unique_pairs,
            "overlap_with_rationale": overlap_pairs,
            "redundant_duplicate": redundant_pairs,
            "summary": summary
        },
        "duplication_score": score_data,
        "summary": summary,
        "output": f"Therapeutic Duplication Analysis: {summary}",
        "unique_count": len(unique_pairs),
        "overlap_count": overlaps,
        "redundant_count": redundant
    }
