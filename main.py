from pathlib import Path
from utils.chunking import semantic_chunk
from utils.processpdfs import process_all_pdfs,extract_medicine_filter,list_available_medicines

from utils.globals import model, client, collection
def ask_question(question, n_results=5, specific_medicine=None):
    """Query ChromaDB with optional medicine filtering."""
    
    # Auto-detect medicine names in question
    if not specific_medicine:
        detected_medicines = extract_medicine_filter(question)
        if detected_medicines:
            print(f"[Filtering by: {', '.join(detected_medicines)}]")
            specific_medicine = detected_medicines
    
    query_embedding = model.encode([question]).tolist()
    where_filter = None
    if specific_medicine:
        if isinstance(specific_medicine, str):
            where_filter = {"medicine": specific_medicine.lower()}
        elif isinstance(specific_medicine, list):
            where_filter = {"medicine": {"$in": [m.lower() for m in specific_medicine]}}
    
    # Query with optional filter
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter
    )
    
    return {
        "documents": results['documents'][0],
        "metadatas": results['metadatas'][0],
        "distances": results['distances'][0]
    }

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
            response = ask_question(user_input)
            
            if not response['documents']:
                print("No relevant information found.\n")
                continue
            
            print("\n" + "-"*60)
            for i, doc in enumerate(response['documents']):
                medicine = response['metadatas'][i].get('medicine', 'Unknown')
                print(f"\n📄 Result {i+1} | Medicine: {medicine.upper()} | Similarity: {1 - response['distances'][i]:.4f}")
                print(f"Content: {doc}")
            print("-"*60 + "\n")
            
        except Exception as e:
            print(f"Error: {e}\n")