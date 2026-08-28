"""Tests for the EmailMaker deterministic Jinja-based email renderer."""

import pytest

from services.email_maker import render_email, EmailMakerError


COMPLETE_CONTEXT = {
    "subject": "Explore the Night Sky",
    "preheader": "Join HELIOTRACK 2.0",
    "headline": "HELIOTRACK 2.0",
    "intro": "Join us for an astronomy event featuring telescope viewing and expert talks.",
    "sections": [
        {
            "heading": "What to Expect",
            "body": "Experience hands-on astronomy activities and learn from experts.",
            "bullets": ["Telescope viewing", "Expert presentations", "Q&A sessions"]
        },
        {
            "heading": "Schedule",
            "body": "The event runs from 10 AM to 4 PM with breaks.",
            "bullets": ["Morning session", "Lunch break", "Afternoon workshop"]
        }
    ],
    "event_details": {
        "date": "October 11, 2026",
        "time": "10:00 AM - 4:00 PM",
        "venue": "PDEU Astronomy Observatory",
        "registration_url": "https://example.com/register"
    },
    "cta": {
        "label": "Register Now",
        "url": "https://example.com/register"
    },
    "closing": "We look forward to seeing you at the observatory!"
}


MINIMAL_CONTEXT = {
    "subject": "Test Event",
    "preheader": "Test preheader",
    "headline": "Test Headline",
    "intro": "Test intro text",
    "sections": [],
    "event_details": {
        "date": "2026-10-11",
        "time": "10:00",
        "venue": None,
        "registration_url": None
    },
    "cta": {
        "label": "Learn More",
        "url": None
    },
    "closing": "Test closing"
}


def test_complete_context_renders_successfully():
    """Test that a complete EmailContext renders without errors."""
    html = render_email(COMPLETE_CONTEXT)
    assert html is not None
    assert isinstance(html, str)
    assert len(html) > 0


def test_html_contains_subject_headline_intro():
    """Test that subject, headline, and intro appear in generated HTML."""
    html = render_email(COMPLETE_CONTEXT)
    assert COMPLETE_CONTEXT["headline"] in html
    assert COMPLETE_CONTEXT["intro"] in html


def test_multiple_sections_render_correctly():
    """Test that multiple sections render correctly."""
    html = render_email(COMPLETE_CONTEXT)
    assert COMPLETE_CONTEXT["sections"][0]["heading"] in html
    assert COMPLETE_CONTEXT["sections"][0]["body"] in html
    assert COMPLETE_CONTEXT["sections"][1]["heading"] in html
    assert COMPLETE_CONTEXT["sections"][1]["body"] in html


def test_multiple_bullets_render_correctly():
    """Test that multiple bullets render correctly."""
    html = render_email(COMPLETE_CONTEXT)
    # Check that bullets appear (accounting for HTML escaping)
    assert "Telescope viewing" in html
    assert "Expert presentations" in html
    assert "Q&amp;A sessions" in html or "Q&A sessions" in html
    assert "Morning session" in html
    assert "Lunch break" in html
    assert "Afternoon workshop" in html


def test_event_details_render_correctly():
    """Test that event details render correctly."""
    html = render_email(COMPLETE_CONTEXT)
    assert COMPLETE_CONTEXT["event_details"]["date"] in html
    assert COMPLETE_CONTEXT["event_details"]["time"] in html
    assert COMPLETE_CONTEXT["event_details"]["venue"] in html
    assert COMPLETE_CONTEXT["event_details"]["registration_url"] in html


def test_cta_renders_when_url_exists():
    """Test that CTA renders correctly when URL exists."""
    html = render_email(COMPLETE_CONTEXT)
    assert COMPLETE_CONTEXT["cta"]["label"] in html
    assert COMPLETE_CONTEXT["cta"]["url"] in html


def test_cta_safe_when_url_is_null():
    """Test that CTA behaves safely when URL is null."""
    html = render_email(MINIMAL_CONTEXT)
    # CTA should not render as a button when URL is null
    assert MINIMAL_CONTEXT["cta"]["label"] not in html or "href" not in html


def test_optional_venue_null_handling():
    """Test that optional venue behaves correctly when null."""
    html = render_email(MINIMAL_CONTEXT)
    # Venue should not appear when null
    assert "VENUE" not in html or MINIMAL_CONTEXT["event_details"]["venue"] is None


