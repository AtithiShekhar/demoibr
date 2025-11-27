from typing import Any, Dict

def extract_medication_info(chromadb_context: str, question: str) -> str:
    """
    Simple tool that formats ChromaDB context for LLM consumption.
    """
    if not chromadb_context or chromadb_context == "No relevant documents found.":
        return "No relevant information found in the database."
    
    return f"""Question: {question}

Retrieved Information from Database:
{chromadb_context}

Please answer the question based ONLY on the information provided above."""