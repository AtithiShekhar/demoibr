# agent/prompt.py
from typing import List, Dict

BASE_PROMPT_PREFIX = """
You are Fit-Med — a clinical medication safety and optimization assistant.
CRITICAL RULES (must be followed exactly):
1) Use ONLY the medication information returned by the tool. Do NOT invent doses, interactions, or other facts.
2) If a field is missing in the tool output, explicitly state: "Information not found in tool output."
3) Produce a structured clinical medication assessment with these sections:
   - Patient Details
   - Medication Assessments (one per med: Indication, Benefits specific to patient, Risks & interactions, Strength of evidence, Risk Minimisation Measures (RMM), Fit-Med Outcome, Recommendation)
   - Monitoring Protocol (table)
   - Summary table (Medication -> Recommendation)
   - Patient Education (short bullets)
4) Use clear headings and bulleted lists. Be concise but thorough.
"""

def build_agent_prompt(patient_details: Dict, medication_tool_outputs: List[Dict]) -> str:
    pat_lines = []
    for k, v in patient_details.items():
        pat_lines.append(f"{k}: {v}")
    pat_block = "\n".join(pat_lines)

    med_blocks = []
    for item in medication_tool_outputs:
        med_name = item.get("med_name")
        tool_output = item.get("tool_output")
        if tool_output is None:
            med_blocks.append(f"[MEDICATION: {med_name}] (source: dummy_tool)\nERROR: No tool output.\n")
            continue

        lines = [f"[MEDICATION: {med_name}] (source: dummy_tool)"]
        for field in ["indication", "benefits", "risks", "contraindications", "interactions", "risk_minimization_measures", "monitoring", "fit_med_outcome"]:
            value = tool_output.get(field)
            if value:
                if isinstance(value, list):
                    lines.append(f"{field.upper()}:")
                    for v in value:
                        lines.append(f"- {v}")
                else:
                    lines.append(f"{field.upper()}: {value}")
            else:
                lines.append(f"{field.upper()}: Information not found in tool output.")
        med_blocks.append("\n".join(lines))

    meds_text = "\n\n".join(med_blocks)

    prompt = f"{BASE_PROMPT_PREFIX}\n\nPATIENT_DETAILS:\n{pat_block}\n\nMEDICATION_TOOL_OUTPUTS:\n{meds_text}\n\nNow produce the final Fit-Med clinical medication assessment report using ONLY the tool outputs above."
    return prompt
