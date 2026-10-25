import pytest
from google.genai import errors
from pydantic import BaseModel, Field

from auditagent.llm.base import LLMError, LLMOutputError, LLMTransientError, generate_structured
from auditagent.llm.fake import ScriptedProvider
from auditagent.llm.gemini import GeminiProvider


class Demo(BaseModel):
    percent: int = Field(ge=1, le=100)
    deadline: str


GOOD = '{"percent": 10, "deadline": "2026-10-15"}'


def test_valid_answer_is_returned_after_one_call():
    """A valid first answer is accepted as it is, with no extra model calls."""
    provider = ScriptedProvider([GOOD])
    result = generate_structured(provider, "sys", "prompt", Demo)
    assert result == Demo(percent=10, deadline="2026-10-15")
    assert len(provider.prompts) == 1


def test_broken_json_is_sent_back_and_fixed():
    """Unparseable output is returned to the model with the reason, and the second answer is used."""
    provider = ScriptedProvider(["not json at all", GOOD])
    result = generate_structured(provider, "sys", "prompt", Demo)
    assert result.percent == 10
    assert len(provider.prompts) == 2
    assert "rejected" in provider.prompts[1] and "not json at all" in provider.prompts[1]


def test_out_of_range_value_is_rejected_with_the_reason():
    """A value that breaks the schema (percent 150) is rejected and the retry names the field."""
    provider = ScriptedProvider(['{"percent": 150, "deadline": "x"}', GOOD])
    generate_structured(provider, "sys", "prompt", Demo)
    assert "percent" in provider.prompts[1]


def test_gives_up_after_max_attempts():
    """After max_attempts bad answers we raise an error instead of looping forever."""
    provider = ScriptedProvider(["bad", "bad", "bad"])
    with pytest.raises(LLMOutputError):
        generate_structured(provider, "sys", "prompt", Demo, max_attempts=3)
    assert len(provider.prompts) == 3


class FakeResponse:
    """Stands in for the SDK response: only the .text attribute is used."""

    def __init__(self, text):
        self.text = text


class FakeModels:
    """Stands in for client.models: plays back prepared outcomes and counts the calls."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


class FakeClient:
    """Stands in for genai.Client so tests never touch the network."""

    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


def api_error(code):
    """Build the SDK's own error type for a given HTTP status code."""
    return errors.APIError(code, {"error": {"message": "x", "status": "SOME_STATUS"}})


def make_provider(outcomes, max_retries=3):
    """A GeminiProvider wired to a fake client, with no waiting between retries."""
    client = FakeClient(outcomes)
    provider = GeminiProvider(
        "unused", "gemini-test", client=client, retry_wait=0, max_retries=max_retries
    )
    return provider, client


def test_gemini_retries_rate_limits_then_succeeds():
    """Two temporary failures (429, 503) are retried and the third call succeeds."""
    provider, client = make_provider([api_error(429), api_error(503), GOOD])
    assert provider.generate_json("s", "p", Demo) == GOOD
    assert client.models.calls == 3


def test_gemini_does_not_retry_a_bad_request():
    """A 400 error is our mistake, so retrying would only waste calls: fail at once."""
    provider, client = make_provider([api_error(400), GOOD])
    with pytest.raises(LLMError) as info:
        provider.generate_json("s", "p", Demo)
    assert not isinstance(info.value, LLMTransientError)
    assert client.models.calls == 1


def test_gemini_gives_up_when_rate_limit_never_clears():
    """If the rate limit never clears, the provider stops after max_retries and says so."""
    provider, client = make_provider([api_error(429)] * 3, max_retries=3)
    with pytest.raises(LLMTransientError):
        provider.generate_json("s", "p", Demo)
    assert client.models.calls == 3


def test_empty_gemini_answer_becomes_a_validation_retry():
    """An empty reply is treated like invalid JSON and goes through the same retry loop."""
    provider, client = make_provider(["", GOOD])
    result = generate_structured(provider, "s", "p", Demo)
    assert result.percent == 10 and client.models.calls == 2
