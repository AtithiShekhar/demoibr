import pymupdf
import os
from utils.chunking import semantic_chunk
from utils.globals import model, client, collection
from pathlib import Path

def process_pdf(pdf_path):
    """Read PDF, convert to embeddings, and store in ChromaDB."""
    filename = os.path.basename(pdf_path)
    
    try:
        existing = collection.get(where={"source": pdf_path})
        if existing['ids']:
            print(f"✓ Already processed: {filename} ({len(existing['ids'])} chunks)")
            return
    except:
        pass
    
    doc = pymupdf.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    
    chunks = semantic_chunk(full_text)
    
    if not chunks:
        print(f"✗ No text extracted from {filename}")
        return
    
    embeddings = model.encode(chunks).tolist()
    medicine_name = Path(pdf_path).stem
    
    ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
    # setting the metadata of medicine in chroma db
    metadatas = [{
        "source": pdf_path,
        "filename": filename,
        "medicine": medicine_name.lower(),
        "chunk_id": i,
        "total_chunks": len(chunks)
    } for i in range(len(chunks))]
    
    collection.add(
        embeddings=embeddings,
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )
    
    print(f"✓ Processed: {filename} ({len(chunks)} chunks)")


def process_all_pdfs(directory="./data"):
    """Process all PDFs in a directory."""
    pdf_files = list(Path(directory).glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {directory}")
        return
    
    print(f"\nProcessing {len(pdf_files)} PDFs from {directory}...\n")
    
    for pdf_path in pdf_files:
        process_pdf(str(pdf_path))
    
    print(f"\n✓ All PDFs processed! Total items in DB: {collection.count()}")

def extract_medicine_filter(question):
    """Extract medicine names mentioned in the question."""
    # Get all unique medicine names from database
    all_data = collection.get()
    all_medicines = set(meta.get('medicine', '') for meta in all_data['metadatas'])
    
    # Check if any medicine name is mentioned in the question
    question_lower = question.lower()
    mentioned_medicines = [med for med in all_medicines if med and med in question_lower]
    
    return mentioned_medicines

def list_available_medicines():
    """List all medicines in the database."""
    all_data = collection.get()
    medicines = set(meta.get('medicine', '') for meta in all_data['metadatas'])
    return sorted([m for m in medicines if m])
