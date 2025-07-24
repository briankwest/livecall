from typing import List, Dict, Any, Optional, Tuple
import openai
import logging
from datetime import datetime, timedelta
from core.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.embedding_model = settings.embedding_model
        
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text using OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
            
    async def analyze_conversation_context(
        self,
        recent_transcriptions: List[Dict[str, Any]],
        window_minutes: int = 2
    ) -> Tuple[str, List[str]]:
        """Analyze recent conversation to extract context and key topics"""
        
        # Format transcriptions into conversation
        conversation = self._format_conversation(recent_transcriptions)
        
        if not conversation:
            return "", []
        
        prompt = f"""Analyze this customer service conversation and extract:
1. A brief summary of what the customer needs help with (1-2 sentences)
2. Key topics or entities mentioned (up to 5)

Conversation:
{conversation}

Response format:
Summary: <summary>
Topics: <topic1>, <topic2>, <topic3>
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing customer service calls."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            summary = ""
            topics = []
            
            for line in content.split('\n'):
                if line.startswith('Summary:'):
                    summary = line.replace('Summary:', '').strip()
                elif line.startswith('Topics:'):
                    topics_str = line.replace('Topics:', '').strip()
                    topics = [t.strip() for t in topics_str.split(',') if t.strip()]
                    
            return summary, topics
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return "", []
            
    async def generate_search_query(
        self,
        conversation_summary: str,
        key_topics: List[str]
    ) -> str:
        """Generate optimized search query for vector database"""
        
        if not conversation_summary and not key_topics:
            return ""
            
        prompt = f"""Based on this customer service context, generate a search query to find relevant documentation:

Summary: {conversation_summary}
Key Topics: {', '.join(key_topics)}

Generate a concise search query (max 100 words) that would help find relevant help documentation:"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a search query optimizer for customer service documentation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating search query: {e}")
            # Fallback to simple concatenation
            return f"{conversation_summary} {' '.join(key_topics)}"
            
    async def summarize_call(
        self,
        transcriptions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive call summary"""
        
        conversation = self._format_conversation(transcriptions)
        
        if not conversation:
            return {
                "summary": "No conversation to summarize",
                "key_topics": [],
                "action_items": [],
                "sentiment": "neutral"
            }
        
        prompt = f"""Analyze this complete customer service call and provide:
1. Executive summary (2-3 sentences)
2. Key topics discussed
3. Action items or follow-ups needed
4. Overall customer sentiment (positive/neutral/negative)

Conversation:
{conversation}

Response format:
Summary: <summary>
Topics: <topic1>, <topic2>, <topic3>
Action Items: <item1>; <item2>
Sentiment: <sentiment>
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at summarizing customer service calls."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            summary = ""
            topics = []
            action_items = []
            sentiment = "neutral"
            
            for line in content.split('\n'):
                if line.startswith('Summary:'):
                    summary = line.replace('Summary:', '').strip()
                elif line.startswith('Topics:'):
                    topics_str = line.replace('Topics:', '').strip()
                    topics = [t.strip() for t in topics_str.split(',') if t.strip()]
                elif line.startswith('Action Items:'):
                    items_str = line.replace('Action Items:', '').strip()
                    action_items = [i.strip() for i in items_str.split(';') if i.strip()]
                elif line.startswith('Sentiment:'):
                    sentiment = line.replace('Sentiment:', '').strip().lower()
                    
            # Calculate sentiment score
            sentiment_scores = {
                "positive": 0.8,
                "neutral": 0.5,
                "negative": 0.2
            }
            
            return {
                "summary": summary,
                "key_topics": topics,
                "action_items": action_items,
                "sentiment": sentiment,
                "sentiment_score": sentiment_scores.get(sentiment, 0.5)
            }
            
        except Exception as e:
            logger.error(f"Error summarizing call: {e}")
            return {
                "summary": "Error generating summary",
                "key_topics": [],
                "action_items": [],
                "sentiment": "neutral",
                "sentiment_score": 0.5
            }
            
    def _format_conversation(self, transcriptions: List[Dict[str, Any]]) -> str:
        """Format transcriptions into readable conversation"""
        if not transcriptions:
            return ""
            
        lines = []
        for trans in transcriptions:
            speaker = trans.get("speaker", "Unknown")
            text = trans.get("text", "")
            lines.append(f"{speaker.capitalize()}: {text}")
            
        return "\n".join(lines)