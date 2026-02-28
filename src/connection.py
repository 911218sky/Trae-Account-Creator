"""IMAP connection management.

This module handles IMAP connection lifecycle, providing async wrappers
around synchronous imaplib operations.
"""

import asyncio
import email.message
import imaplib
import logging
import socket
from typing import List, Optional

from .config import MailConfig
from .exceptions import ConnectionError as MailConnectionError


class IMAPConnection:
    """IMAP connection manager.
    
    Encapsulates all IMAP operations and provides async interface.
    Uses asyncio.to_thread to wrap synchronous imaplib operations.
    
    Example:
        config = MailConfig.from_env()
        connection = IMAPConnection(config)
        await connection.connect()
        email_ids = await connection.search_emails('(TO "user@example.com")')
        await connection.close()
    """
    
    def __init__(self, config: MailConfig, logger: Optional[logging.Logger] = None):
        """Initialize IMAP connection manager.
        
        Args:
            config: Mail configuration.
            logger: Logger instance (optional).
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._connection: Optional[imaplib.IMAP4_SSL] = None
    
    async def connect(self) -> None:
        """Establish IMAP connection.
        
        Connects to the IMAP server and authenticates using credentials
        from the configuration.
        
        Raises:
            MailConnectionError: When connection or authentication fails.
        """
        self.logger.info(
            f"Connecting to IMAP server {self.config.imap_server}:{self.config.imap_port}..."
        )
        
        try:
            self._connection = await asyncio.to_thread(self._sync_connect)
            self.logger.info("IMAP connection successful")
        except (socket.error, imaplib.IMAP4.error, OSError) as e:
            error_msg = (
                f"Failed to connect to IMAP server "
                f"{self.config.imap_server}:{self.config.imap_port}"
            )
            self.logger.error(f"{error_msg}: {e}", exc_info=True)
            raise MailConnectionError(error_msg, original_error=e) from e
    
    async def search_emails(self, criteria: str) -> List[bytes]:
        """Search for emails matching criteria.
        
        Args:
            criteria: IMAP search criteria (e.g., '(TO "user@example.com")').
            
        Returns:
            List of email IDs.
            
        Raises:
            MailConnectionError: When search fails.
        """
        if not self._connection:
            raise MailConnectionError("Not connected to IMAP server")
        
        try:
            status, messages = await asyncio.to_thread(
                self._connection.search, None, criteria
            )
            
            if status != "OK":
                raise MailConnectionError(f"IMAP search failed with status: {status}")
            
            # Parse email IDs
            email_ids = messages[0].split() if messages[0] else []
            return email_ids
            
        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP search failed: {criteria}"
            self.logger.error(f"{error_msg}: {e}", exc_info=True)
            raise MailConnectionError(error_msg, original_error=e) from e
    
    async def fetch_email(self, email_id: bytes) -> email.message.Message:
        """Fetch email content.
        
        Args:
            email_id: Email ID to fetch.
            
        Returns:
            Email message object.
            
        Raises:
            MailConnectionError: When fetch fails.
        """
        if not self._connection:
            raise MailConnectionError("Not connected to IMAP server")
        
        try:
            status, msg_data = await asyncio.to_thread(
                self._connection.fetch, email_id.decode() if isinstance(email_id, bytes) else email_id, "(RFC822)"
            )
            
            if status != "OK":
                raise MailConnectionError(
                    f"IMAP fetch failed with status: {status} for email ID: {email_id}"
                )
            
            # Parse email message
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    return msg
            
            raise MailConnectionError(f"No email data found for ID: {email_id}")
            
        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP fetch failed for email ID: {email_id}"
            self.logger.error(f"{error_msg}: {e}", exc_info=True)
            raise MailConnectionError(error_msg, original_error=e) from e
    
    async def select_mailbox(self, mailbox: str = "inbox") -> None:
        """Select a mailbox.
        
        Args:
            mailbox: Mailbox name (default: "inbox").
            
        Raises:
            MailConnectionError: When selection fails.
        """
        if not self._connection:
            raise MailConnectionError("Not connected to IMAP server")
        
        try:
            status, _ = await asyncio.to_thread(
                self._connection.select, mailbox
            )
            
            if status != "OK":
                raise MailConnectionError(
                    f"Failed to select mailbox '{mailbox}' with status: {status}"
                )
                
        except imaplib.IMAP4.error as e:
            error_msg = f"Failed to select mailbox '{mailbox}'"
            self.logger.error(f"{error_msg}: {e}", exc_info=True)
            raise MailConnectionError(error_msg, original_error=e) from e
    
    async def close(self) -> None:
        """Close IMAP connection.
        
        Logs out from the IMAP server and closes the connection.
        Does not raise exceptions on failure, only logs errors.
        """
        if self._connection:
            try:
                await asyncio.to_thread(self._connection.logout)
                self.logger.info("IMAP connection closed")
            except Exception as e:
                self.logger.error(f"Error closing IMAP connection: {e}", exc_info=True)
            finally:
                self._connection = None
    
    def _sync_connect(self) -> imaplib.IMAP4_SSL:
        """Synchronous connection implementation.
        
        This method is called via asyncio.to_thread to avoid blocking.
        
        Returns:
            Connected IMAP4_SSL instance.
            
        Raises:
            socket.error: On network errors.
            imaplib.IMAP4.error: On IMAP protocol errors.
        """
        # Create SSL connection
        mail = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
        
        # Authenticate
        mail.login(self.config.email_user, self.config.email_pass)
        
        return mail
