from typing import List, Dict, Any, Optional, Tuple
import boto3
import json
import logging
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, BotoCoreError
from core.config import settings

logger = logging.getLogger(__name__)


class BedrockService:
    def __init__(self):
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.aws_region or 'us-east-1'
        )
        self.model_id = "amazon.nova-micro-v1:0"
        
    def _call_bedrock(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Internal method to call Bedrock Nova Micro"""
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": 0.9
                }
            )
            
            return response['output']['message']['content'][0]['text']
            
        except ClientError as e:
            logger.error(f"Bedrock ClientError: {e}")
            return None
        except Exception as e:
            logger.error(f"Bedrock error: {e}")
            return None
            
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
        
        prompt = f"""Analyze this customer service conversation and extract information that would be useful for searching documentation:

1. What is the customer's main issue or question? (Be specific)
2. What product features, services, or processes are being discussed?
3. Are there any error messages, specific problems, or technical terms mentioned?
4. What action is the customer trying to perform?

Conversation:
{conversation}

Response format:
Summary: <specific description of the customer's issue>
Topics: <relevant search terms, product names, features, error messages, etc>"""
        
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        try:
            content = self._call_bedrock(messages, temperature=0.3, max_tokens=200)
            
            if not content:
                return "", []
            
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
            
        prompt = f"""You are searching a knowledge base to help a customer service agent. Based on this context, generate the BEST search query to find relevant documentation.

Customer Issue: {conversation_summary}
Key Topics: {', '.join(key_topics)}

Generate a search query that would match relevant help articles, policies, or troubleshooting guides. Focus on:
- The specific problem or question
- Product/feature names
- Error messages or symptoms
- Actions the customer is trying to perform

Search query (be specific but concise):"""
        
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        try:
            content = self._call_bedrock(messages, temperature=0.3, max_tokens=100)
            
            if content:
                return content.strip()
            else:
                # Fallback to simple concatenation
                return f"{conversation_summary} {' '.join(key_topics)}"
            
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
                "sentiment": "neutral",
                "sentiment_score": 0.5
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
Sentiment: <sentiment>"""
        
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        try:
            content = self._call_bedrock(messages, temperature=0.3, max_tokens=500)
            
            if not content:
                return {
                    "summary": "Error generating summary",
                    "key_topics": [],
                    "action_items": [],
                    "sentiment": "neutral",
                    "sentiment_score": 0.5
                }
            
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
            
    async def analyze_sentiment(
        self,
        conversation_text: str
    ) -> Tuple[str, float]:
        """
        Analyze sentiment from conversation text
        Returns: (sentiment, confidence) where sentiment is 'happy', 'neutral', or 'mad'
        """
        if not conversation_text:
            return "neutral", 0.0
            
        system_prompt = """You are a sentiment analysis assistant. Analyze the following conversation and determine the overall sentiment.
        
        Classify the sentiment as one of: happy, neutral, or mad
        
        Consider:
        - Tone and language used
        - Customer satisfaction indicators
        - Frustration or anger signals
        - Positive or appreciative language
        
        Respond with a JSON object containing:
        {
            "sentiment": "happy" | "neutral" | "mad",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }"""
        
        messages = [
            {
                "role": "user",
                "content": [{"text": f"{system_prompt}\n\nAnalyze this conversation:\n\n{conversation_text}"}]
            }
        ]
        
        try:
            response = self._call_bedrock(messages, temperature=0.3, max_tokens=200)
            
            if not response:
                return "neutral", 0.0
            
            # Parse JSON response
            try:
                result = json.loads(response)
                sentiment = result.get("sentiment", "neutral")
                confidence = float(result.get("confidence", 0.5))
                
                # Validate sentiment
                if sentiment not in ["happy", "neutral", "mad"]:
                    sentiment = "neutral"
                    
                logger.info(f"Sentiment analysis result: {sentiment} (confidence: {confidence})")
                return sentiment, confidence
                
            except json.JSONDecodeError:
                # Fallback: try to parse from plain text
                response_lower = response.lower()
                if "happy" in response_lower or "positive" in response_lower:
                    return "happy", 0.7
                elif "mad" in response_lower or "negative" in response_lower or "angry" in response_lower:
                    return "mad", 0.7
                else:
                    return "neutral", 0.5
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return "neutral", 0.0
            
    async def generate_conversation_summary(self, conversation_text: str) -> str:
        """Generate a brief summary of the conversation"""
        
        if not conversation_text:
            return "No conversation to summarize"
            
        prompt = f"""Please provide a brief 2-3 sentence summary of this customer service conversation. Focus on the main issue and current status:

{conversation_text}

Summary:"""
        
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
        
        try:
            response = self._call_bedrock(messages, temperature=0.3, max_tokens=150)
            
            if not response:
                return "Error generating summary"
            
            summary = response.strip()
            
            # Remove "Summary:" prefix if present
            if summary.startswith("Summary:"):
                summary = summary.replace("Summary:", "").strip()
                
            return summary
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {e}")
            return "Error generating summary"
            
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