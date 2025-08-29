#!/usr/bin/env python
"""
Test script to verify Bedrock Titan embeddings are working
Run this after migration to ensure everything is configured correctly
"""

import asyncio
import logging
import json
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_titan_embedding():
    """Test Bedrock Titan embedding generation"""
    
    try:
        # Initialize Bedrock client
        client = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1'
        )
        logger.info("✅ Bedrock client initialized")
        
        # Test text
        test_text = "This is a test of the Bedrock Titan embedding service. We want to verify that embeddings are generated correctly."
        
        # Test Titan v2 with 1024 dimensions
        logger.info("\n🔍 Testing Titan Embed Text v2 (1024 dimensions)...")
        
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
            logger.info(f"✅ Embedding generated successfully!")
            logger.info(f"   - Dimension: {len(embedding)}")
            logger.info(f"   - First 5 values: {embedding[:5]}")
            logger.info(f"   - Type: {type(embedding)}")
            
            # Test similarity calculation
            logger.info("\n🔍 Testing similarity calculation...")
            
            # Generate another embedding for comparison
            similar_text = "This is another test of Bedrock Titan embeddings to check similarity."
            request_body['inputText'] = similar_text
            
            response2 = client.invoke_model(
                modelId='amazon.titan-embed-text-v2:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )
            
            response_body2 = json.loads(response2['body'].read())
            embedding2 = response_body2['embedding']
            
            # Calculate cosine similarity
            import math
            dot_product = sum(x * y for x, y in zip(embedding, embedding2))
            magnitude_a = math.sqrt(sum(x * x for x in embedding))
            magnitude_b = math.sqrt(sum(x * x for x in embedding2))
            
            similarity = dot_product / (magnitude_a * magnitude_b) if magnitude_a and magnitude_b else 0
            
            logger.info(f"✅ Similarity between test texts: {similarity:.2%}")
            
            # Test with very different text
            different_text = "The weather is sunny today and birds are singing in the trees."
            request_body['inputText'] = different_text
            
            response3 = client.invoke_model(
                modelId='amazon.titan-embed-text-v2:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )
            
            response_body3 = json.loads(response3['body'].read())
            embedding3 = response_body3['embedding']
            
            dot_product = sum(x * y for x, y in zip(embedding, embedding3))
            magnitude_c = math.sqrt(sum(x * x for x in embedding3))
            
            similarity2 = dot_product / (magnitude_a * magnitude_c) if magnitude_a and magnitude_c else 0
            
            logger.info(f"✅ Similarity with unrelated text: {similarity2:.2%}")
            
            logger.info("\n🎉 All tests passed! Bedrock Titan embeddings are working correctly.")
            return True
            
        else:
            logger.error(f"❌ No embedding found in response: {response_body}")
            return False
            
    except ClientError as e:
        logger.error(f"❌ Bedrock API error: {e}")
        logger.info("\n📝 Troubleshooting tips:")
        logger.info("1. Check AWS credentials are configured")
        logger.info("2. Verify Bedrock is enabled in us-east-1 region")
        logger.info("3. Ensure you have access to Titan Embed models")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


async def test_embedding_service():
    """Test the embedding service wrapper"""
    try:
        from services.embedding_service import get_embedding_service
        
        logger.info("\n🔍 Testing embedding service wrapper...")
        
        service = get_embedding_service()
        
        # Test single embedding
        test_text = "Testing the embedding service wrapper"
        embedding = service.generate_embedding(test_text)
        
        if embedding:
            logger.info(f"✅ Single embedding generated: dimension {len(embedding)}")
        else:
            logger.error("❌ Failed to generate single embedding")
            return False
            
        # Test batch embeddings
        texts = [
            "First test document about refunds",
            "Second test document about shipping",
            "Third test document about customer service"
        ]
        
        embeddings = service.generate_embeddings_batch(texts)
        
        if embeddings and len(embeddings) == len(texts):
            logger.info(f"✅ Batch embeddings generated: {len(embeddings)} embeddings")
            for i, emb in enumerate(embeddings):
                if emb:
                    logger.info(f"   - Text {i+1}: dimension {len(emb)}")
        else:
            logger.error("❌ Failed to generate batch embeddings")
            return False
            
        # Test dimension detection
        dimension = service.get_embedding_dimension()
        logger.info(f"✅ Detected embedding dimension: {dimension}")
        
        # Test similarity calculation
        emb1 = embeddings[0]
        emb2 = embeddings[1]
        similarity = service.calculate_similarity(emb1, emb2)
        logger.info(f"✅ Similarity calculation works: {similarity:.2%}")
        
        logger.info("\n🎉 Embedding service wrapper is working correctly!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing embedding service: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("🚀 Starting Bedrock Titan embedding tests...\n")
    
    # Test direct Bedrock API
    if not await test_titan_embedding():
        logger.error("\n❌ Direct Bedrock API test failed")
        return
        
    # Test embedding service wrapper
    if not await test_embedding_service():
        logger.error("\n❌ Embedding service wrapper test failed")
        return
        
    logger.info("\n✨ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())