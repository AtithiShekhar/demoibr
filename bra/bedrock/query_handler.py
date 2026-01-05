import json
import boto3

# Configuration
REGION = "ap-south-1"
KNOWLEDGE_BASE_ID = "R1JBPOUITW"
MODEL_ARN = "arn:aws:bedrock:ap-south-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"

class BedrockDrugChecker:
    def __init__(self):
        self.kb_client = boto3.client("bedrock-agent-runtime", region_name=REGION)
        self.runtime = boto3.client("bedrock-runtime", region_name=REGION)

    def retrieve_docs(self, drug: str, condition: str) -> str:
        query = f"Indications for {drug}. Is {condition} an indication?"
        try:
            response = self.kb_client.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5,
                        "filter": {"equals": {"key": "drug_name", "value": drug.lower().strip()}}
                    }
                }
            )
            results = response.get("retrievalResults", [])
            return "\n\n".join([r["content"]["text"] for r in results])
        except Exception:
            return ""

    def generate_answer(self, drug: str, condition: str, context: str) -> bool:
        if not context.strip():
            return False
            
        prompt = f"""Based on the following medical information about {drug}, determine if {condition} is a described indication.
        Context: {context}
        Answer ONLY with "Yes" or "No"."""

        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "temperature": 0,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            })
            response = self.runtime.invoke_model(modelId=MODEL_ARN, body=body)
            answer = json.loads(response.get("body").read())["content"][0]["text"].lower()
            return "yes" in answer
        except Exception:
            return False

def format_bedrock_output(approved: bool, drug: str, condition: str) -> str:
    result = "Yes" if approved else "No"
    return f"{condition} is described in {drug}?: {result}"