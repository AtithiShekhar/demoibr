from typing import Any, Dict
from utils.db_query import ask_question
def med_info_tool(context_for_llm:str, med_name: str) -> Dict[str, Any]:
    """
    Tool: Retrieve authoritative medication information.
    Returns structured dict or error dict. Agent MUST use only this output
    for drug facts.
    """
    if not med_name or not isinstance(med_name, str):
        return {"error": "Invalid or empty medication name passed to tool."}
    # wholerespons=ask_question()
    result = context_for_llm
    if not result:
        return {
            "error": f"No information found for medication '{med_name}'. Ensure the drug is present in DRUG_DATA."
        }

    return {
        "drug_name": result.get("name"),
        "indication": result.get("indication", []),
        "benefits": result.get("benefits", []),
        "risks": result.get("risks", []),
        "contraindications": result.get("contraindications", []),
        "interactions": result.get("interactions", []),
        "risk_minimization_measures": result.get("rmm", []),
        "monitoring": result.get("monitoring", []),
        "fit_med_outcome": result.get("fit_med_outcome", "Unknown"),
    }
