import imaplib
import email
from email.header import decode_header
import random
import string
import re
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN")

class AsyncMailClient:
    def __init__(self):
        self.email_address = None
        self.last_verification_code = None
        self.mail = None
        self.connected = False

    async def start(self):
        """Initialize IMAP connection"""
        if not all([EMAIL_USER, EMAIL_PASS, CUSTOM_DOMAIN]):
            print("Error: Please configure EMAIL_USER, EMAIL_PASS, and CUSTOM_DOMAIN in .env file")
            return

        print(f"Connecting to IMAP server ({IMAP_SERVER})...")
        try:
            self.mail = await asyncio.to_thread(self._connect_imap)
            self.connected = True
            print("IMAP connection successful")
        except Exception as e:
            print(f"IMAP connection failed: {e}")

    def _connect_imap(self):
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail

    def get_email(self):
        """Generate a random email address with custom domain"""
        # Generate a random string of 10 characters (letters + digits)
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        # Handle multiple domains
        domains = [d.strip() for d in CUSTOM_DOMAIN.split(',') if d.strip()]
        if not domains:
            print("Error: No valid domains found in CUSTOM_DOMAIN")
            return None
            
        domain = random.choice(domains)
        self.email_address = f"{username}@{domain}"
        print(f"Generated email address: {self.email_address}")
        return self.email_address

    async def check_emails(self):
        """Check for new emails sent to the generated address"""
        if not self.connected or not self.mail:
            return

        try:
            # Run blocking IMAP operations in a separate thread
            await asyncio.to_thread(self._check_emails_sync)
        except Exception as e:
            print(f"Error checking emails: {e}")

    def _check_emails_sync(self):
        try:
            # Select inbox
            self.mail.select("inbox")

            # Search for emails sent TO our generated address
            # Also filter by SUBJECT "Trae" to avoid spam or other emails
            status, messages = self.mail.search(None, f'(TO "{self.email_address}" SUBJECT "Trae")')

            if status != "OK":
                return

            email_ids = messages[0].split()
            if not email_ids:
                return

            # Process the latest email
            latest_email_id = email_ids[-1]
            status, msg_data = self.mail.fetch(latest_email_id, "(RFC822)")

            if status != "OK":
                return

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Verify recipient strictly in Python
                    # Sometimes IMAP search might be loose or headers might be complex
                    recipient_found = False
                    check_headers = ['To', 'X-Forwarded-To', 'Delivered-To', 'Cc']
                    for header_name in check_headers:
                        header_val = msg.get(header_name, '')
                        if header_val and self.email_address.lower() in str(header_val).lower():
                            recipient_found = True
                            break
                    
                    if not recipient_found:
                        # Double check raw headers just in case
                        try:
                            raw_headers = str(msg)
                            if self.email_address.lower() in raw_headers.lower():
                                recipient_found = True
                        except:
                            pass

                    if not recipient_found:
                        print(f"Skipping email (recipient mismatch): Expected {self.email_address}")
                        continue

                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    print(f"Received new email: {subject}")
                    
                    body = self._get_email_body(msg)
                    self._parse_verification_code(body)

        except Exception as e:
            print(f"IMAP sync check error: {e}")

    def _get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" not in content_disposition:
                    if content_type == "text/plain" or content_type == "text/html":
                        try:
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset()
                            if charset:
                                return payload.decode(charset, errors="replace")
                            else:
                                return payload.decode("utf-8", errors="replace")
                        except:
                            pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset()
                if charset:
                    return payload.decode(charset, errors="replace")
                else:
                    return payload.decode("utf-8", errors="replace")
            except:
                pass
        return ""

    def _parse_verification_code(self, content):
        # Clean HTML tags to avoid parsing numbers from attributes or styles
        clean_content = re.sub(r'<[^>]+>', ' ', content)
        
        # Look for 6-digit code (e.g., 123456)
        codes = re.findall(r'\b\d{6}\b', clean_content)
        if codes:
            self.last_verification_code = codes[0]
            print(f"Parsed verification code: {self.last_verification_code}")
            return

        # Look for spaced 6-digit code (e.g., 3 5 5 9 0 3)
        # Matches 6 digits separated by whitespace
        spaced_codes = re.findall(r'\b\d\s+\d\s+\d\s+\d\s+\d\s+\d\b', clean_content)
        if spaced_codes:
            # Remove spaces to get the raw code
            code = re.sub(r'\s+', '', spaced_codes[0])
            self.last_verification_code = code
            print(f"Parsed spaced verification code: {self.last_verification_code}")

    async def close(self):
        if self.mail:
            try:
                await asyncio.to_thread(self.mail.logout)
            except:
                pass
        self.connected = False
