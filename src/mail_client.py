"""Async IMAP mail client for temporary email addresses and verification code extraction.

This module provides a professional-grade async mail client with type safety,
comprehensive error handling, and structured logging.
"""

import email.message
import logging
import random
from email.header import decode_header
from typing import Optional

from src.config import MailConfig
from src.connection import IMAPConnection
from src.constants import SEARCH_HEADERS, SUBJECT_FILTER, USERNAME_CHARSET, USERNAME_LENGTH
from src.logger import setup_logger
from src.parser import VerificationCodeParser


class AsyncMailClient:
    """Async IMAP mail client.
    
    Provides temporary email address generation, email checking, and
    verification code parsing functionality. Supports async context manager
    protocol for proper resource management.
    
    Example:
        async with AsyncMailClient() as client:
            email = client.get_email()
            print(f"Generated email: {email}")
            
            await client.check_emails()
            if client.last_verification_code:
                print(f"Verification code: {client.last_verification_code}")
    """
    
    def __init__(
        self,
        config: Optional[MailConfig] = None,
        connection: Optional[IMAPConnection] = None,
        parser: Optional[VerificationCodeParser] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize mail client.
        
        Args:
            config: Configuration object, None to load from environment.
            connection: IMAP connection, for dependency injection (testing).
            parser: Verification code parser, for dependency injection (testing).
            logger: Logger instance, for dependency injection (testing).
        """
        # Load or use provided configuration
        self.config = config or MailConfig.from_env()
        
        # Setup logger
        self.logger = logger or self._setup_logger()
        
        # Initialize components
        self.connection = connection or IMAPConnection(self.config, self.logger)
        self.parser = parser or VerificationCodeParser(
            self.config.verification_code_length
        )
        
        # State
        self.email_address: Optional[str] = None
        self.last_verification_code: Optional[str] = None
    
    async def __aenter__(self) -> "AsyncMailClient":
        """Async context manager entry.
        
        Establishes IMAP connection.
        
        Returns:
            Self for use in with statement.
        """
        await self.connection.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.
        
        Closes IMAP connection, even if an exception occurred.
        
        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        await self.close()
    
    def get_email(self) -> str:
        """Generate random temporary email address.
        
        Generates a random username and combines it with a randomly
        selected domain from the configuration.
        
        Returns:
            Generated email address.
            
        Example:
            email = client.get_email()
            # Returns something like: "a3x9k2m7p1@example.com"
        """
        # Generate random username
        username = ''.join(
            random.choices(USERNAME_CHARSET, k=USERNAME_LENGTH)
        )
        
        # Select random domain
        domain = random.choice(self.config.custom_domains)
        
        # Create email address
        self.email_address = f"{username}@{domain}"
        
        self.logger.info(f"Generated email address: {self.email_address}")
        
        return self.email_address
    
    async def check_emails(self) -> None:
        """Check for new emails sent to the generated address.
        
        Searches for emails matching the generated address and subject filter,
        then processes them to extract verification codes.
        
        Updates last_verification_code if a code is found.
        """
        if not self.email_address:
            self.logger.warning("No email address generated yet. Call get_email() first.")
            return
        
        try:
            # Select inbox
            await self.connection.select_mailbox("inbox")
            
            # Search for emails
            criteria = f'(TO "{self.email_address}" SUBJECT "{SUBJECT_FILTER}")'
            email_ids = await self.connection.search_emails(criteria)
            
            if not email_ids:
                self.logger.debug(f"No emails found for {self.email_address}")
                return
            
            # Process the latest email
            latest_email_id = email_ids[-1]
            self.logger.info(f"Found {len(email_ids)} email(s), processing latest")
            
            msg = await self.connection.fetch_email(latest_email_id)
            await self._process_email(msg)
            
        except Exception as e:
            self.logger.error(f"Error checking emails: {e}", exc_info=True)
    
    async def close(self) -> None:
        """Close connection and clean up resources.
        
        Closes the IMAP connection. Does not raise exceptions on failure.
        """
        await self.connection.close()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the mail client.
        
        Returns:
            Configured logger instance.
        """
        return setup_logger(
            name="mail_client",
            log_level=self.config.log_level
        )
    
    async def _process_email(self, msg: email.message.Message) -> None:
        """Process a single email message.
        
        Verifies the recipient, extracts the body, and parses verification code.
        
        Args:
            msg: Email message object.
        """
        # Verify recipient
        if not self._verify_recipient(msg):
            self.logger.warning(
                f"Skipping email: recipient mismatch (expected {self.email_address})"
            )
            return
        
        # Decode subject
        subject = self._decode_subject(msg)
        self.logger.info(f"Processing email: {subject}")
        
        # Extract body
        body = self._extract_body(msg)
        
        # Parse verification code
        code = self.parser.parse(body)
        if code:
            self.last_verification_code = code
            self.logger.info(f"Extracted verification code: {code}")
        else:
            self.logger.debug("No verification code found in email")
    
    def _verify_recipient(self, msg: email.message.Message) -> bool:
        """Verify email was sent to the generated address.
        
        Checks multiple headers to ensure the email was actually sent
        to our generated address.
        
        Args:
            msg: Email message object.
            
        Returns:
            True if recipient matches, False otherwise.
        """
        if not self.email_address:
            return False
        
        email_lower = self.email_address.lower()
        
        # Check standard headers
        for header_name in SEARCH_HEADERS:
            header_val = msg.get(header_name, '')
            if header_val and email_lower in str(header_val).lower():
                return True
        
        # Double check raw headers
        try:
            raw_headers = str(msg)
            if email_lower in raw_headers.lower():
                return True
        except Exception as e:
            self.logger.debug(f"Error checking raw headers: {e}")
        
        return False
    
    def _decode_subject(self, msg: email.message.Message) -> str:
        """Decode email subject.
        
        Args:
            msg: Email message object.
            
        Returns:
            Decoded subject string.
        """
        subject_header = msg.get("Subject", "")
        if not subject_header:
            return "(No Subject)"
        
        try:
            decoded_parts = decode_header(subject_header)
            subject_parts = []
            
            for content, encoding in decoded_parts:
                if isinstance(content, bytes):
                    subject_parts.append(
                        content.decode(encoding if encoding else "utf-8", errors="replace")
                    )
                else:
                    subject_parts.append(str(content))
            
            return ''.join(subject_parts)
        except Exception as e:
            self.logger.warning(f"Error decoding subject: {e}")
            return str(subject_header)
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract text body from email message.
        
        Handles both multipart and single-part messages, extracting
        text/plain or text/html content.
        
        Args:
            msg: Email message object.
            
        Returns:
            Email body text.
        """
        body = ""
        
        if msg.is_multipart():
            # Process multipart message
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Extract text content
                if content_type in ("text/plain", "text/html"):
                    try:
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="replace")
                            break  # Use first text part found
                    except Exception as e:
                        self.logger.debug(f"Error extracting part: {e}")
        else:
            # Process single-part message
            try:
                payload = msg.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
            except Exception as e:
                self.logger.debug(f"Error extracting body: {e}")
        
        return body
