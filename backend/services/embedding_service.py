from typing import List, Dict, Any, Optional
import logging
import json
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Embedding service using AWS Bedrock Titan Embeddings"""
    
    def __init__(self, model_id: str = 'amazon.titan-embed-text-v2:0'):
        """
        Initialize embedding service with Bedrock Titan
        
        Args:
            model_id: Bedrock Titan embedding model ID
                     Options: 
                     - amazon.titan-embed-text-v1 (1536 dimensions)
                     - amazon.titan-embed-text-v2:0 (1024 dimensions)
        """
        self.model_id = model_id
        self.client = None
        self._dimension = None
        
    def _get_client(self):
        """Get or create Bedrock client"""
        if self.client is None:
            try:
                # Use us-east-1 for Titan embeddings (verified working)
                self.client = boto3.client(
                    'bedrock-runtime',
                    region_name='us-east-1'
                )
                logger.info(f"Initialized Bedrock client for embeddings with model: {self.model_id} in us-east-1")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
                raise
        return self.client
        
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using Bedrock Titan
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []
            
        try:
            client = self._get_client()
            
            # Prepare request body for Titan
            request_body = {
                "inputText": text[:8192]  # Titan has 8192 token limit
            }
            
            if 'v2' in self.model_id:
                # v2 supports dimension configuration
                request_body["dimensions"] = 1024  # Using 1024D for v2
                request_body["normalize"] = True
            # v1 doesn't support dimension configuration, always returns 1536D
            
            # Call Bedrock
            response = client.invoke_model(
                modelId=self.model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract embedding from response
            if 'embedding' in response_body:
                embedding = response_body['embedding']
            else:
                raise ValueError(f"No embedding found in response: {response_body}")
            
            # Cache dimension
            if self._dimension is None:
                self._dimension = len(embedding)
                logger.info(f"Detected embedding dimension: {self._dimension}")
            
            return embedding
            
        except ClientError as e:
            logger.error(f"Bedrock API error generating embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
            
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts
        Note: Titan doesn't support batch processing, so we iterate
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        # Filter out empty texts
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            logger.warning("No valid texts provided for embedding")
            return []
            
        results = []
        for i, text in enumerate(valid_texts):
            try:
                embedding = self.generate_embedding(text)
                results.append(embedding)
                if (i + 1) % 10 == 0:
                    logger.info(f"Generated {i + 1}/{len(valid_texts)} embeddings")
            except Exception as e:
                logger.error(f"Error generating embedding for text {i}: {e}")
                # Return empty embedding to maintain list alignment
                results.append([])
                
        return results
            
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors
        
        Returns:
            Integer representing the embedding dimension
        """
        if self._dimension is not None:
            return self._dimension
            
        # Generate a test embedding to determine dimension
        try:
            test_embedding = self.generate_embedding("test")
            self._dimension = len(test_embedding)
            return self._dimension
        except Exception as e:
            logger.error(f"Error determining embedding dimension: {e}")
            # Default dimensions based on model
            if 'v1' in self.model_id:
                return 1536
            else:  # v2
                return 1024
            
    def preprocess_text(self, text: str) -> str:
        """
        Basic text preprocessing for better embeddings
        
        Args:
            text: Raw text
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
            
        # Basic cleaning
        text = text.strip()
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Truncate to Titan's limit (approximately 8192 tokens)
        # Using character limit as approximation
        if len(text) > 30000:
            text = text[:30000] + "..."
            
        return text
        
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            import math
            
            # Calculate dot product
            dot_product = sum(x * y for x, y in zip(embedding1, embedding2))
            
            # Calculate magnitudes
            magnitude_a = math.sqrt(sum(x * x for x in embedding1))
            magnitude_b = math.sqrt(sum(x * x for x in embedding2))
            
            # Avoid division by zero
            if magnitude_a == 0 or magnitude_b == 0:
                return 0.0
                
            # Calculate cosine similarity
            similarity = dot_product / (magnitude_a * magnitude_b)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

# Singleton instance
embedding_service = None

def get_embedding_service():
    """Get the singleton embedding service instance"""
    global embedding_service
    if embedding_service is None:
        # Using Titan v2 with 1024 dimensions (available in us-east-2)
        embedding_service = EmbeddingService(model_id='amazon.titan-embed-text-v2:0')
    return embedding_service