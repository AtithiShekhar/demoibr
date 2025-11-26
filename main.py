import pymupdf
import chromadb
from sentence_transformers import SentenceTransformer
import re
import os
from pathlib import Path

model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="pdf_docs")

def semantic_chunk(text, max_chunk_size=500):
    """Split text into semantic chunks based on sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence)
        if current_size + sentence_size > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_size = sentence_size
        else:
            current_chunk.append(sentence)
            current_size += sentence_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

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

def list_available_medicines():
    """List all medicines in the database."""
    all_data = collection.get()
    medicines = set(meta.get('medicine', '') for meta in all_data['metadatas'])
    return sorted([m for m in medicines if m])

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