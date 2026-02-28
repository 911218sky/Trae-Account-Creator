"""Custom exceptions for the mail client.

This module defines the exception hierarchy for the mail client,
providing structured error handling with contextual information.
"""

from typing import List, Optional


class MailClientError(Exception):
    """Base class for all mail client exceptions.
    
    All custom exceptions in the mail client inherit from this class,
    allowing for broad exception handling when needed.
    """
    pass


class ConfigurationError(MailClientError):
    """Configuration-related errors.
    
    Raised when required configuration is missing or invalid.
    
    Attributes:
        missing_keys: List of configuration keys that are missing or invalid.
    """
    
    def __init__(self, message: str, missing_keys: Optional[List[str]] = None):
        """Initialize configuration error.
        
        Args:
            message: Error description.
            missing_keys: List of missing configuration keys.
        """
        super().__init__(message)
        self.missing_keys = missing_keys or []


class ConnectionError(MailClientError):
    """IMAP connection-related errors.
    
    Raised when connection to the IMAP server fails or is interrupted.
    
    Attributes:
        original_error: The underlying exception that caused the connection error.
    """
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize connection error.
        
        Args:
            message: Error description.
            original_error: The original exception that caused this error.
        """
        super().__init__(message)
        self.original_error = original_error


class EmailParsingError(MailClientError):
    """Email parsing-related errors.
    
    Raised when email content cannot be parsed or decoded properly.
    """
    pass
