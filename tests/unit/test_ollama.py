import json

import httpx
import pytest
from pydantic import BaseModel, Field

from auditagent.llm.base import LLMError, generate_structured
from auditagent.llm.ollama import OllamaProvider


class Demo(BaseModel):
    percent: int = Field(ge=1, le=100)
    deadline: str


GOOD = '{"percent": 10, "deadline": "2026-10-15"}'


def make_provider(handler, **kwargs):
    """An OllamaProvider wired to a fake server, so tests never touch the network."""
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OllamaProvider("tiny:1b", base_url="http://ollama.test", client=client, **kwargs)


def answer(content):
    return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})


def test_request_carries_the_model_the_schema_the_options_and_both_messages():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return answer(GOOD)

    provider = make_provider(handler, num_ctx=4096)
    assert provider.generate_json("sys", "prompt", Demo) == GOOD
    body = seen["body"]
    assert seen["url"] == "http://ollama.test/api/chat"
    assert body["model"] == "tiny:1b" and body["stream"] is False
    assert body["format"] == Demo.model_json_schema()
    assert body["options"] == {"temperature": 0, "num_ctx": 4096}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["messages"][0]["content"] == "sys" and body["messages"][1]["content"] == "prompt"


def test_a_trailing_slash_in_the_base_url_is_harmless():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return answer(GOOD)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    OllamaProvider("tiny:1b", base_url="http://ollama.test/", client=client).generate_json("s", "p", Demo)
    assert seen["url"] == "http://ollama.test/api/chat"


def test_the_structured_loop_sends_bad_json_back_and_accepts_the_fixed_answer():
    replies = ["not json at all", GOOD]
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["messages"][1]["content"])
        return answer(replies.pop(0))

    result = generate_structured(make_provider(handler), "s", "p", Demo)
    assert result.percent == 10
    assert len(calls) == 2 and "rejected" in calls[1]


def test_a_server_that_is_not_running_gives_a_clear_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError, match="ollama serve"):
        make_provider(handler).generate_json("s", "p", Demo)


def test_a_model_that_was_not_downloaded_says_how_to_get_it():
    def handler(request):
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(LLMError, match="ollama pull tiny:1b"):
        make_provider(handler).generate_json("s", "p", Demo)


def test_a_slow_model_that_times_out_says_which_setting_to_raise():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(LLMError, match="OLLAMA_TIMEOUT"):
        make_provider(handler).generate_json("s", "p", Demo)


def test_other_server_errors_show_their_status_code():
    def handler(request):
        return httpx.Response(500, text="boom")

    with pytest.raises(LLMError, match="500"):
        make_provider(handler).generate_json("s", "p", Demo)


def test_an_empty_answer_is_returned_as_empty_text_so_the_retry_loop_handles_it():
    def handler(request):
        return answer("")

    assert make_provider(handler).generate_json("s", "p", Demo) == ""


def test_downloaded_models_are_listed_by_name():
    def handler(request):
        assert request.method == "GET" and str(request.url) == "http://ollama.test/api/tags"
        return httpx.Response(200, json={"models": [{"name": "b:1b"}, {"name": "a:3b"}]})

    assert make_provider(handler).list_models() == ["a:3b", "b:1b"]