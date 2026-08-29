"""Tests for the MIME builder module."""

import base64
import email
import pytest

from services.mime_builder import (
    build_mime_message,
    message_to_base64url,
    message_to_string,
    message_recipients_list,
    MIMEBuilderError,
    MIMEBuilderValidationError,
)


class TestBasicMessageConstruction:
    """Test basic MIME message construction."""
    
    def test_build_simple_message(self):
        """Test building a simple email message."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML body</p>"
        )
        
        assert msg is not None
        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "recipient@example.com"
        assert msg["Subject"] == "Test Subject"
    
    def test_build_with_single_recipient_string(self):
        """Test that single recipient as string is accepted."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Body</p>"
        )
        assert msg["To"] == "recipient@example.com"
    
    def test_build_with_multiple_recipients(self):
        """Test message with multiple recipients."""
        recipients = ["recipient1@example.com", "recipient2@example.com"]
        msg = build_mime_message(
            sender="sender@example.com",
            recipients=recipients,
            subject="Test",
            html_body="<p>Body</p>"
        )
        
        to_header = msg["To"]
        assert "recipient1@example.com" in to_header
        assert "recipient2@example.com" in to_header
    
    def test_build_with_cc(self):
        """Test message with CC recipients."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            cc=["cc1@example.com", "cc2@example.com"]
        )
        
        cc_header = msg["Cc"]
        assert "cc1@example.com" in cc_header
        assert "cc2@example.com" in cc_header
    
    def test_bcc_not_in_headers(self):
        """Test that BCC recipients are not included in message headers."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            bcc=["bcc@example.com"]
        )
        
        # BCC should not appear in headers
        assert "bcc@example.com" not in msg.as_string()
    
    def test_subject_with_unicode(self):
        """Test message with Unicode subject."""
        subject = "Résumé for 2026-10-11 प्रोग्राम"
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject=subject,
            html_body="<p>Body</p>"
        )
        
        # Subject is encoded with Header class
        assert msg["Subject"] is not None


