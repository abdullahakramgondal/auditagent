"""A Gemini call that does not answer in time is retried like a 503 (TODO item 81)."""

import httpx
import pytest
from pydantic import BaseModel

from auditagent.llm.base import LLMTransientError
from auditagent.llm.gemini import GeminiProvider

GOOD = '{"percent": 10}'


class Demo(BaseModel):
    percent: int


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
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
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


def make_provider(outcomes, max_retries=3):
    client = FakeClient(outcomes)
    provider = GeminiProvider(
        "unused", "gemini-test", client=client, retry_wait=0, max_retries=max_retries
    )
    return provider, client


def test_a_call_that_times_out_is_tried_again_and_then_succeeds():
    provider, client = make_provider([httpx.ReadTimeout("slow"), GOOD])
    assert provider.generate_json("s", "p", Demo) == GOOD
    assert client.models.calls == 2 and provider.retries == 1


def test_a_call_that_always_times_out_gives_a_transient_error_after_the_last_try():
    provider, client = make_provider([httpx.ReadTimeout("slow")] * 3, max_retries=3)
    with pytest.raises(LLMTransientError, match="did not answer"):
        provider.generate_json("s", "p", Demo)
    assert client.models.calls == 3
