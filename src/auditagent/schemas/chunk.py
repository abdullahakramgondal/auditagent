from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A clause-sized piece of a contract that remembers where it came from."""

    chunk_id: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    heading: str = ""
    text: str = Field(min_length=1)


class SearchHit(BaseModel):
    chunk: Chunk
    distance: float  # smaller is closer
