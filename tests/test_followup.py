"""Tests for follow-up sequence module."""
import pytest
import asyncio
from src.outreach.followup import FollowUpSequence


@pytest.fixture
def followup():
    """Create FollowUpSequence instance."""
    return FollowUpSequence()


def test_default_sequence(followup):
    """Test default sequence has 3 steps."""
    assert len(followup.default_sequence) == 3


def test_default_sequence_delays(followup):
    """Test default sequence delays."""
    delays = [step["delay_hours"] for step in followup.default_sequence]
    assert delays == [0, 48, 96]


def test_sequence_structure(followup):
    """Test sequence structure."""
    for step in followup.default_sequence:
        assert "step" in step
        assert "delay_hours" in step
        assert "subject" in step
        assert "template" in step


def test_sequence_step_numbers(followup):
    """Test sequence step numbers are sequential."""
    steps = [step["step"] for step in followup.default_sequence]
    assert steps == [1, 2, 3]


def test_sequence_delay_order(followup):
    """Test sequence delays are in order."""
    delays = [step["delay_hours"] for step in followup.default_sequence]
    assert delays == sorted(delays)