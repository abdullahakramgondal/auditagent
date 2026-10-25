from pydantic import BaseModel, Field, model_validator


class PageText(BaseModel):
    """Text of one PDF page. `number` is 1-based and comes from the parser, never from an LLM."""

    number: int = Field(ge=1)
    text: str


class ParsedDocument(BaseModel):
    """Page-wise text of one PDF, with the evidence trail kept."""

    source_name: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    pages: list[PageText] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def page_numbers_must_be_consecutive(self):
        if [p.number for p in self.pages] != list(range(1, len(self.pages) + 1)):
            raise ValueError("pages must be numbered 1..N in order")
        return self

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def has_text(self) -> bool:
        return any(p.text.strip() for p in self.pages)

    def page_text(self, number: int) -> str:
        return self.pages[number - 1].text
