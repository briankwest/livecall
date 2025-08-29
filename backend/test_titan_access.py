#!/usr/bin/env python
"""
Test script to verify access to Bedrock Titan embeddings in us-east-2
"""

import boto3
import json
from botocore.exceptions import ClientError

def test_titan_access():
    print("=" * 60)
    print("Testing Bedrock Titan Embedding Access in us-east-2")
    print("=" * 60)
    
    # Test us-east-2 region
    print("\n1. Testing us-east-2 region...")
    try:
        client = boto3.client('bedrock-runtime', region_name='us-east-2')
        print("   ✓ Connected to Bedrock in us-east-2")
        
        # Test Titan v2
        print("\n2. Testing Titan Embed Text v2:0...")
        test_text = "This is a test of Titan embeddings"
        
        request_body = {
            "inputText": test_text,
            "dimensions": 1024,
            "normalize": True
        }
        
        response = client.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        if 'embedding' in response_body:
            embedding = response_body['embedding']
            print(f"   ✓ SUCCESS! Generated embedding with {len(embedding)} dimensions")
            print(f"   First 5 values: {embedding[:5]}")
        else:
            print(f"   ✗ No embedding in response: {response_body}")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"   ✗ FAILED: {error_code}: {error_msg}")
        
        if error_code == 'AccessDeniedException':
            print("\n   📝 To fix this:")
            print("   1. Go to AWS Bedrock console in us-east-2")
            print("   2. Navigate to Model Access")
            print("   3. Request access to 'Titan Text Embeddings V2'")
            print("   4. Wait for approval (usually instant)")
            
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
    
    # List available models in us-east-2
    print("\n3. Listing available models in us-east-2...")
    try:
        client = boto3.client('bedrock', region_name='us-east-2')
        response = client.list_foundation_models()
        
        print("   Embedding models available:")
        embed_models = []
        for model in response['modelSummaries']:
            if 'embed' in model['modelId'].lower():
                status = model.get('modelLifecycle', {}).get('status', 'UNKNOWN')
                embed_models.append(model['modelId'])
                print(f"   - {model['modelId']} (status: {status})")
        
        if not embed_models:
            print("   - No embedding models found")
            
    except Exception as e:
        print(f"   ✗ Error listing models: {e}")
    
    # Check AWS credentials
    print("\n4. Checking AWS credentials...")
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"   ✓ Using AWS Account: {identity['Account']}")
        print(f"   ✓ ARN: {identity['Arn']}")
    except Exception as e:
        print(f"   ✗ Error checking credentials: {e}")

if __name__ == "__main__":
    test_titan_access()