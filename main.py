
# main.py - COMPLETE REWRITE FOR JSON REPORT GENERATION
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from core.llm import GeminiLLM
from utils.db_query import ask_question
from utils.processpdfs import process_all_pdfs, list_available_medicines

def load_patient_input(input_path: str = "patient_input.json") -> dict:
    """Load patient data from JSON file."""
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_medication_contexts(medications: List[str], n_results: int = 5) -> Dict[str, str]:
    """
    Fetch ChromaDB context for each medication.
    
    Returns:
        Dict mapping medication names to their database context
    """
    contexts = {}
    
    for med in medications:
        print(f"🔍 Querying database for: {med}")
        
        # Build comprehensive query
        query = f"clinical information for {med} including indication, dosage, side effects, interactions, contraindications, monitoring requirements"
        
        # Query ChromaDB
        result = ask_question(query, n_results=n_results, specific_medicine=med)
        
        if result["found"]:
            contexts[med] = result["context_for_llm"]
            print(f"   ✅ Found {len(result['documents'])} relevant sources")
        else:
            contexts[med] = "No information found in database for this medication."
            print(f"   ❌ No information found")
    
    return contexts


def generate_fitmed_report(input_path: str = "patient_input.json", 
                           output_path: str = "fitmed_report.json") -> dict:
    """
    Main function to generate Fit-Med clinical assessment report.
    
    Args:
        input_path: Path to patient input JSON
        output_path: Path to save output JSON report
        
    Returns:
        dict: Generated report
    """
    print("\n" + "="*80)
    print("🏥  FIT-MED CLINICAL MEDICATION ASSESSMENT GENERATOR")
    print("="*80 + "\n")
    
    # Step 1: Load patient data
    print("📋 Step 1: Loading patient data...")
    try:
        patient_data = load_patient_input(input_path)
        print(f"   Patient: {patient_data['patient'].get('age')}yo {patient_data['patient'].get('gender')}")
        print(f"   Diagnosis: {patient_data['patient'].get('diagnosis')}")
        print(f"   Medications: {', '.join(patient_data['prescription'])}")
    except Exception as e:
        print(f"❌ Error loading patient data: {e}")
        return {}
    
    # Step 2: Query ChromaDB for each medication
    print("\n📚 Step 2: Querying medication database...")
    medications_context = fetch_medication_contexts(patient_data['prescription'])
    
    # Step 3: Initialize LLM
    print("\n🤖 Step 3: Initializing Gemini LLM...")
    llm = GeminiLLM(
        model_name="gemini-2.0-flash",
        temperature=0.1,  # Low temperature for consistent clinical output
        max_output_tokens=8192
    )
    
    # Step 4: Generate clinical assessment
    print("\n⚕️  Step 4: Generating clinical assessment...")
    print("   (This may take 30-60 seconds...)")
    
    report = llm.generate_clinical_json(patient_data, medications_context)
    
    if "error" in report:
        print(f"\n❌ Error generating report: {report['error']}")
        return report
    
    # Step 5: Save report
    print("\n💾 Step 5: Saving report...")
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Report saved to: {output_file.absolute()}")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 REPORT SUMMARY")
    print("="*80)
    print(f"Patient: {report['patient_details']['age']}yo {report['patient_details']['gender']}")
    print(f"Medications Assessed: {len(report['medication_assessments'])}")
    print("\nFit-Med Outcomes:")
    
    for assessment in report['medication_assessments']:
        outcome = assessment['fit_med_outcome']
        emoji = "✅" if outcome == "Favorable" else "⚠️" if outcome == "Conditional" else "❌"
        print(f"  {emoji} {assessment['medication']}: {outcome}")
    
    print("="*80 + "\n")
    
    return report


def interactive_qa_mode():
    """Interactive Q&A mode for quick medication queries."""
    print("\n" + "="*80)
    print("💬  INTERACTIVE Q&A MODE")
    print("="*80)
    print("\nAsk questions about medications (e.g., 'What is the dosage of metformin?')")
    print("Type 'report' to generate a full clinical assessment")
    print("Type 'exit' to quit\n")
    
    # Initialize
    llm = GeminiLLM(model_name="gemini-2.0-flash", temperature=0.2, max_output_tokens=2000)
    
    while True:
        try:
            user_input = input("💬 Question: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!\n")
                break
            
            if user_input.lower() == 'report':
                print("\n📋 Generating full clinical report...\n")
                generate_fitmed_report()
                continue
            
            # Query ChromaDB
            print("🔍 Searching database...")
            result = ask_question(user_input, n_results=3)
            
            if not result["found"]:
                print("❌ No relevant information found.\n")
                continue
            
            # Get LLM answer
            print("🤖 Generating answer...\n")
            answer = llm.answer_question(user_input, result["context_for_llm"])
            
            print("="*80)
            print("💡 ANSWER:")
            print("="*80)
            print(answer)
            print("="*80 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point."""
    # Process PDFs first
    print("🔧 Initializing system...")
    data_dir = Path("./data")
    if data_dir.exists():
        print("📂 Processing medication PDFs...")
        process_all_pdfs(str(data_dir))
        medicines = list_available_medicines()
        print(f"✅ Database ready with {len(medicines)} medications\n")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "qa":
            # Interactive Q&A mode
            interactive_qa_mode()
        elif command == "report":
            # Generate report mode
            input_file = sys.argv[2] if len(sys.argv) > 2 else "patient_input.json"
            output_file = sys.argv[3] if len(sys.argv) > 3 else "fitmed_report.json"
            generate_fitmed_report(input_file, output_file)
        else:
            print("Usage:")
            print("  python main.py report [input.json] [output.json]  - Generate clinical report")
            print("  python main.py qa                                  - Interactive Q&A mode")
    else:
        # Default: Generate report
        generate_fitmed_report()


if __name__ == "__main__":
    main()


# utils/db_query.py - KEEP AS IS, NO CHANGES NEEDED
# (Your existing implementation is fine)


# Example patient_input.json structure:
"""
{
  "patient": {
    "age": 65,
    "gender": "Male",
    "diagnosis": "Acute Myeloid Leukemia, s/p Stem Cell Transplant (Day +8)",
    "smoking_alcohol": "Not reported",
    "date_of_assessment": "2025-09-17"
  },
  "prescription": [
    "Meropenem",
    "Zavicefta",
    "Fluconazole",
    "Valacyclovir",
    "Cyclosporine"
  ],
  "notes": "Sample run. resource_pdf: /mnt/data/example.pdf"
}
"""