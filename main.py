
# main.py - COMPLETE REWRITE FOR Q&A MODE
import sys
from pathlib import Path
from core.llm import GeminiLLM
from utils.db_query import ask_question, query_and_format
from utils.processpdfs import process_all_pdfs, list_available_medicines

def print_banner():
    """Print welcome banner."""
    print("\n" + "="*70)
    print("🏥  MEDICATION Q&A SYSTEM - Powered by ChromaDB + Gemini LLM")
    print("="*70)
    print("\n📚 This system can answer questions about medications using")
    print("   information from your PDF database.\n")
    print("💡 Example questions:")
    print("   • What is the dosage of metformin?")
    print("   • What are the side effects of atorvastatin?")
    print("   • Can I take aspirin with ibuprofen?")
    print("   • What should I monitor when taking warfarin?")
    print("\n" + "="*70 + "\n")


def print_help():
    """Print help information."""
    print("\n" + "="*70)
    print("📖 AVAILABLE COMMANDS:")
    print("="*70)
    print("  help     - Show this help message")
    print("  list     - List all available medicines in database")
    print("  clear    - Clear screen")
    print("  exit     - Exit the program (or use 'quit', 'q')")
    print("\n💬 Or simply ask any question about medications!")
    print("="*70 + "\n")


def process_user_question(question: str, llm: GeminiLLM, verbose: bool = True) -> dict:
    """
    Process a user question: query ChromaDB -> send to LLM -> return answer.
    
    Returns:
        dict with keys: question, context, answer, sources_found
    """
    # Step 1: Query ChromaDB
    if verbose:
        print("🔍 Searching database...")
    
    chromadb_results = ask_question(question, n_results=5)
    
    if not chromadb_results["found"]:
        return {
            "question": question,
            "context": "",
            "answer": "❌ I couldn't find any relevant information in the database for your question. Please try rephrasing or ask about a different medication.",
            "sources_found": False
        }
    
    context = chromadb_results["context_for_llm"]
    
    # Step 2: Show sources (optional)
    if verbose:
        print(f"✅ Found {len(chromadb_results['documents'])} relevant sources\n")
    
    # Step 3: Send to LLM
    if verbose:
        print("🤖 Generating answer with LLM...")
    
    answer = llm.answer_question(question, context)
    
    return {
        "question": question,
        "context": context,
        "answer": answer,
        "sources_found": True,
        "sources": chromadb_results["documents"],
        "metadatas": chromadb_results["metadatas"]
    }


def show_sources(result: dict):
    """Display source information."""
    if not result.get("sources_found") or not result.get("sources"):
        return
    
    print("\n" + "─"*70)
    print("📚 SOURCES USED:")
    print("─"*70)
    
    for i, (doc, meta) in enumerate(zip(result["sources"], result["metadatas"]), 1):
        medicine = meta.get("medicine", "Unknown")
        print(f"\n[{i}] Medicine: {medicine.upper()}")
        print(f"    Preview: {doc[:200]}...")
    
    print("─"*70 + "\n")


def interactive_mode():
    """Main interactive Q&A loop."""
    # Initialize
    print("🔧 Initializing system...")
    
    # Process PDFs
    data_dir = Path("./data")
    if data_dir.exists():
        print(f"📂 Processing PDFs from {data_dir}...")
        process_all_pdfs(str(data_dir))
    else:
        print(f"⚠️  Warning: Data directory not found at {data_dir}")
        print("   Please ensure your PDF files are in the ./data directory")
    
    # Initialize LLM
    llm = GeminiLLM(
        model_name="gemini-2.0-flash",
        temperature=0.2,
        max_output_tokens=2000
    )
    
    # Show available medicines
    try:
        medicines = list_available_medicines()
        print(f"\n✅ Database ready! Found {len(medicines)} medicines:")
        print(f"   {', '.join(sorted(medicines)[:10])}" + 
              (f" and {len(medicines)-10} more..." if len(medicines) > 10 else ""))
    except Exception as e:
        print(f"⚠️  Could not list medicines: {e}")
    
    print_banner()
    print_help()
    
    # Main loop
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("💬 Your question: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Thank you for using the Medication Q&A System. Goodbye!\n")
                break
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            if user_input.lower() == 'list':
                try:
                    medicines = list_available_medicines()
                    print(f"\n📋 Available medicines ({len(medicines)}):")
                    for i, med in enumerate(sorted(medicines), 1):
                        print(f"   {i}. {med}")
                    print()
                except Exception as e:
                    print(f"❌ Error listing medicines: {e}\n")
                continue
            
            if user_input.lower() == 'clear':
                print("\033[H\033[J", end="")  # Clear screen
                print_banner()
                continue
            
            # Process the question
            print()  # Blank line for readability
            result = process_user_question(user_input, llm, verbose=True)
            
            # Display answer
            print("\n" + "="*70)
            print("💡 ANSWER:")
            print("="*70)
            print(result["answer"])
            print("="*70 + "\n")
            
            # Optionally show sources
            show_sources_prompt = input("📚 Show source documents? (y/n): ").strip().lower()
            if show_sources_prompt == 'y':
                show_sources(result)
            
            # Save to history
            conversation_history.append(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()


def single_question_mode(question: str):
    """
    Process a single question non-interactively.
    Useful for API or batch processing.
    """
    print(f"Processing question: {question}\n")
    
    # Initialize
    process_all_pdfs("./data")
    llm = GeminiLLM(model_name="gemini-2.0-flash", temperature=0.2, max_output_tokens=2000)
    
    # Process question
    result = process_user_question(question, llm, verbose=True)
    
    # Display result
    print("\n" + "="*70)
    print("ANSWER:")
    print("="*70)
    print(result["answer"])
    print("="*70 + "\n")
    
    return result


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Single question mode
        question = " ".join(sys.argv[1:])
        single_question_mode(question)
    else:
        # Interactive mode
        interactive_mode()