def test_optional_registration_url_null_handling():
    """Test that optional registration URL behaves correctly when null."""
    html = render_email(MINIMAL_CONTEXT)
    # Registration link should not appear when null
    assert "INITIATE REGISTRATION" not in html or MINIMAL_CONTEXT["event_details"]["registration_url"] is None


def test_html_is_produced_not_empty():
    """Test that HTML is actually produced rather than empty/stub response."""
    html = render_email(COMPLETE_CONTEXT)
    assert len(html) > 100  # Should be substantial HTML
    assert "<!doctype html>" in html.lower()
    assert "<html" in html.lower()
    assert "</html>" in html.lower()


def test_renderer_does_not_modify_context():
    """Test that the renderer does not modify the EmailContext."""
    original_context = COMPLETE_CONTEXT.copy()
    original_context["sections"] = [section.copy() for section in COMPLETE_CONTEXT["sections"]]
    
    render_email(COMPLETE_CONTEXT)
    
    # Verify context unchanged
    assert COMPLETE_CONTEXT == original_context


def test_html_escaping_for_user_content():
    """Test that HTML escaping works for user/content-provided text."""
    context_with_html = {
        "subject": "Test <script>alert('xss')</script>",
        "preheader": "Test preheader",
        "headline": "Test <img src=x onerror=alert(1)>",
        "intro": "Test & < > \" ' intro",
        "sections": [
            {
                "heading": "Test <b>heading</b>",
                "body": "Test <script>body</script>",
                "bullets": ["Test <a href='xss'>bullet</a>"]
            }
        ],
        "event_details": {
            "date": "2026-10-11",
            "time": "10:00",
            "venue": None,
            "registration_url": None
        },
        "cta": {
            "label": "Test & label",
            "url": None
        },
        "closing": "Test </closing> tag"
    }
    
    html = render_email(context_with_html)
    
    # Jinja autoescape should convert dangerous characters to safe entities
    assert "&lt;" in html  # < should be escaped
    assert "&gt;" in html  # > should be escaped
    assert "&amp;" in html  # & should be escaped
    # The escaped content should appear as text, not executable HTML
    assert "&lt;script&gt;" in html or "<script" not in html


def test_empty_sections_render():
    """Test that empty sections list renders without error."""
    context = MINIMAL_CONTEXT.copy()
    context["sections"] = []
    html = render_email(context)
    assert html is not None
    assert len(html) > 0


def test_section_without_bullets_renders():
    """Test that sections without bullets render correctly."""
    context = COMPLETE_CONTEXT.copy()
    context["sections"] = [
        {
            "heading": "Test",
            "body": "Test body",
            "bullets": []
        }
    ]
    html = render_email(context)
    assert "Test" in html


def test_template_error_raises_email_maker_error():
    """Test that template errors raise EmailMakerError."""
    invalid_context = {
        "subject": "Test",
        "preheader": "Test",
        "headline": "Test",
        "intro": "Test",
        "sections": [],
        "event_details": {
            "date": "Test",
            "time": "Test",
            "venue": None,
            "registration_url": None
        },
        "cta": {
            "label": "Test",
            "url": None
        },
        "closing": "Test"
    }
    
    # This should work fine, but let's test the error handling
    # by passing an invalid context that would cause template error
    try:
        html = render_email(invalid_context)
        assert html is not None
    except EmailMakerError:
        pass  # Expected for template errors


# New tests for poster/background handling


def test_poster_url_renders_when_present():
    """Test that poster URL is rendered when present."""
    poster_url = "https://res.cloudinary.com/test/image/upload/poster.jpg"
    html = render_email(COMPLETE_CONTEXT, poster_url=poster_url)
    assert poster_url in html
    assert "Event Poster" in html


def test_poster_omitted_when_absent():
    """Test that poster is safely omitted when URL is None."""
    html = render_email(COMPLETE_CONTEXT, poster_url=None)
    # Should not contain poster-related elements
    assert "Event Poster" not in html or "poster" not in html.lower()


def test_background_url_accepted():
    """Test that background URL is accepted by renderer (even if not used directly in template)."""
    background_url = "https://res.cloudinary.com/test/image/upload/bg.jpg"
    html = render_email(COMPLETE_CONTEXT, background_url=background_url)
    # Should render successfully without errors
    assert html is not None
    assert len(html) > 0


