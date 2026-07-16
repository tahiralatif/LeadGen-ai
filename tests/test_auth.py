"""Tests for authentication module."""
import pytest
from src.auth.jwt import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token
)


def test_hash_password():
    """Test password hashing."""
    password = "testpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 0


def test_verify_password():
    """Test password verification."""
    password = "testpassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "1"}
    token = create_access_token(data)
    assert token is not None
    assert len(token) > 0


def test_decode_token():
    """Test JWT token decoding."""
    data = {"sub": "1"}
    token = create_access_token(data)
    payload = decode_token(token)
    assert payload["sub"] == "1"
    assert "exp" in payload


def test_decode_invalid_token():
    """Test decoding invalid token."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        decode_token("invalid.token.here")