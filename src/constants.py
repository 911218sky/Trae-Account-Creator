"""Constants for the mail client.

This module centralizes all magic numbers and configuration defaults,
making them easy to adjust and maintain.
"""

import string

# Email address generation
USERNAME_LENGTH: int = 10
USERNAME_CHARSET: str = string.ascii_lowercase + string.digits

# Verification code parsing
DEFAULT_CODE_LENGTH: int = 6
CODE_PATTERN_CONTINUOUS: str = r'\b\d{{{length}}}\b'
CODE_PATTERN_SPACED: str = r'\b\d(?:\s+\d){{{count}}}\b'
CODE_PATTERN_DASHED: str = r'\b\d(?:-\d){{{count}}}\b'

# IMAP search
SEARCH_HEADERS: list[str] = ['To', 'X-Forwarded-To', 'Delivered-To', 'Cc']
SUBJECT_FILTER: str = "Trae"

# Logging
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_LEVEL: str = "INFO"

# Timeouts (in seconds)
IMAP_CONNECT_TIMEOUT: int = 30
EMAIL_CHECK_TIMEOUT: int = 60

# Default IMAP configuration
DEFAULT_IMAP_SERVER: str = "imap.gmail.com"
DEFAULT_IMAP_PORT: int = 993

# Port validation
MIN_PORT: int = 1
MAX_PORT: int = 65535

# Code length validation
MIN_CODE_LENGTH: int = 4
MAX_CODE_LENGTH: int = 8