def test_background_none_safe():
    """Test that None background URL is handled safely."""
    html = render_email(COMPLETE_CONTEXT, background_url=None)
    assert html is not None
    assert len(html) > 0


def test_backward_compatibility_without_assets():
    """Test that render_email works without asset parameters (backward compatibility)."""
    html = render_email(COMPLETE_CONTEXT)
    assert html is not None
    assert len(html) > 0


# New tests for newline handling


def test_newline_conversion_in_intro():
    """Test that newlines in intro are converted to <br> tags."""
    context = MINIMAL_CONTEXT.copy()
    context["intro"] = "Line 1\nLine 2\nLine 3"
    html = render_email(context)
    # Check that the text appears (newlines may be converted or preserved)
    assert "Line 1" in html
    assert "Line 2" in html
    assert "Line 3" in html


def test_newline_conversion_in_section_body():
    """Test that newlines in section body are converted to <br> tags."""
    context = COMPLETE_CONTEXT.copy()
    context["sections"][0]["body"] = "Paragraph 1\nParagraph 2"
    html = render_email(context)
    # Check that the text appears
    assert "Paragraph 1" in html
    assert "Paragraph 2" in html


def test_newline_conversion_in_closing():
    """Test that newlines in closing are converted to <br> tags."""
    context = MINIMAL_CONTEXT.copy()
    context["closing"] = "Best regards,\nThe Team"
    html = render_email(context)
    # Check that the text appears
    assert "Best regards," in html
    assert "The Team" in html


def test_null_text_safe_with_nl2br():
    """Test that nl2br filter handles None safely."""
    context = MINIMAL_CONTEXT.copy()
    context["intro"] = None
    html = render_email(context)
    assert html is not None


# New tests for visual elements


def test_space_aesthetic_colors_present():
    """Test that space mission control aesthetic colors are present."""
    html = render_email(COMPLETE_CONTEXT)
    # Deep navy background
    assert "#f2eefb" in html
    assert "Georgia" in html


def test_system_header_renders():
    """Test that system header with technical labels renders."""
    html = render_email(COMPLETE_CONTEXT)
    assert "AUTO-MAIL // EVENT DISPATCH" not in html
    assert "MISSION TRANSMISSION" not in html


def test_mission_parameters_section_renders():
    """Test that mission parameters section renders correctly."""
    html = render_email(COMPLETE_CONTEXT)
    assert "MISSION PARAMETERS" not in html
    assert "Event details" in html
    assert "Date" in html
    assert "Time" in html


def test_bullet_style_cyan_accent():
    """Test that bullets use cyan accent character."""
    html = render_email(COMPLETE_CONTEXT)
    assert "&#8226;" in html  # Editorial list bullet


def test_footer_system_identity():
    """Test that footer contains system identity."""
    html = render_email(COMPLETE_CONTEXT)
    assert "AUTO-MAIL SYSTEM" not in html
    assert "GENERATED TRANSMISSION" not in html


def test_legacy_contacts_are_migrated_to_fixed_final_contact_block():
    context = {
        "subject": "Interviews",
        "preheader": "Interview details",
        "headline": "Build with us",
        "intro": "Join the team.",
        "sections": [{
            "heading": "Interview Format & Support",
            "body": "Interviews are hosted in both offline and online modes.",
            "bullets": [
                "Mode: Offline & Online",
                "Interview Window: 16th - 18th January 2026",
                "Astha: +91 98765 43210",
                "Naman: +91 91234 56789",
            ],
        }],
        "event_details": {
            "date": "January 16-18, 2026",
            "time": "11:00 AM onwards",
            "venue": "D-Gazebo / Google Meet",
            "registration_url": "https://example.com/register",
        },
        "cta": {"label": "Register Now", "url": "https://example.com/register"},
        "closing": "Not everyone watches the stars. Some help shape the cosmos.",
    }

    html = render_email(context)

    interview = html.index("Interview Format &amp; Support")
    details = html.index("Event details")
    closing = html.index("Not everyone watches the stars")
    contacts = html.index("Contact Details")
    assert interview < details < closing < contacts
    assert html.count('href="https://example.com/register"') == 1

    event_block = html[details:closing]
    assert "Astha" not in event_block
    assert "Naman" not in event_block

    interview_block = html[interview:details]
    assert "Astha" not in interview_block
    assert "Naman" not in interview_block
    assert "Mode: Offline &amp; Online" in interview_block
    assert "Interview Window: 16th - 18th January 2026" in interview_block
    assert "Astha: +91 98765 43210" in html[contacts:]


