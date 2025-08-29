
# Working Bedrock Titan Embedding Configuration
# Region: us-east-2
# Model: amazon.titan-embed-text-v2:0
# Dimensions: 1024

import boto3
import json

def generate_embedding(text: str) -> list:
    """Generate embedding using Bedrock Titan"""
    client = boto3.client('bedrock-runtime', region_name='us-east-2')
    
    request_body = {
        "inputText": text[:8192]  # Titan limit
    }
    
    # Titan v2 supports dimension configuration
    request_body["dimensions"] = 1024
    request_body["normalize"] = True
    
    response = client.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

# Example usage:
# embedding = generate_embedding("Your text here")
# print(f"Generated {len(embedding)}-dimensional embedding")
