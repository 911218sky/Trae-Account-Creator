"""Logging configuration for the mail client.

This module provides centralized logging setup with configurable levels
and structured output format.
"""

import logging
import sys

from .constants import DEFAULT_LOG_LEVEL, LOG_FORMAT


def setup_logger(
    name: str = "mail_client",
    log_level: str = DEFAULT_LOG_LEVEL,
    log_format: str = LOG_FORMAT
) -> logging.Logger:
    """Setup and configure logger.
    
    Creates a logger with console handler and specified format.
    
    Args:
        name: Logger name (default: "mail_client").
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Log message format string.
        
    Returns:
        Configured logger instance.
        
    Example:
        logger = setup_logger("my_app", "DEBUG")
        logger.info("Application started")
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger
