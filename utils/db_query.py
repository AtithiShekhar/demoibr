import numpy as np # Adding numpy import as model.encode suggests a dependency
from utils.globals import model, client, collection
from utils.processpdfs import extract_medicine_filter
# main ye function h jo question leke process krega aur chroma se fetch krega 
def ask_question(question, n_results=5, specific_medicine=None):
    """Query ChromaDB with optional medicine filtering."""
    
    # Auto-detect medicine names in question
    if not specific_medicine:
        # Note: If extract_medicine_filter also uses a circular dependency, 
        # that dependency will need to be resolved similarly.
        detected_medicines = extract_medicine_filter(question)
        if detected_medicines:
            print(f"[Filtering by: {', '.join(detected_medicines)}]")
            specific_medicine = detected_medicines
    
    # Ensure model.encode is available and correctly imported in this scope
    # Assuming 'model' is initialized in utils.globals and is a sentence transformer/embedder.
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
    formatted_context = ""
    
    # Assuming results structure is correct based on original main.py
    if results and results.get('documents') and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            # Calculate similarity based on distance (assuming normalized distances 0 to 1)
            similarity = 1 - results['distances'][0][i]
            medicine = meta.get("medicine", "Unknown").upper()

            formatted_context += (
                f"### Result {i+1}\n"
                f"Medicine: {medicine}\n"
                f"Similarity: {similarity:.4f}\n"
                f"Content:\n{doc}\n\n"
            )

        return {
            "documents": results['documents'][0],
            "metadatas": results['metadatas'][0],
            "distances": results['distances'][0],
            "context_for_llm": formatted_context.strip()
        }
    
    return {
        "documents": [],
        "metadatas": [],
        "distances": [],
        "context_for_llm": "No relevant documents found."
    }