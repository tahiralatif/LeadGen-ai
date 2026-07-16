"""Tests for email finder module."""
import pytest
import asyncio
from src.discovery.email_finder import EmailFinder


@pytest.fixture
def finder():
    """Create EmailFinder instance."""
    return EmailFinder()


def test_guess_email_patterns(finder):
    """Test email pattern guessing."""
    patterns = finder.guess_email_patterns("example.com", "John", "Smith")
    assert len(patterns) > 0
    assert any(p["email"] == "john@example.com" for p in patterns)
    assert any(p["email"] == "info@example.com" for p in patterns)


def test_guess_email_patterns_with_domain(finder):
    """Test pattern guessing with specific domain."""
    patterns = finder.guess_email_patterns("test.com", "Jane", "Doe")
    assert any("test.com" in p["email"] for p in patterns)


@pytest.mark.asyncio
async def test_find_emails_from_website(finder):
    """Test finding emails from website."""
    # This is a basic test - in production, mock the HTTP calls
    emails = await finder.find_emails_from_website("https://example.com")
    assert isinstance(emails, list)


@pytest.mark.asyncio
async def test_find_emails_for_lead(finder):
    """Test finding emails for a lead."""
    lead = {
        "company": "Example Corp",
        "website": "https://example.com"
    }
    result = await finder.find_emails_for_lead(lead)
    assert "email" in result or "email_source" in result