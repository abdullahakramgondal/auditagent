"""A wait between two tries of a Gemini call must be visible in the log (TODO item 38)."""

import logging

import pytest
from google.genai import errors
from pydantic import BaseModel

from auditagent.llm.base import LLMTransientError
from auditagent.llm.gemini import GeminiProvider

LOGGER = "auditagent.llm.gemini"
GOOD = '{"percent": 10}'


class Demo(BaseModel):
    percent: int


class FakeResponse:
    """Stands in for the SDK response: only the .text attribute is used."""

    def __init__(self, text):
        self.text = text


class FakeModels:
    """Stands in for client.models: plays back prepared outcomes."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def generate_content(self, model, contents, config):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


class FakeClient:
    """Stands in for genai.Client so tests never touch the network."""

    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


def api_error(code):
    """The SDK's own error type for a given HTTP status code."""
    return errors.APIError(code, {"error": {"message": "x", "status": "RESOURCE_EXHAUSTED"}})


def make_provider(outcomes, max_retries=3):
    """A GeminiProvider wired to a fake client, with no waiting between tries."""
    client = FakeClient(outcomes)
    return GeminiProvider(
        "unused", "gemini-test", client=client, retry_wait=0, max_retries=max_retries
    )


def test_each_retry_is_logged_with_the_error_and_the_try_number(caplog):
    provider = make_provider([api_error(429), api_error(503), GOOD])
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        assert provider.generate_json("s", "p", Demo) == GOOD
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 2
    assert "429" in messages[0] and "try 2 of 3" in messages[0]
    assert "503" in messages[1] and "try 3 of 3" in messages[1]
    assert provider.retries == 2 and provider.seconds_waited == 0.0


def test_a_call_that_works_at_once_logs_nothing(caplog):
    provider = make_provider([GOOD])
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        provider.generate_json("s", "p", Demo)
    assert caplog.records == [] and provider.retries == 0


def test_a_call_that_never_succeeds_logs_one_wait_per_retry_and_then_gives_up(caplog):
    provider = make_provider([api_error(429)] * 3, max_retries=3)
    with caplog.at_level(logging.WARNING, logger=LOGGER), pytest.raises(LLMTransientError):
        provider.generate_json("s", "p", Demo)
    assert len(caplog.records) == 2  # no wait after the last try
    assert provider.retries == 2
