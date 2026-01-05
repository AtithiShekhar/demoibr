import json
from config import kb_client, bedrock_runtime, KNOWLEDGE_BASE_ID, MODEL_ARN

def retrieve_docs(query_text: str, drug_name: str) -> str:
    search_term = drug_name.lower().strip()
    try:
        response = kb_client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query_text},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                    "filter": {"equals": {"key": "drug_name", "value": search_term}}
                }
            }
        )
        results = response.get("retrievalResults", [])
        return "\n\n".join([r["content"]["text"] for r in results]) if results else ""
    except Exception:
        return ""

def generate_answer(prompt: str) -> str:
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        })
        response = bedrock_runtime.invoke_model(modelId=MODEL_ARN, body=body)
        response_body = json.loads(response.get("body").read())
        return response_body["content"][0]["text"].strip()
    except Exception:
        return ""

def process_drug_query(drug: str, condition: str) -> str:
    """The core logic to be called by other scripts"""
    query = f"Indications for {drug}. Is {condition} an indication?"
    retrieved_text = retrieve_docs(query, drug)
    
    if not retrieved_text:
        return f"{condition} is described in {drug}?: No"
    
    prompt = f"Context: {retrieved_text}\n\nQuestion: Is {condition} an indication for {drug}?\nAnswer ONLY 'Yes' or 'No'."
    answer = generate_answer(prompt)
    
    result = "Yes" if "yes" in answer.lower() else "No"
    return f"{condition} is described in {drug}?: {result}"