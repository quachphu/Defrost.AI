"""
Tests for EmailOutreachTool.verify() — the server-side confirmation step.

The critical behavior: verify() must return False when SendGrid reports failure.
If this breaks, the agent will think emails were delivered when they weren't,
and will never retry via phone or SMS.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from defrosted.agents.tools.email_tool import EmailOutreachTool


@pytest.fixture
def email_tool():
    settings = MagicMock()
    settings.sendgrid_api_key = "test-key"
    settings.outreach_from_email = "agent@defrosted.ai"
    rate_limiter = AsyncMock()
    return EmailOutreachTool(settings=settings, rate_limiter=rate_limiter)


@pytest.mark.asyncio
async def test_verify_returns_true_on_delivered(email_tool):
    """The happy path: SendGrid confirms delivery."""
    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "messages": [{"status": "delivered"}]
    }
    email_tool._client.client.messages = MagicMock()
    email_tool._client.client.messages._("test-msg-id").get.return_value = mock_response

    result = await email_tool.verify("test-msg-id")
    assert result is True


@pytest.mark.asyncio
async def test_verify_returns_false_on_bounced(email_tool):
    """If the email bounced, we must not treat it as delivered."""
    mock_response = MagicMock()
    mock_response.to_dict.return_value = {
        "messages": [{"status": "bounced"}]
    }
    email_tool._client.client.messages = MagicMock()
    email_tool._client.client.messages._("test-msg-id").get.return_value = mock_response

    result = await email_tool.verify("test-msg-id")
    assert result is False


@pytest.mark.asyncio
async def test_verify_returns_false_on_timeout(email_tool, monkeypatch):
    """
    If SendGrid never confirms after 5 attempts, return False.
    We don't want the agent stuck forever waiting for a confirmation.
    """
    async def slow_sleep(seconds):
        pass  # don't actually sleep in tests

    monkeypatch.setattr("asyncio.sleep", slow_sleep)

    mock_response = MagicMock()
    mock_response.to_dict.return_value = {"messages": []}   # empty — not yet processed
    email_tool._client.client.messages = MagicMock()
    email_tool._client.client.messages._("test-msg-id").get.return_value = mock_response

    result = await email_tool.verify("test-msg-id")
    assert result is False
