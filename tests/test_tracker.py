"""Tests for email tracker module."""
import pytest
import asyncio
from src.outreach.tracker import EmailTracker, ReplyDetector


@pytest.fixture
def tracker():
    """Create EmailTracker instance."""
    return EmailTracker()


@pytest.fixture
def detector():
    """Create ReplyDetector instance."""
    return ReplyDetector()


def test_generate_tracking_pixel(tracker):
    """Test tracking pixel generation."""
    pixel = tracker.generate_tracking_pixel(123)
    assert "img" in pixel
    assert "123" in pixel
    assert "width=\"1\"" in pixel


def test_wrap_links(tracker):
    """Test link wrapping for click tracking."""
    html = '<a href="https://example.com">Click here</a>'
    wrapped = tracker.wrap_links(123, html)
    assert "track/click/123" in wrapped
    assert "example.com" in wrapped


def test_wrap_links_no_href(tracker):
    """Test link wrapping with no href."""
    html = '<p>No links here</p>'
    wrapped = tracker.wrap_links(123, html)
    assert wrapped == html


def test_parse_replyInterested(detector):
    """Test reply parsing for interested intent."""
    reply = "I'm interested in learning more about your services."
    result = detector.parse_reply(reply)
    assert result["intent"] == "interested"


def test_parse_reply_not_interested(detector):
    """Test reply parsing for not interested intent."""
    reply = "No thanks, I'm not interested in this."
    result = detector.parse_reply(reply)
    assert result["intent"] == "not_interested"


def test_parse_reply_question(detector):
    """Test reply parsing for question intent."""
    reply = "How much does this cost?"
    result = detector.parse_reply(reply)
    assert result["intent"] == "question"


def test_parse_reply_schedule(detector):
    """Test reply parsing for schedule intent."""
    reply = "Let's schedule a call for next week."
    result = detector.parse_reply(reply)
    assert result["intent"] == "schedule"


def test_parse_reply_positive_sentiment(detector):
    """Test reply parsing for positive sentiment."""
    reply = "This is great! I love it."
    result = detector.parse_reply(reply)
    assert result["sentiment"] == "positive"


def test_parse_reply_negative_sentiment(detector):
    """Test reply parsing for negative sentiment."""
    reply = "This is terrible and I hate it."
    result = detector.parse_reply(reply)
    assert result["sentiment"] == "negative"


def test_parse_reply_neutral_sentiment(detector):
    """Test reply parsing for neutral sentiment."""
    reply = "Thanks for the information."
    result = detector.parse_reply(reply)
    assert result["sentiment"] == "neutral"