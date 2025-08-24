from typing import List, Dict, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Embedding service using Sentence Transformers (based on SignalWire Agents approach)"""
    
    def __init__(self, model_name: str = 'sentence-transformers/all-mpnet-base-v2'):
        """
        Initialize embedding service with Sentence Transformers
        
        Args:
            model_name: Name of the Sentence Transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
        
    def _load_model(self):
        """Load the Sentence Transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded embedding model: {self.model_name}")
        except ImportError:
            logger.error(
                "sentence-transformers not available. Install with: "
                "pip install sentence-transformers"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading embedding model {self.model_name}: {e}")
            raise
            
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using Sentence Transformers
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
            
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []
            
        try:
            # Generate embedding
            embedding = self.model.encode(text, show_progress_bar=False)
            
            # Convert numpy array to list
            if hasattr(embedding, 'tolist'):
                return embedding.tolist()
            else:
                return embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding)
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
            
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts (batch processing)
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
            
        if not texts:
            return []
            
        # Filter out empty texts
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            logger.warning("No valid texts provided for embedding")
            return []
            
        try:
            # Generate embeddings in batch
            embeddings = self.model.encode(valid_texts, show_progress_bar=False)
            
            # Convert to list of lists
            result = []
            for embedding in embeddings:
                if hasattr(embedding, 'tolist'):
                    result.append(embedding.tolist())
                else:
                    result.append(embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding))
                    
            return result
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
            
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors
        
        Returns:
            Integer representing the embedding dimension
        """
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
            
        # Get dimension from model
        if hasattr(self.model, 'get_sentence_embedding_dimension'):
            return self.model.get_sentence_embedding_dimension()
        elif hasattr(self.model, 'encode'):
            # Fallback: encode a dummy text to get dimension
            dummy_embedding = self.model.encode("test", show_progress_bar=False)
            return len(dummy_embedding)
        else:
            logger.warning("Cannot determine embedding dimension, defaulting to 768")
            return 768
            
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
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Convert to numpy arrays
            emb1 = np.array(embedding1).reshape(1, -1)
            emb2 = np.array(embedding2).reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
            
        except ImportError:
            logger.error("scikit-learn not available for similarity calculation")
            # Fallback to manual cosine similarity
            return self._manual_cosine_similarity(embedding1, embedding2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
            
    def _manual_cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Manual cosine similarity calculation without scikit-learn
        
        Args:
            a: First embedding vector
            b: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        try:
            import math
            
            # Calculate dot product
            dot_product = sum(x * y for x, y in zip(a, b))
            
            # Calculate magnitudes
            magnitude_a = math.sqrt(sum(x * x for x in a))
            magnitude_b = math.sqrt(sum(x * x for x in b))
            
            # Avoid division by zero
            if magnitude_a == 0 or magnitude_b == 0:
                return 0.0
                
            # Calculate cosine similarity
            similarity = dot_product / (magnitude_a * magnitude_b)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error in manual cosine similarity calculation: {e}")
            return 0.0

# Singleton instance - initialized lazily to avoid import errors
embedding_service = None

def get_embedding_service():
    """Get the singleton embedding service instance"""
    global embedding_service
    if embedding_service is None:
        embedding_service = EmbeddingService()
    return embedding_service