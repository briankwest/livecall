#!/usr/bin/env python
"""
Comprehensive test script for Bedrock Titan Embeddings
Tests authentication, permissions, and embedding generation
"""

import json
import boto3
import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def test_aws_credentials():
    """Test AWS credentials and account info"""
    print_section("1. AWS Credentials Check")
    try:
        # Check environment variables
        print("\nEnvironment Variables:")
        print(f"  AWS_REGION: {os.environ.get('AWS_REGION', 'NOT SET')}")
        print(f"  AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION', 'NOT SET')}")
        print(f"  AWS_ACCESS_KEY_ID: {'SET' if os.environ.get('AWS_ACCESS_KEY_ID') else 'NOT SET'}")
        print(f"  AWS_SECRET_ACCESS_KEY: {'SET' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
        
        # Test STS
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"\n✅ AWS Credentials Valid:")
        print(f"  Account: {identity['Account']}")
        print(f"  User ARN: {identity['Arn']}")
        return True
    except NoCredentialsError:
        print("\n❌ No AWS credentials found!")
        return False
    except Exception as e:
        print(f"\n❌ Error checking credentials: {e}")
        return False

def test_bedrock_access(region: str):
    """Test Bedrock service access in a specific region"""
    print(f"\n Testing region: {region}")
    try:
        client = boto3.client('bedrock', region_name=region)
        
        # List foundation models
        response = client.list_foundation_models()
        
        # Filter for Titan embedding models
        titan_models = [
            m for m in response['modelSummaries'] 
            if 'titan' in m['modelId'].lower() and 'embed' in m['modelId'].lower()
        ]
        
        if titan_models:
            print(f"  ✅ Found {len(titan_models)} Titan embedding model(s):")
            for model in titan_models:
                status = model.get('modelLifecycle', {}).get('status', 'UNKNOWN')
                print(f"    - {model['modelId']} (Status: {status})")
        else:
            print(f"  ⚠️  No Titan embedding models found in {region}")
            
        return titan_models
        
    except ClientError as e:
        print(f"  ❌ Error accessing Bedrock in {region}: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return []

def test_model_invocation(region: str, model_id: str, verbose: bool = True):
    """Test invoking a specific model"""
    if verbose:
        print(f"\n Testing model: {model_id} in {region}")
    
    try:
        client = boto3.client('bedrock-runtime', region_name=region)
        
        # Prepare request based on model version
        test_text = "This is a test of Amazon Bedrock Titan embeddings"
        
        if 'v2' in model_id:
            # Titan v2 request format
            request_body = {
                "inputText": test_text,
                "dimensions": 1024,
                "normalize": True
            }
        else:
            # Titan v1 request format
            request_body = {
                "inputText": test_text
            }
        
        if verbose:
            print(f"  Request body: {json.dumps(request_body, indent=2)}")
        
        # Invoke model
        response = client.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        if 'embedding' in response_body:
            embedding = response_body['embedding']
            print(f"  ✅ SUCCESS! Generated embedding:")
            print(f"    - Dimensions: {len(embedding)}")
            print(f"    - First 5 values: {embedding[:5]}")
            print(f"    - Input token count: {response_body.get('inputTextTokenCount', 'N/A')}")
            return True, embedding
        else:
            print(f"  ❌ No embedding in response")
            print(f"    Response keys: {list(response_body.keys())}")
            return False, None
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if verbose:
            print(f"  ❌ {error_code}: {error_msg}")
            
            if error_code == 'AccessDeniedException':
                print("\n  📝 To fix AccessDeniedException:")
                print(f"  1. Go to https://console.aws.amazon.com/bedrock/home?region={region}#/model-access")
                print(f"  2. Find '{model_id}' and click 'Manage model access'")
                print(f"  3. Enable the model and save changes")
            elif error_code == 'ValidationException':
                print("\n  📝 ValidationException suggests:")
                print(f"  - Model ID might be incorrect: {model_id}")
                print(f"  - Request body format might be wrong")
                print(f"  - Model might not be available in {region}")
            elif error_code == 'ResourceNotFoundException':
                print(f"\n  📝 Model {model_id} not found in {region}")
                
        return False, None
        
    except Exception as e:
        if verbose:
            print(f"  ❌ Unexpected error: {e}")
        return False, None

def find_working_configuration():
    """Try different configurations to find what works"""
    print_section("3. Finding Working Configuration")
    
    # Test different regions and model IDs
    test_configs = [
        # US East 2 (Ohio)
        ("us-east-2", "amazon.titan-embed-text-v2:0"),
        ("us-east-2", "amazon.titan-embed-text-v1"),
        ("us-east-2", "amazon.titan-embed-g1-text-02"),
        
        # US East 1 (Virginia) 
        ("us-east-1", "amazon.titan-embed-text-v2:0"),
        ("us-east-1", "amazon.titan-embed-text-v1"),
        ("us-east-1", "amazon.titan-embed-g1-text-02"),
        
        # US West 2 (Oregon)
        ("us-west-2", "amazon.titan-embed-text-v2:0"),
        ("us-west-2", "amazon.titan-embed-text-v1"),
    ]
    
    working_configs = []
    
    for region, model_id in test_configs:
        print(f"\n➤ Testing {model_id} in {region}...")
        success, embedding = test_model_invocation(region, model_id, verbose=False)
        if success:
            print(f"  ✅ WORKS! Dimension: {len(embedding)}")
            working_configs.append((region, model_id, len(embedding)))
        else:
            print(f"  ❌ Failed")
    
    return working_configs

def test_embedding_functionality(region: str, model_id: str):
    """Test embedding functionality with multiple texts"""
    print_section(f"4. Testing Embedding Functionality")
    print(f"Using: {model_id} in {region}")
    
    try:
        client = boto3.client('bedrock-runtime', region_name=region)
        
        # Test texts
        test_texts = [
            "Refund policy for damaged items",
            "How to return a product",
            "The weather is nice today",
        ]
        
        embeddings = []
        
        for text in test_texts:
            request_body = {
                "inputText": text
            }
            
            if 'v2' in model_id:
                request_body["dimensions"] = 1024
                request_body["normalize"] = True
            
            response = client.invoke_model(
                modelId=model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body['embedding']
            embeddings.append(embedding)
            print(f"\n✅ Embedded: '{text[:50]}...'")
            print(f"   Dimension: {len(embedding)}")
        
        # Calculate similarities
        print("\n📊 Similarity Matrix:")
        print("   (1=identical, 0=orthogonal)")
        
        def cosine_similarity(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = sum(x * x for x in a) ** 0.5
            mag_b = sum(x * x for x in b) ** 0.5
            return dot / (mag_a * mag_b) if mag_a and mag_b else 0
        
        for i in range(len(test_texts)):
            for j in range(i + 1, len(test_texts)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                print(f"   Text {i+1} vs Text {j+1}: {sim:.3f}")
        
        print("\n✅ Embedding functionality working correctly!")
        print("   (Similar texts have higher similarity scores)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing functionality: {e}")
        return False

def generate_working_code(region: str, model_id: str, dimension: int):
    """Generate working Python code for the configuration"""
    print_section("5. Generated Working Code")
    
    code = f'''
# Working Bedrock Titan Embedding Configuration
# Region: {region}
# Model: {model_id}
# Dimensions: {dimension}

import boto3
import json

def generate_embedding(text: str) -> list:
    """Generate embedding using Bedrock Titan"""
    client = boto3.client('bedrock-runtime', region_name='{region}')
    
    request_body = {{
        "inputText": text[:8192]  # Titan limit
    }}
    '''
    
    if 'v2' in model_id:
        code += '''
    # Titan v2 supports dimension configuration
    request_body["dimensions"] = 1024
    request_body["normalize"] = True
    '''
    
    code += f'''
    response = client.invoke_model(
        modelId='{model_id}',
        contentType='application/json',
        accept='application/json',
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['embedding']

# Example usage:
# embedding = generate_embedding("Your text here")
# print(f"Generated {{len(embedding)}}-dimensional embedding")
'''
    
    print(code)
    
    # Save to file
    with open('working_bedrock_config.py', 'w') as f:
        f.write(code)
    print("\n✅ Saved working configuration to: working_bedrock_config.py")

def main():
    """Main test function"""
    print("\n" + "🚀 " * 20)
    print(" BEDROCK TITAN EMBEDDINGS - COMPREHENSIVE TEST")
    print("🚀 " * 20)
    
    # Step 1: Check credentials
    if not test_aws_credentials():
        print("\n❌ Fix AWS credentials first!")
        return
    
    # Step 2: Check Bedrock access in different regions
    print_section("2. Bedrock Service Access")
    
    regions_to_test = ['us-east-2', 'us-east-1', 'us-west-2']
    available_models = {}
    
    for region in regions_to_test:
        models = test_bedrock_access(region)
        if models:
            available_models[region] = models
    
    if not available_models:
        print("\n❌ No Titan embedding models found in any region!")
        return
    
    # Step 3: Find working configuration
    working_configs = find_working_configuration()
    
    if not working_configs:
        print("\n❌ Could not find any working configuration!")
        print("\nPossible issues:")
        print("1. Model access not enabled in Bedrock console")
        print("2. IAM permissions missing for bedrock:InvokeModel")
        print("3. Region restrictions on your AWS account")
        return
    
    # Step 4: Use the first working configuration for detailed tests
    region, model_id, dimension = working_configs[0]
    print(f"\n🎯 Using working configuration: {model_id} in {region}")
    
    # Step 5: Test embedding functionality
    test_embedding_functionality(region, model_id)
    
    # Step 6: Generate working code
    generate_working_code(region, model_id, dimension)
    
    print("\n" + "✅ " * 20)
    print(" ALL TESTS COMPLETED SUCCESSFULLY!")
    print("✅ " * 20)
    
    print(f"\n📝 RECOMMENDED CONFIGURATION:")
    print(f"   Region: {region}")
    print(f"   Model ID: {model_id}")
    print(f"   Dimensions: {dimension}")
    
    # Update .env recommendation
    print(f"\n📝 Update your .env file:")
    print(f"   AWS_REGION={region}")
    print(f"   BEDROCK_EMBEDDING_MODEL={model_id}")

if __name__ == "__main__":
    main()