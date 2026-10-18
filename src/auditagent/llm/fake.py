"""A scripted provider for tests: returns prepared replies and records every prompt."""

from pydantic import BaseModel


class ScriptedProvider:
    name = "scripted"
    model = "scripted-1"

    def __init__(self, replies: list[str]):
        self._replies = list(replies)
        self.prompts: list[str] = []

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        self.prompts.append(prompt)
        if not self._replies:
            raise AssertionError("ScriptedProvider ran out of replies")
        return self._replies.pop(0)