class TestUnicode:
    """Test Unicode handling in MIME messages."""
    
    def test_html_body_with_unicode(self):
        """Test HTML body containing Unicode characters."""
        html_body = "<p>Héllo Wørld! 你好</p>"
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body=html_body
        )
        
        msg_str = msg.as_string()
        assert "utf-8" in msg_str.lower()
    
    def test_unicode_in_subject_and_body(self):
        """Test Unicode in both subject and body."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="पाठ विषय",
            html_body="<p>Тело сообщения</p>"
        )
        
        assert msg is not None
        msg_str = msg.as_string()
        assert msg_str is not None
    
    def test_text_body_with_unicode(self):
        """Test plain-text body with Unicode."""
        text_body = "Plain text with Unicode: Ñoño, Übermensch, 北京"
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body=text_body
        )
        
        msg_str = msg.as_string()
        assert msg_str is not None


class TestHTMLPreservation:
    """Test that HTML content is preserved correctly."""
    
    def test_html_content_survives_mime_construction(self):
        """Test that HTML content is not corrupted."""
        html = """<html><body>
        <p>Hello <strong>World</strong></p>
        <img src="https://example.com/image.jpg" />
        <a href="https://example.com">Link</a>
        </body></html>"""
        
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body=html
        )
        
        # Extract the HTML part and decode it
        parts = msg.get_payload()
        html_part = parts[1]  # HTML is the second part in multipart/alternative
        html_content = html_part.get_payload(decode=True).decode("utf-8")
        
        # HTML should be preserved
        assert "<strong>World</strong>" in html_content
        assert 'href="https://example.com"' in html_content
    
    def test_html_not_escaped_in_mime(self):
        """Test that HTML is not HTML-escaped in MIME."""
        html = '<p>Test &amp; verify</p>'
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body=html
        )
        
        # Extract the HTML part and decode it
        parts = msg.get_payload()
        html_part = parts[1]
        html_content = html_part.get_payload(decode=True).decode("utf-8")
        
        # HTML entities should be preserved (not double-escaped)
        assert '<p>Test &amp; verify</p>' in html_content
    
    def test_css_in_html_preserved(self):
        """Test that CSS in HTML is preserved."""
        html = """<html><head><style>
        .container { width: 100%; }
        </style></head><body>Content</body></html>"""
        
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body=html
        )
        
        # Extract the HTML part and decode it
        parts = msg.get_payload()
        html_part = parts[1]
        html_content = html_part.get_payload(decode=True).decode("utf-8")
        
        # CSS should be preserved
        assert "width: 100%;" in html_content


class TestMIMEStructure:
    """Test MIME message structure."""
    
    def test_multipart_alternative_structure(self):
        """Test that message is multipart/alternative."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="Plain text"
        )
        
        assert msg.is_multipart()
        assert msg.get_content_type() == "multipart/alternative"
    
    def test_plain_text_alternative_present(self):
        """Test that plain-text alternative is included."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="Plain text"
        )
        
        parts = msg.get_payload()
        assert len(parts) == 2
        
        # First part is plain text
        assert parts[0].get_content_type() == "text/plain"
        assert "Plain text" in parts[0].get_payload(decode=True).decode("utf-8")
        
        # Second part is HTML
        assert parts[1].get_content_type() == "text/html"
    
    def test_html_alternative_present(self):
        """Test that HTML alternative is included."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>HTML Body</p>"
        )
        
        parts = msg.get_payload()
        html_part = parts[1]
        assert html_part.get_content_type() == "text/html"
        html_content = html_part.get_payload(decode=True).decode("utf-8")
        assert "<p>HTML Body</p>" in html_content
    
    def test_auto_generated_plain_text(self):
        """Test auto-generation of plain-text from HTML when not provided."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>This is a paragraph</p><br><a href='#'>Link</a>"
        )
        
        parts = msg.get_payload()
        text_part = parts[0]
        text_content = text_part.get_payload(decode=True).decode("utf-8")
        
        # Should contain text but not HTML tags
        assert "This is a paragraph" in text_content
        assert "<p>" not in text_content
        assert "<a" not in text_content


class TestEncoding:
    """Test encoding and format compliance."""
    
    def test_message_parseable_as_rfc2822(self):
        """Test that generated message can be parsed as RFC 2822."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Body</p>"
        )
        
        msg_str = message_to_string(msg)
        parsed = email.message_from_string(msg_str)
        
        assert parsed["From"] == "sender@example.com"
        assert "recipient@example.com" in parsed["To"]
    
    def test_base64url_encoding(self):
        """Test conversion to base64url format for Gmail API."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>"
        )
        
        b64url = message_to_base64url(msg)
        
        # Should be valid base64url (no padding)
        assert isinstance(b64url, str)
        assert "=" not in b64url  # base64url removes padding
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in b64url)
    
    def test_base64url_can_be_decoded(self):
        """Test that base64url output can be decoded back."""
        original_msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>"
        )
        
        b64url = message_to_base64url(original_msg)
        
        # Add padding back
        padding = 4 - (len(b64url) % 4)
        if padding != 4:
            b64url_padded = b64url + ("=" * padding)
        else:
            b64url_padded = b64url
        
        # Decode
        decoded_bytes = base64.urlsafe_b64decode(b64url_padded)
        decoded_str = decoded_bytes.decode("utf-8")
        
        # Parse as RFC 2822
        decoded_msg = email.message_from_string(decoded_str)
        assert decoded_msg["From"] == "sender@example.com"
    
    def test_utf8_encoding_used(self):
        """Test that UTF-8 encoding is used for bodies."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Caf\u00e9</p>"
        )
        
        msg_str = message_to_string(msg)
        
        # Should specify UTF-8 encoding
        assert "charset=\"utf-8\"" in msg_str.lower() or "charset='utf-8'" in msg_str.lower()


class TestSecurity:
    """Test security validations (header injection prevention)."""
    
    def test_reject_newline_in_sender(self):
        """Test that newlines in sender are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com\nBcc: attacker@example.com",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_newline_in_recipient(self):
        """Test that newlines in recipient are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient@example.com\nBcc: attacker@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_newline_in_subject(self):
        """Test that newlines in subject are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient@example.com",
                subject="Test\nBcc: attacker@example.com",
                html_body="<p>Body</p>"
            )
    
    def test_reject_carriage_return_in_sender(self):
        """Test that CR in sender is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com\rBcc: attacker@example.com",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_null_byte_in_sender(self):
        """Test that null bytes in sender are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com\x00",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_newline_in_cc(self):
        """Test that newlines in CC are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>",
                cc=["cc@example.com\nBcc: attacker@example.com"]
            )
    
    def test_reject_newline_in_bcc(self):
        """Test that newlines in BCC are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>",
                bcc=["bcc@example.com\nTo: attacker@example.com"]
            )
    
    def test_reject_multiple_addresses_in_single_recipient(self):
        """Test that comma-separated addresses in a single field are rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient1@example.com, recipient2@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )


