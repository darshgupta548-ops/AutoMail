"""Standards-compliant MIME/RFC 2822 email message builder for Gmail API compatibility."""

import base64
import email
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header


class MIMEBuilderError(Exception):
    """Raised when MIME message construction fails."""


class MIMEBuilderValidationError(MIMEBuilderError):
    """Raised when email fields fail validation (e.g., header injection attempts)."""


def _validate_email_address(email_addr, field_name):
    """Validate email address and reject header injection attempts."""
    if not isinstance(email_addr, str):
        raise MIMEBuilderValidationError(f"{field_name} must be a string.")
    
    email_addr = email_addr.strip()
    
    if not email_addr:
        raise MIMEBuilderValidationError(f"{field_name} cannot be empty.")
    
    # Reject newlines, carriage returns, and other control characters that could inject headers
    if '\n' in email_addr or '\r' in email_addr or '\x00' in email_addr:
        raise MIMEBuilderValidationError(
            f"{field_name} contains invalid characters (newlines/control chars not allowed)."
        )
    
    # Basic email format validation
    # Must have at least one @, and non-whitespace around it
    if '@' not in email_addr or email_addr.count('@') > 1:
        raise MIMEBuilderValidationError(f"{field_name} is not a valid email address.")
    
    local_part, domain_part = email_addr.rsplit('@', 1)
    if not local_part.strip() or not domain_part.strip():
        raise MIMEBuilderValidationError(f"{field_name} is not a valid email address.")
    
    # Reject common injection patterns
    if any(char in email_addr for char in ['<', '>', ';', ',']):
        raise MIMEBuilderValidationError(
            f"{field_name} contains characters that are not allowed in a single email address."
        )
    
    return email_addr


def _validate_text(text, field_name, allow_empty=False, allow_newlines=False):
    """Validate text field and reject header injection attempts."""
    if not isinstance(text, str):
        raise MIMEBuilderValidationError(f"{field_name} must be a string.")
    
    # Reject newlines and carriage returns in header fields (subject, etc.)
    # RFC 5322 allows folding whitespace (CRLF SPACE/TAB), but we restrict to plain CRLF
    # to prevent injection. We allow internal newlines for body text if allow_newlines=True.
    if '\r' in text or '\x00' in text:
        raise MIMEBuilderValidationError(
            f"{field_name} contains invalid characters (CR or null bytes not allowed)."
        )
    
    if not allow_newlines and '\n' in text:
        raise MIMEBuilderValidationError(
            f"{field_name} contains newlines (header injection not allowed)."
        )
    
    if not allow_empty and not text.strip():
        raise MIMEBuilderValidationError(f"{field_name} cannot be empty.")
    
    return text


def _validate_email_list(email_list, field_name):
    """Validate a list of email addresses."""
    if email_list is None:
        return None
    
    if not isinstance(email_list, (list, tuple)):
        raise MIMEBuilderValidationError(f"{field_name} must be a list of email addresses.")
    
    if not email_list:
        return None
    
    return [_validate_email_address(addr, f"{field_name}[{i}]") for i, addr in enumerate(email_list)]


def build_mime_message(sender, recipients, subject, html_body, text_body=None, cc=None, bcc=None):
    """
    Construct a standards-compliant MIME/RFC 2822 email message.
    
    Args:
        sender (str): Sender email address.
        recipients (str or list): Recipient email address(es). Can be a single string or list.
        subject (str): Email subject.
        html_body (str): HTML email body.
        text_body (str, optional): Plain-text alternative body. If None, auto-generated from HTML.
        cc (list, optional): CC recipients.
        bcc (list, optional): BCC recipients.
    
    Returns:
        email.message.Message: The MIME message object, ready for sending.
    
    Raises:
        MIMEBuilderValidationError: If email addresses or text contain invalid characters.
        MIMEBuilderError: If message construction fails.
    """
    try:
        # Validate all inputs
        sender = _validate_email_address(sender, "sender")
        
        # Normalize recipients to list
        if isinstance(recipients, str):
            recipients = [recipients]
        recipients = _validate_email_list(recipients, "recipients")
        
        if not recipients:
            raise MIMEBuilderValidationError("At least one recipient must be provided.")
        
        subject = _validate_text(subject, "subject")
        html_body = _validate_text(html_body, "html_body", allow_newlines=True)
        
        if text_body is not None:
            text_body = _validate_text(text_body, "text_body", allow_empty=True, allow_newlines=True)
        
        cc = _validate_email_list(cc, "cc")
        bcc = _validate_email_list(bcc, "bcc")
        
        # Generate plain-text alternative if not provided
        if not text_body:
            text_body = _generate_plain_text_from_html(html_body)
        
        # Create multipart/alternative message (most clients prefer HTML)
        msg = MIMEMultipart("alternative")
        
        # Set headers
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        if cc:
            msg["Cc"] = ", ".join(cc)
        
        # BCC is not included in headers (by design) but affects recipients list for sending
        # The caller is responsible for providing BCC addresses to the SMTP/API layer
        
        # Subject may contain UTF-8; use Header encoding if needed
        msg["Subject"] = Header(subject, "utf-8")
        
        # Attach plain-text alternative first (least preferred)
        text_part = MIMEText(text_body, "plain", "utf-8")
        msg.attach(text_part)
        
        # Attach HTML alternative (preferred)
        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)
        
        return msg
    
    except MIMEBuilderValidationError:
        raise
    except Exception as error:
        raise MIMEBuilderError(f"Failed to construct MIME message: {str(error)}") from error


def message_to_base64url(msg):
    """
    Convert a MIME message to base64url encoding for Gmail API.
    
    Args:
        msg (email.message.Message): The MIME message object.
    
    Returns:
        str: The message encoded as base64url (RFC 4648 without padding).
    """
    try:
        # Convert message to string (RFC 2822 format)
        msg_str = msg.as_string()
        
        # Encode to bytes
        msg_bytes = msg_str.encode("utf-8")
        
        # Base64url encode (RFC 4648)
        b64_bytes = base64.urlsafe_b64encode(msg_bytes)
        
        # Return as string, removing padding
        return b64_bytes.decode("ascii").rstrip("=")
    except Exception as error:
        raise MIMEBuilderError(f"Failed to encode message to base64url: {str(error)}") from error


def message_to_string(msg):
    """
    Convert a MIME message to RFC 2822 string format.
    
    Args:
        msg (email.message.Message): The MIME message object.
    
    Returns:
        str: The message as an RFC 2822 string.
    """
    return msg.as_string()


def message_recipients_list(msg):
    """
    Extract all recipients from a MIME message (To, Cc, Bcc).
    
    Args:
        msg (email.message.Message): The MIME message object.
    
    Returns:
        list: All recipient email addresses.
    """
    recipients = []
    
    # To recipients
    to = msg.get("To", "")
    if to:
        recipients.extend([addr.strip() for addr in to.split(",")])
    
    # Cc recipients
    cc = msg.get("Cc", "")
    if cc:
        recipients.extend([addr.strip() for addr in cc.split(",")])
    
    # BCC is not in headers, so caller must track separately
    return recipients


def _generate_plain_text_from_html(html):
    """
    Generate a basic plain-text alternative from HTML body.
    
    This is a simple fallback that strips HTML tags and preserves text.
    For production use, consider a more sophisticated library like html2text.
    
    Args:
        html (str): HTML body text.
    
    Returns:
        str: Plain-text representation.
    """
    # Remove script and style tags and their content
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # Replace common block elements with newlines
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</br>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    # Decode HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    
    # Clean up excessive whitespace
    text = re.sub(r"\n\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    
    return text
