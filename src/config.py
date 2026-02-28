"""Configuration management for the mail client.

This module handles loading and validating configuration from environment variables.
"""

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

from .constants import (
    DEFAULT_CODE_LENGTH,
    DEFAULT_IMAP_PORT,
    DEFAULT_IMAP_SERVER,
    DEFAULT_LOG_LEVEL,
    MAX_PORT,
    MIN_PORT,
)
from .exceptions import ConfigurationError


@dataclass(frozen=True)
class MailConfig:
    """Mail client configuration.
    
    All configuration items are loaded from environment variables and validated.
    Using frozen dataclass ensures configuration is immutable after creation.
    
    Attributes:
        imap_server: IMAP server hostname.
        imap_port: IMAP server port (1-65535).
        email_user: Email account username.
        email_pass: Email account password.
        custom_domains: List of custom domains for temporary email addresses.
        verification_code_length: Expected length of verification codes (default: 6).
        log_level: Logging level (default: "INFO").
    """
    
    imap_server: str
    imap_port: int
    email_user: str
    email_pass: str
    custom_domains: List[str]
    verification_code_length: int = DEFAULT_CODE_LENGTH
    log_level: str = DEFAULT_LOG_LEVEL
    
    @classmethod
    def from_env(cls) -> "MailConfig":
        """Load configuration from environment variables.
        
        Loads configuration from .env file and environment variables.
        Required variables: IMAP_SERVER, IMAP_PORT, EMAIL_USER, EMAIL_PASS, CUSTOM_DOMAIN.
        
        Returns:
            MailConfig: Validated configuration object.
            
        Raises:
            ConfigurationError: When required configuration is missing or invalid.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Required configuration keys
        required_keys = ['EMAIL_USER', 'EMAIL_PASS', 'CUSTOM_DOMAIN']
        missing_keys = []
        
        # Check for missing required keys
        for key in required_keys:
            if not os.getenv(key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration: {', '.join(missing_keys)}. "
                f"Please configure these variables in your .env file.",
                missing_keys=missing_keys
            )
        
        # Load configuration values
        imap_server = os.getenv("IMAP_SERVER", DEFAULT_IMAP_SERVER)
        imap_port_str = os.getenv("IMAP_PORT", str(DEFAULT_IMAP_PORT))
        email_user = os.getenv("EMAIL_USER")
        email_pass = os.getenv("EMAIL_PASS")
        custom_domain_str = os.getenv("CUSTOM_DOMAIN")
        
        # Ensure email_user and email_pass are not None (already checked above)
        if not email_user or not email_pass:
            raise ConfigurationError(
                "EMAIL_USER and EMAIL_PASS must be set",
                missing_keys=['EMAIL_USER', 'EMAIL_PASS']
            )
        
        # Parse IMAP port
        try:
            imap_port = int(imap_port_str)
        except ValueError:
            raise ConfigurationError(
                f"Invalid IMAP_PORT configuration: '{imap_port_str}'. "
                f"Port must be a number between {MIN_PORT} and {MAX_PORT}. "
                f"Please check your .env file and ensure IMAP_PORT is set correctly.",
                missing_keys=[]
            )
        
        # Parse custom domains
        if not custom_domain_str:
            raise ConfigurationError(
                "Missing required configuration: CUSTOM_DOMAIN. "
                "Please configure this variable in your .env file.",
                missing_keys=['CUSTOM_DOMAIN']
            )
        custom_domains = [d.strip() for d in custom_domain_str.split(',') if d.strip()]
        
        # Create config instance
        config = cls(
            imap_server=imap_server,
            imap_port=imap_port,
            email_user=email_user,
            email_pass=email_pass,
            custom_domains=custom_domains,
            verification_code_length=int(os.getenv("VERIFICATION_CODE_LENGTH", str(DEFAULT_CODE_LENGTH))),
            log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """Validate configuration values.
        
        Raises:
            ConfigurationError: When configuration is invalid.
        """
        # Validate IMAP port range
        if not (MIN_PORT <= self.imap_port <= MAX_PORT):
            raise ConfigurationError(
                f"Invalid IMAP_PORT configuration: '{self.imap_port}'. "
                f"Port must be between {MIN_PORT} and {MAX_PORT}.",
                missing_keys=[]
            )
        
        # Validate custom domains
        if not self.custom_domains:
            raise ConfigurationError(
                "Invalid CUSTOM_DOMAIN configuration: No valid domains found. "
                "Please provide at least one domain in CUSTOM_DOMAIN.",
                missing_keys=['CUSTOM_DOMAIN']
            )
        
        # Validate domain format (basic check)
        for domain in self.custom_domains:
            if not domain or domain.isspace():
                raise ConfigurationError(
                    f"Invalid CUSTOM_DOMAIN configuration: Empty or whitespace-only domain found. "
                    f"Please check your CUSTOM_DOMAIN setting.",
                    missing_keys=['CUSTOM_DOMAIN']
                )
            
            # Basic domain format validation (contains at least one dot)
            if '.' not in domain:
                raise ConfigurationError(
                    f"Invalid CUSTOM_DOMAIN configuration: '{domain}' does not appear to be a valid domain. "
                    f"Domains should contain at least one dot (e.g., 'example.com').",
                    missing_keys=['CUSTOM_DOMAIN']
                )


def env_bool(name: str, default: bool) -> bool:
    """Parse boolean value from environment variable.

    Args:
        name: Environment variable name.
        default: Default value if variable is not set.

    Returns:
        Boolean value parsed from environment variable.
    """
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return default


def env_int(name: str, default: int) -> int:
    """Parse integer value from environment variable.

    Args:
        name: Environment variable name.
        default: Default value if variable is not set or invalid.

    Returns:
        Integer value parsed from environment variable.
    """
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default




def env_bool(name: str, default: bool) -> bool:
    """Parse boolean value from environment variable.
    
    Args:
        name: Environment variable name.
        default: Default value if variable is not set.
        
    Returns:
        Boolean value parsed from environment variable.
    """
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip().lower()
    if val in {"1", "true", "yes", "y", "on"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return default


def env_int(name: str, default: int) -> int:
    """Parse integer value from environment variable.
    
    Args:
        name: Environment variable name.
        default: Default value if variable is not set or invalid.
        
    Returns:
        Integer value parsed from environment variable.
    """
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default
