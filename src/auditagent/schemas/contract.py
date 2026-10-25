from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Where in the contract a rule was found (evidence)."""

    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class LatePenaltyRule(BaseModel):
    clause_type: Literal["late_penalty"] = "late_penalty"
    deadline: date
    mode: Literal["flat_percent", "per_day_percent"]
    percent: Decimal = Field(gt=0, le=100)
    cap_percent: Decimal | None = Field(default=None, gt=0, le=100)
    grace_days: int = Field(default=0, ge=0)
    source: Source
    deadline_source: Source | None = Field(
        default=None,
        description="Where the deadline date is written, only when it is in a different clause than `source`",
    )


class VolumeDiscountRule(BaseModel):
    clause_type: Literal["volume_discount"] = "volume_discount"
    min_quantity: int = Field(ge=1)
    discount_percent: Decimal = Field(gt=0, le=100)
    source: Source


class PaymentTermsRule(BaseModel):
    clause_type: Literal["payment_terms"] = "payment_terms"
    net_days: int = Field(ge=0)
    source: Source


class UnitPriceRule(BaseModel):
    clause_type: Literal["unit_price"] = "unit_price"
    item_name: str = Field(min_length=1)
    agreed_unit_price: Decimal = Field(gt=0)
    source: Source


ContractRule = Annotated[
    LatePenaltyRule | VolumeDiscountRule | PaymentTermsRule | UnitPriceRule,
    Field(discriminator="clause_type"),
]


class ExtractedContract(BaseModel):
    """The full output of Agent 1 for one contract."""

    rules: list[ContractRule]