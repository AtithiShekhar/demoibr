import json
from pathlib import Path
from datetime import datetime
from agent.agent_builder import build_agent
from agent.tools import med_info_tool
from agent.prompt import build_agent_prompt
from core.llm import GeminiLLM

def fetch_med_tool_outputs(prescription_list):
    outputs = []
    for med in prescription_list:
        tool_output = med_info_tool(med)
        outputs.append({
            "med_name": med,
            "tool_output": tool_output
        })
    return outputs

def run_agent(input_path: str = "sample_input.json", out_path: str = "generated_report.txt"):
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input JSON not found: {input_file.resolve()}")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    patient = data.get("patient", {})
    prescription = data.get("prescription", [])
    notes = data.get("notes", "")

    agent = build_agent()
    llm = GeminiLLM(model_name="gemini-2.0-flash", temperature=0.2, max_output_tokens=3000)

    med_tool_outputs = fetch_med_tool_outputs(prescription)

    #  prompt
    patient_details = {
        **patient,
        "run_datetime": datetime.utcnow().isoformat() + "Z",
        "notes": notes
    }
    prompt = build_agent_prompt(patient_details, med_tool_outputs)

    print("[debug] Sending prompt to Gemini (this may take a few seconds)...")
    report_text = llm._call(prompt)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Report generated and saved to: {out_path}")
    print("\n--- Report Preview ---\n")
    print(report_text[:2000])

if __name__ == "__main__":
    run_agent()
