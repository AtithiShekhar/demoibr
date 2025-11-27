from sentence_transformers import SentenceTransformer
import chromadb

# Shared global objects
model = SentenceTransformer('all-MiniLM-L6-v2')

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(name="pdf_docs")