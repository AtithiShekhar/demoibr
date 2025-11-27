import json
from pathlib import Path
from datetime import datetime
from agent.agent_builder import build_agent
from agent.tools import med_info_tool
from agent.prompt import build_agent_prompt
from core.llm import GeminiLLM
from utils.chunking import semantic_chunk
from utils.processpdfs import process_all_pdfs,extract_medicine_filter,list_available_medicines

from utils.db_query import ask_question
def fetch_med_tool_outputs(context_for_llm, prescription_list):
    outputs = []
    for med in prescription_list:
        tool_output = med_info_tool(context_for_llm, med)
        outputs.append({
            "med_name": med,
            "tool_output": tool_output
        })
    return outputs

def run_agent(context_for_llm:str, input_path: str = "sample_input.json", out_path: str = "generated_report.txt"):
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

    med_tool_outputs = fetch_med_tool_outputs(context_for_llm, prescription)

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
    # Process all PDFs in data directory
    process_all_pdfs("./data")
    
    # Show available medicines
    medicines = list_available_medicines()
    print(f"\n📋 Available medicines: {', '.join(medicines)}")
    
    print("\n" + "="*60)
    print("Ask questions! Tips:")
    print("  • Mention medicine name to filter (e.g., 'Atorvastatin side effects')")
    print("  • Ask general questions to search all PDFs")
    print("  • Type 'list' to see all medicines")
    print("  • Type 'exit' to quit")
    print("="*60 + "\n")
    
    while True:
        user_input = input("Question: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("Goodbye!")
            break
        
        if user_input.lower() == 'list':
            print(f"\n📋 Available medicines: {', '.join(list_available_medicines())}\n")
            continue
        
        try:
            whole_response = ask_question(user_input)
            run_agent(whole_response["context_for_llm"])
            if not whole_response['documents']:
                print("No relevant information found.\n")
                continue
            
            print("\n" + "-"*60)
            for i, doc in enumerate(whole_response['documents']):
                medicine = whole_response['metadatas'][i].get('medicine', 'Unknown')
                print(f"\n📄 Result {i+1} | Medicine: {medicine.upper()} | Similarity: {1 - whole_response['distances'][i]:.4f}")
                print(f"Content: {doc}")
            print("-"*60 + "\n")
            
        except Exception as e:
            print(f"Error: {e}\n")