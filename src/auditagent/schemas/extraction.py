from pydantic import BaseModel, Field

from auditagent.schemas.contract import ExtractedContract


class ExtractionIssue(BaseModel):
    """A rule the model proposed but we refused, or a problem we want a human to see."""

    clause_type: str
    reason: str = Field(min_length=1)
    quote: str = ""


class AgentOneResult(BaseModel):
    """Everything Agent 1 returns for one contract."""

    contract: ExtractedContract
    issues: list[ExtractionIssue] = Field(default_factory=list)
    llm_model: str