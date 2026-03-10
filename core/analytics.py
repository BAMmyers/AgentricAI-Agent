"""
Analytics engine for conversation analysis and insights extraction.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import json

try:
    import spacy
except ImportError:
    spacy = None

from core.config import get_config


class ConversationAnalytics:
    """Analyze conversations to extract insights and patterns."""
    
    def __init__(self):
        """Initialize analytics engine."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            self.nlp = None
            print("Warning: spacy model not available for NLP analysis")
    
    async def analyze_session(
        self,
        messages: List[Dict[str, Any]],
        resource: str = "default"
    ) -> Dict[str, Any]:
        """Analyze a conversation session."""
        if not messages:
            return {
                "total_messages": 0,
                "error": "No messages to analyze"
            }
        
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        stats = {
            "session_id": resource,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "message_distribution": len(user_messages) / max(1, len(messages)),
            "avg_user_length": sum(len(m.get("content", "")) for m in user_messages) / max(1, len(user_messages)),
            "avg_assistant_length": sum(len(m.get("content", "")) for m in assistant_messages) / max(1, len(assistant_messages)),
        }
        
        # Extract topics if NLP available
        if self.nlp:
            stats["topics"] = await self._extract_topics(user_messages)
            stats["entities"] = await self._extract_entities(user_messages)
            stats["sentiment_trends"] = await self._analyze_sentiment_trends(messages)
        
        # Extract key questions
        stats["key_questions"] = await self._extract_key_questions(user_messages)
        
        # Calculate session duration if timestamps available
        if messages and "timestamp" in messages[0]:
            try:
                start = datetime.fromisoformat(messages[0]["timestamp"])
                end = datetime.fromisoformat(messages[-1]["timestamp"])
                stats["session_duration_seconds"] = (end - start).total_seconds()
            except Exception:
                pass
        
        return stats
    
    async def _extract_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key topics from messages."""
        if not self.nlp or not messages:
            return []
        
        all_text = " ".join(m.get("content", "") for m in messages)
        doc = self.nlp(all_text[:5000])  # Limit to first 5000 chars
        
        # Extract noun chunks as topics
        topics = Counter()
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Simple noun phrases
                topics[chunk.text.lower()] += 1
        
        return [f"{topic} ({count})" for topic, count in topics.most_common(5)]
    
    async def _extract_entities(self, messages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract named entities."""
        if not self.nlp or not messages:
            return {}
        
        all_text = " ".join(m.get("content", "") for m in messages)
        doc = self.nlp(all_text[:5000])
        
        entities = {}
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            if ent.text not in entities[ent.label_]:
                entities[ent.label_].append(ent.text)
        
        return {k: v[:10] for k, v in entities.items()}  # Limit to 10 per type
    
    async def _analyze_sentiment_trends(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment trends through conversation."""
        # Simple sentiment analysis
        positive_words = {"good", "great", "excellent", "amazing", "love", "brilliant", "perfect"}
        negative_words = {"bad", "poor", "terrible", "hate", "awful", "problem", "issue"}
        
        sentiments = []
        for msg in messages:
            content = msg.get("content", "").lower()
            pos_count = sum(1 for word in positive_words if word in content)
            neg_count = sum(1 for word in negative_words if word in content)
            
            if pos_count > neg_count:
                sentiments.append("positive")
            elif neg_count > pos_count:
                sentiments.append("negative")
            else:
                sentiments.append("neutral")
        
        return {
            "timeline": sentiments,
            "positive_count": sentiments.count("positive"),
            "negative_count": sentiments.count("negative"),
            "neutral_count": sentiments.count("neutral"),
            "overall": "positive" if sentiments.count("positive") > sentiments.count("negative") else "negative" if sentiments.count("negative") > 0 else "neutral"
        }
    
    async def _extract_key_questions(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key questions from user messages."""
        questions = []
        
        for msg in messages:
            content = msg.get("content", "")
            if "?" in content:
                # Extract sentences ending with ?
                sentences = content.split(".")
                for sentence in sentences:
                    if "?" in sentence:
                        q = sentence.split("?")[0].strip() + "?"
                        if len(q) > 5:  # Only sentences with substance
                            questions.append(q)
        
        return questions[:10]  # Return top 10
    
    async def get_usage_statistics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get usage statistics."""
        if not messages:
            return {}
        
        content_lengths = [len(m.get("content", "")) for m in messages]
        
        return {
            "total_characters": sum(content_lengths),
            "total_words": sum(len(m.get("content", "").split()) for m in messages),
            "avg_message_length": sum(content_lengths) / max(1, len(messages)),
            "max_message_length": max(content_lengths) if content_lengths else 0,
            "min_message_length": min(content_lengths) if content_lengths else 0,
        }
    
    async def compare_sessions(
        self,
        session1: List[Dict[str, Any]],
        session2: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare statistics between two sessions."""
        analysis1 = await self.analyze_session(session1)
        analysis2 = await self.analyze_session(session2)
        
        return {
            "session1": analysis1,
            "session2": analysis2,
            "comparison": {
                "total_messages_change": analysis2.get("total_messages", 0) - analysis1.get("total_messages", 0),
                "avg_length_change": analysis2.get("avg_user_length", 0) - analysis1.get("avg_user_length", 0),
            }
        }


# Global analytics instance
analytics = ConversationAnalytics()