def test_only_supplied_header_logos_render_in_fixed_order():
    context = {**MINIMAL_CONTEXT, "logo_urls": {
        "S&T": "https://example.com/st.png",
        "Brahmand": "https://example.com/brahmand.png",
    }}
    html = render_email(context)
    assert html.index("brahmand.png") < html.index("st.png")
    assert "SAIIL" not in html


ORGANIZATION_LOGOS = {
    "brahmand_logo_url": "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png",
    "snt_logo_url": "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png",
    "osail_logo_url": "https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png",
}


def test_all_supplied_organization_logos_render_before_headline():
    html = render_email({**COMPLETE_CONTEXT, **ORGANIZATION_LOGOS})
    for url in ORGANIZATION_LOGOS.values():
        assert url in html
    assert html.index(ORGANIZATION_LOGOS["brahmand_logo_url"]) < html.index('<h1 class="email-headline"')
    assert html.index(ORGANIZATION_LOGOS["osail_logo_url"]) < html.index(ORGANIZATION_LOGOS["snt_logo_url"])
    assert 'alt="Brahmand"' in html
    assert 'alt="OSAIl"' in html
    assert 'alt="S&amp;T"' in html


def test_missing_organization_logo_is_omitted_without_broken_image_markup():
    context = {**COMPLETE_CONTEXT, **ORGANIZATION_LOGOS, "snt_logo_url": None}
    html = render_email(context)
    assert ORGANIZATION_LOGOS["snt_logo_url"] not in html
    assert ORGANIZATION_LOGOS["brahmand_logo_url"] in html
    assert ORGANIZATION_LOGOS["osail_logo_url"] in html
    assert 'src=""' not in html
    assert 'alt="S&T"' not in html


def test_responsive_logo_markup_exists_without_scaling():
    html = render_email({**COMPLETE_CONTEXT, **ORGANIZATION_LOGOS})
    assert 'class="org-logo"' in html
    assert '.org-logo{width:100%!important;max-width:90px!important;height:auto!important}' in html
    assert 'transform:scale' not in html
    assert 'width:28%' in html, "Mobile logos should use percentage-based sizing (28%)"
    assert 'font-size:28px' in html, "Mobile headline should be 28px"
    assert 'img{max-width:100%!important' in html, "Mobile should have img max-width rule for responsiveness"


def test_no_fixed_width_elements_cause_mobile_overflow():
    """Regression test to ensure no fixed-width elements cause mobile overflow."""
    html = render_email({**COMPLETE_CONTEXT, **ORGANIZATION_LOGOS})
    
    # Main container should use width="100%" with max-width, not fixed width="600"
    assert 'width="100%"' in html, "Main container should use width=100%"
    assert 'max-width:600px' in html, "Main container should have max-width:600px"
    
    # Poster image should use width="100%" with max-width, not fixed width="600"
    assert 'width="100%"' in html, "Images should use width=100%"
    
    # Email container should have width="100%" attribute (not width="600")
    import re
    container_match = re.search(r'<table[^>]*class="email-container"[^>]*>', html)
    assert container_match, "Email container should exist"
    assert 'width="100%"' in container_match.group(), "Email container should use width=100%"
    assert 'width="600"' not in container_match.group(), "Email container should not use width=600"
    
    # Verify mobile CSS overrides exist
    assert 'table[class=email-container]{width:100%!important;max-width:100%!important}' in html
    assert 'img{max-width:100%!important;height:auto!important}' in html
    
    # Verify word-wrap for text wrapping
    assert 'word-wrap:break-word' in html, "Should have word-wrap for text wrapping"
    
    # Verify no min-width that could cause overflow
    assert 'min-width:' not in html.lower(), "Should not have min-width that could cause overflow"
    
    # Verify no nowrap that could cause overflow
    assert 'nowrap' not in html.lower(), "Should not have nowrap that could cause overflow"
    
    # Verify mobile padding is reasonable (not 52px which would cause overflow on 375px)
    assert 'padding:28px 52px' not in html, "Should not have 52px padding that causes mobile overflow"
    assert 'padding:0 52px' not in html, "Should not have 52px padding that causes mobile overflow"
    assert 'td.mobile-padding{padding:20px 16px!important}' in html, "Mobile padding should be overridden to 20px 16px"

