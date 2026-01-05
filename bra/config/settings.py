import boto3
REGION = "ap-south-1"
KNOWLEDGE_BASE_ID = "R1JBPOUITW"

MODEL_ARN = (
    "arn:aws:bedrock:ap-south-1::foundation-model/"
    "anthropic.claude-3-sonnet-20240229-v1:0"
)

MAX_RESULTS = 5
TEMPERATURE = 0.0
# Clients
kb_client = boto3.client("bedrock-agent-runtime", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)