"""
Input validation and sanitization utilities to guard against injection attacks.
"""
from html import escape
import re


class InputValidator:
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """Sanitize user input to prevent injection attacks."""
        if not text:
            raise ValueError("Text cannot be empty")
        
        if len(text) > max_length:
            raise ValueError(f"Text exceeds max length of {max_length}")
        
        # Remove potential XSS
        text = escape(text)
        
        # Prevent SQL injection in resource/thread params
        text = re.sub(r'[^\w\-.]', '', text)
        
        return text
    
    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        """Detect potential prompt injection attacks based on suspicious patterns."""
        suspicious_patterns = [
            r'ignore.*instructions',
            r'system.*override',
            r'act\s+as\s+admin',
            r'execute.*code',
        ]
        
        lowercase_text = text.lower()
        return any(re.search(pattern, lowercase_text) for pattern in suspicious_patterns)