class TestValidation:
    """Test input validation."""
    
    def test_reject_non_string_sender(self):
        """Test that non-string sender is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender=123,
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_empty_sender(self):
        """Test that empty sender is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_empty_recipients(self):
        """Test that empty recipients list is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients=[],
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_reject_empty_subject(self):
        """Test that empty subject is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient@example.com",
                subject="",
                html_body="<p>Body</p>"
            )
    
    def test_reject_empty_html_body(self):
        """Test that empty HTML body is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="recipient@example.com",
                subject="Test",
                html_body=""
            )
    
    def test_allow_empty_text_body(self):
        """Test that empty text body is allowed (will auto-generate)."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body=""
        )
        assert msg is not None
    
    def test_invalid_email_format_sender(self):
        """Test that invalid email format in sender is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="not-an-email",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_invalid_email_format_recipient(self):
        """Test that invalid email format in recipient is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example.com",
                recipients="not-an-email",
                subject="Test",
                html_body="<p>Body</p>"
            )
    
    def test_multiple_at_signs_rejected(self):
        """Test that email with multiple @ signs is rejected."""
        with pytest.raises(MIMEBuilderValidationError):
            build_mime_message(
                sender="sender@example@com",
                recipients="recipient@example.com",
                subject="Test",
                html_body="<p>Body</p>"
            )


class TestRecipientsExtraction:
    """Test recipient extraction from messages."""
    
    def test_extract_to_recipients(self):
        """Test extraction of To recipients."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients=["recipient1@example.com", "recipient2@example.com"],
            subject="Test",
            html_body="<p>Body</p>"
        )
        
        recipients = message_recipients_list(msg)
        assert "recipient1@example.com" in recipients
        assert "recipient2@example.com" in recipients
    
    def test_extract_cc_recipients(self):
        """Test extraction of CC recipients."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            cc=["cc1@example.com", "cc2@example.com"]
        )
        
        recipients = message_recipients_list(msg)
        assert "cc1@example.com" in recipients
        assert "cc2@example.com" in recipients
    
    def test_bcc_not_extractable_from_headers(self):
        """Test that BCC is not extractable from message headers (as expected)."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients="recipient@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            bcc=["bcc@example.com"]
        )
        
        recipients = message_recipients_list(msg)
        # BCC should NOT be in extracted recipients (it's not in headers)
        assert "bcc@example.com" not in recipients


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_full_workflow_render_and_send(self):
        """Test complete workflow: create message, convert to RFC 2822, then to base64url."""
        # This mimics the real workflow
        html = """<html><body>
        <h1>Event Notification</h1>
        <p>Dear Recipient,</p>
        <p>You are invited to our event!</p>
        <a href="https://example.com/register">Register</a>
        </body></html>"""
        
        msg = build_mime_message(
            sender="events@brahmand.com",
            recipients=["student@example.com"],
            subject="You're Invited to Our Event",
            html_body=html,
            cc=["admin@brahmand.com"]
        )
        
        # Convert to RFC 2822
        rfc_msg = message_to_string(msg)
        assert rfc_msg is not None
        
        # Convert to base64url (for Gmail API)
        b64url = message_to_base64url(msg)
        assert b64url is not None
        assert "=" not in b64url
    
    def test_multiple_recipients_and_cc(self):
        """Test message with multiple recipients and CC."""
        msg = build_mime_message(
            sender="sender@example.com",
            recipients=["r1@example.com", "r2@example.com", "r3@example.com"],
            subject="Group Notification",
            html_body="<p>Message for all</p>",
            cc=["cc1@example.com", "cc2@example.com"]
        )
        
        msg_str = message_to_string(msg)
        assert "r1@example.com" in msg_str
        assert "r2@example.com" in msg_str
        assert "r3@example.com" in msg_str
        assert "cc1@example.com" in msg_str
        assert "cc2@example.com" in msg_str
    
    def test_event_email_simulation(self):
        """Test with realistic event email content."""
        subject = "HELIOTRACK 2.0 - Explore the Night Sky"
        html = """<html><body>
        <img src="https://res.cloudinary.com/example/poster.jpg" />
        <h1>HELIOTRACK 2.0</h1>
        <p>Join us for an astronomy event featuring telescope viewing and expert talks.</p>
        <h2>Schedule</h2>
        <ul>
        <li>10:00 AM - Morning session</li>
        <li>12:00 PM - Lunch break</li>
        <li>2:00 PM - Afternoon workshop</li>
        </ul>
        <p><a href="https://example.com/register">Register Now</a></p>
        </body></html>"""
        
        msg = build_mime_message(
            sender="events@pdeu.edu",
            recipients="student@example.com",
            subject=subject,
            html_body=html,
            cc=["admin@pdeu.edu"]
        )
        
        assert msg is not None
        b64url = message_to_base64url(msg)
        assert b64url is not None
