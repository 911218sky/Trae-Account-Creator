"""Verification code parser for extracting codes from email content.

This module provides functionality to parse verification codes from email content,
supporting multiple formats and using heuristic rules to select the best candidate.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from .constants import (
    CODE_PATTERN_CONTINUOUS,
    CODE_PATTERN_DASHED,
    CODE_PATTERN_SPACED,
    DEFAULT_CODE_LENGTH,
)


@dataclass
class CodeCandidate:
    """Verification code candidate.
    
    Represents a potential verification code found in email content,
    along with metadata for confidence scoring.
    
    Attributes:
        code: The extracted verification code (digits only).
        confidence: Confidence score (0.0 - 1.0).
        pattern_type: Type of pattern matched ("continuous", "spaced", "dashed").
    """
    code: str
    confidence: float
    pattern_type: str


class VerificationCodeParser:
    """Verification code parser.
    
    Supports parsing multiple verification code formats using regex patterns
    and heuristic rules to select the most likely candidate.
    
    Supported formats:
    - Continuous digits: "123456"
    - Spaced digits: "1 2 3 4 5 6"
    - Dashed digits: "123-456"
    
    Example:
        parser = VerificationCodeParser(code_length=6)
        code = parser.parse(email_content)
        if code:
            print(f"Found verification code: {code}")
    """
    
    def __init__(self, code_length: int = DEFAULT_CODE_LENGTH):
        """Initialize verification code parser.
        
        Args:
            code_length: Expected length of verification codes (default: 6).
        """
        self.code_length = code_length
        self._patterns = self._compile_patterns()
    
    def parse(self, content: str) -> Optional[str]:
        """Parse verification code from email content.
        
        Cleans HTML tags, finds all candidates, and returns the one with
        the highest confidence score.
        
        Args:
            content: Email content (may contain HTML).
            
        Returns:
            Verification code string, or None if not found.
        """
        # Clean HTML tags
        clean_content = self._clean_html(content)
        
        # Find all candidates
        candidates = self.find_candidates(clean_content)
        
        # Return the best candidate (highest confidence)
        if candidates:
            return candidates[0].code
        
        return None
    
    def find_candidates(self, content: str) -> List[CodeCandidate]:
        """Find all candidate verification codes.
        
        Args:
            content: Cleaned text content.
            
        Returns:
            List of candidates sorted by confidence (highest first).
        """
        candidates = []
        
        # Search for continuous digits
        for match in self._patterns['continuous'].finditer(content):
            code = match.group(0)
            confidence = self._calculate_confidence(
                code, 'continuous', content, match.start()
            )
            candidates.append(CodeCandidate(code, confidence, 'continuous'))
        
        # Search for spaced digits
        for match in self._patterns['spaced'].finditer(content):
            spaced_code = match.group(0)
            code = re.sub(r'\s+', '', spaced_code)
            confidence = self._calculate_confidence(
                code, 'spaced', content, match.start()
            )
            candidates.append(CodeCandidate(code, confidence, 'spaced'))
        
        # Search for dashed digits
        for match in self._patterns['dashed'].finditer(content):
            dashed_code = match.group(0)
            code = re.sub(r'-', '', dashed_code)
            confidence = self._calculate_confidence(
                code, 'dashed', content, match.start()
            )
            candidates.append(CodeCandidate(code, confidence, 'dashed'))
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        
        return candidates
    
    def _compile_patterns(self) -> dict:
        """Compile regex patterns for different code formats.
        
        Returns:
            Dictionary of compiled regex patterns.
        """
        patterns = {}
        
        # Continuous digits pattern: \b\d{6}\b
        continuous_pattern = CODE_PATTERN_CONTINUOUS.format(length=self.code_length)
        patterns['continuous'] = re.compile(continuous_pattern)
        
        # Spaced digits pattern: \b\d(?:\s+\d){5}\b
        count = self.code_length - 1
        spaced_pattern = CODE_PATTERN_SPACED.format(count=count)
        patterns['spaced'] = re.compile(spaced_pattern)
        
        # Dashed digits pattern: \b\d(?:-\d){5}\b or \b\d{3}-\d{3}\b
        dashed_pattern = CODE_PATTERN_DASHED.format(count=count)
        patterns['dashed'] = re.compile(dashed_pattern)
        
        return patterns
    
    def _clean_html(self, content: str) -> str:
        """Remove HTML tags from content.
        
        Args:
            content: Raw email content (may contain HTML).
            
        Returns:
            Content with HTML tags removed.
        """
        # Remove HTML tags
        clean_content = re.sub(r'<[^>]+>', ' ', content)
        return clean_content
    
    def _calculate_confidence(
        self, 
        code: str, 
        pattern_type: str, 
        context: str,
        position: int
    ) -> float:
        """Calculate confidence score for a candidate code.
        
        Heuristic rules:
        - Continuous digits: base score 0.8
        - Spaced/dashed digits: base score 0.9 (more explicit formatting)
        - Near keywords ("code", "verification", "otp"): +0.1
        - Standalone on line: +0.05
        
        Args:
            code: The extracted code.
            pattern_type: Type of pattern ("continuous", "spaced", "dashed").
            context: Full text content for context analysis.
            position: Position of the code in the content.
            
        Returns:
            Confidence score (0.0 - 1.0).
        """
        # Base score by pattern type
        if pattern_type == 'continuous':
            confidence = 0.8
        else:  # spaced or dashed
            confidence = 0.9
        
        # Extract context around the code (50 chars before and after)
        start = max(0, position - 50)
        end = min(len(context), position + 50)
        local_context = context[start:end].lower()
        
        # Check for verification-related keywords
        keywords = ['code', 'verification', 'verify', 'otp', 'pin', 'token']
        if any(keyword in local_context for keyword in keywords):
            confidence += 0.1
        
        # Check if code is standalone on a line (surrounded by newlines or whitespace)
        if position > 0 and position < len(context) - len(code):
            before = context[max(0, position - 2):position]
            after = context[position + len(code):min(len(context), position + len(code) + 2)]
            if ('\n' in before or before.isspace()) and ('\n' in after or after.isspace()):
                confidence += 0.05
        
        # Cap confidence at 1.0
        return min(confidence, 1.0)
