"""Tests for authentication."""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def set_auth_env(monkeypatch):
    monkeypatch.setenv("APP_EMAIL", "test@example.com")
    monkeypatch.setenv("APP_PASSWORD", "secret123")
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key-for-jwt")


class TestAuthModule:
    def test_verify_credentials_correct(self):
        from steps.auth import verify_credentials
        assert verify_credentials("test@example.com", "secret123") is True

    def test_verify_credentials_wrong_password(self):
        from steps.auth import verify_credentials
        assert verify_credentials("test@example.com", "wrong") is False

    def test_verify_credentials_wrong_email(self):
        from steps.auth import verify_credentials
        assert verify_credentials("wrong@example.com", "secret123") is False

    def test_create_token(self):
        from steps.auth import create_token
        token = create_token("test@example.com")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_token_valid(self):
        from steps.auth import create_token, verify_token
        token = create_token("test@example.com")
        email = verify_token(token)
        assert email == "test@example.com"

    def test_verify_token_invalid(self):
        from steps.auth import verify_token
        assert verify_token("garbage-token") is None

    def test_verify_token_empty(self):
        from steps.auth import verify_token
        assert verify_token("") is None
