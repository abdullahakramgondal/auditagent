"""The forms the LLM fills in for Agent 1.

These are deliberately flat and simple. They carry no page number (the parser knows the page)
and no defaults (the Gemini response schema does not like them): every key must be present.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LateRuleForm(BaseModel):
    quote: str = Field(description="The clause sentence(s), copied word for word from the contract text")
    chunk_id: str = Field(description="The chunk_id of the chunk the quote was copied from")
    deadline: str = Field(description="Delivery deadline as YYYY-MM-DD")
    mode: Literal["flat_percent", "per_day_percent"]
    percent: float = Field(ge=0.01, le=100, description="Penalty percentage without the % sign")
    cap_percent: float | None = Field(ge=0.01, le=100, description="Maximum total penalty percent, or null if none")
    grace_days: int = Field(ge=0, description="Days of delay that are not penalised, 0 if none")


class VolumeRuleForm(BaseModel):
    quote: str
    chunk_id: str
    min_quantity: int = Field(ge=1, description="Minimum number of units that earns the discount")
    discount_percent: float = Field(ge=0.01, le=100)


class PaymentRuleForm(BaseModel):
    quote: str
    chunk_id: str
    net_days: int = Field(ge=0, description="Days after the invoice date within which payment is due")


class PriceRuleForm(BaseModel):
    quote: str
    chunk_id: str
    item_name: str = Field(min_length=1)
    agreed_unit_price: float = Field(ge=1, description="PKR per unit, digits only, no commas")


class LateRulesForm(BaseModel):
    rules: list[LateRuleForm]


class VolumeRulesForm(BaseModel):
    rules: list[VolumeRuleForm]


class PaymentRulesForm(BaseModel):
    rules: list[PaymentRuleForm]


class PriceRulesForm(BaseModel):
    rules: list[PriceRuleForm]