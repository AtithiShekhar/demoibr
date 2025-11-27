
# utils/db_query.py - KEEP AS IS BUT ADD HELPER
from typing import Optional, Union, List
from utils.globals import model, collection
from utils.processpdfs import extract_medicine_filter

def ask_question(question: str, n_results: int = 5, specific_medicine: Optional[Union[str, List[str]]] = None) -> dict:
    """Query ChromaDB with optional medicine filtering and return structured results."""
    
    # Auto-detect medicine names in question
    if not specific_medicine:
        detected_medicines = extract_medicine_filter(question)
        if detected_medicines:
            print(f"🔍 [Auto-detected medicines: {', '.join(detected_medicines)}]")
            specific_medicine = detected_medicines
    
    query_embedding = model.encode([question]).tolist()
    where_filter = None
    
    if specific_medicine:
        if isinstance(specific_medicine, str):
            where_filter = {"medicine": specific_medicine.lower()}
        elif isinstance(specific_medicine, list):
            where_filter = {"medicine": {"$in": [m.lower() for m in specific_medicine]}}
    
    # Query ChromaDB
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter
    )
    
    if not results or not results.get('documents') or not results['documents'][0]:
        return {
            "documents": [],
            "metadatas": [],
            "distances": [],
            "context_for_llm": "No relevant documents found.",
            "found": False
        }
    
    # Format context for LLM
    formatted_context = ""
    
    for i, doc in enumerate(results['documents'][0]):
        meta = results['metadatas'][0][i]
        similarity = 1 - results['distances'][0][i]
        medicine = meta.get("medicine", "Unknown")
        
        formatted_context += (
            f"[Source {i+1}] Medicine: {medicine.upper()} (Relevance: {similarity:.2%})\n"
            f"{doc}\n"
            f"{'-'*80}\n\n"
        )
    
    return {
        "documents": results['documents'][0],
        "metadatas": results['metadatas'][0],
        "distances": results['distances'][0],
        "context_for_llm": formatted_context.strip(),
        "found": True
    }


def query_and_format(question: str, n_results: int = 5) -> str:
    """
    Helper function: Query ChromaDB and return formatted context.
    """
    results = ask_question(question, n_results=n_results)
    return results["context_for_llm"]
