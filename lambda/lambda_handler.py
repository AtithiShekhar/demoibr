import os
import json
import boto3
import requests
from sentence_transformers import SentenceTransformer

# -------------------------------
# Global Initialization (cold start)
# -------------------------------

CHROMA_HOST = os.environ.get("CHROMA_HOST")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
CHROMA_URL = f"http://{CHROMA_HOST}:{CHROMA_PORT}"

# S3 client
s3 = boto3.client("s3")

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2", cache_folder="/opt/ml/model")


# -------------------------------
# Chroma HTTP API Helpers
# -------------------------------
def get_or_create_collection(name):
    """Get or create collection using Chroma's HTTP API"""
    # Try to get existing collection
    try:
        response = requests.get(f"{CHROMA_URL}/api/v1/collections/{name}")
        if response.status_code == 200:
            print(f"Found existing collection: {name}")
            return response.json()
    except Exception as e:
        print(f"Collection doesn't exist yet: {e}")
    
    # Create new collection if it doesn't exist
    try:
        response = requests.post(
            f"{CHROMA_URL}/api/v1/collections",
            json={
                "name": name,
                "metadata": {"hnsw:space": "cosine"}
            }
        )
        
        if response.status_code in [200, 201]:
            print(f"Created new collection: {name}")
            return response.json()
        elif response.status_code == 409:  # Already exists (race condition)
            response = requests.get(f"{CHROMA_URL}/api/v1/collections/{name}")
            return response.json()
        else:
            raise Exception(f"Failed to create collection: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"Error creating collection: {str(e)}")


def add_embeddings(collection_id, ids, embeddings, documents):
    """Add embeddings to collection"""
    try:
        response = requests.post(
            f"{CHROMA_URL}/api/v1/collections/{collection_id}/add",
            json={
                "ids": ids,
                "embeddings": embeddings,
                "documents": documents
            }
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to add embeddings: {response.status_code} - {response.text}")
        
        print(f"Successfully added {len(ids)} embeddings to collection")
        return response.json()
    except Exception as e:
        raise Exception(f"Error adding embeddings: {str(e)}")


# -------------------------------
# Helper: extract text
# -------------------------------
def extract_text(file_bytes, key):
    """Return extracted string text from files."""
    if key.lower().endswith(".pdf"):
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except:
            return file_bytes.decode("latin-1", errors="ignore")

    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except:
        return file_bytes.decode("latin-1", errors="ignore")


# -------------------------------
# Helper: embed text
# -------------------------------
def generate_embedding(text: str):
    """Return vector embedding list."""
    return model.encode(text).tolist()


# -------------------------------
# Main Lambda Handler
# -------------------------------
def handler(event, context):
    try:
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        print(f"Processing file: s3://{bucket}/{key}")
        print(f"Chroma URL: {CHROMA_URL}")

        # Download file from S3
        obj = s3.get_object(Bucket=bucket, Key=key)
        file_bytes = obj["Body"].read()
        print(f"Downloaded {len(file_bytes)} bytes from S3")

        # Extract text
        text = extract_text(file_bytes, key)
        print(f"Extracted {len(text)} characters of text")
        
        # Truncate if needed
        max_text_length = 50000
        if len(text) > max_text_length:
            text = text[:max_text_length]
            print(f"Text truncated to {max_text_length} characters")

        # Generate embedding
        print("Generating embedding...")
        embedding = generate_embedding(text)
        print(f"Generated embedding with {len(embedding)} dimensions")

        # Get or create collection
        print("Getting/creating collection...")
        collection = get_or_create_collection("my_collection")
        collection_id = collection.get("id") or collection.get("name")
        
        # Add to Chroma (on your Fargate instance)
        print(f"Adding to Chroma collection {collection_id}...")
        add_embeddings(
            collection_id,
            [key],
            [embedding],
            [text]
        )

        print(f"Successfully processed: {key}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "bucket": bucket,
                "key": key,
                "message": "File processed and embedded into Chroma"
            })
        }
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": str(e),
                "trace": traceback.format_exc()
            })
        }
