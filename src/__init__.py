"""Mail client package for temporary email addresses and verification code extraction.

This package provides a professional-grade async mail client with modular architecture.
"""

from src.config import MailConfig
from src.connection import IMAPConnection
from src.exceptions import (
    ConfigurationError,
    ConnectionError,
    EmailParsingError,
    MailClientError,
)
from src.mail_client import AsyncMailClient
from src.parser import CodeCandidate, VerificationCodeParser

__all__ = [
    "AsyncMailClient",
    "MailConfig",
    "IMAPConnection",
    "VerificationCodeParser",
    "CodeCandidate",
    "MailClientError",
    "ConfigurationError",
    "ConnectionError",
    "EmailParsingError",
]

__version__ = "2.0.0"
