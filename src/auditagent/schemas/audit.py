from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from auditagent.schemas.contract import Source

ClauseType = Literal["late_penalty", "volume_discount", "payment_terms", "unit_price"]
AuditStatus = Literal["COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"]


class Finding(BaseModel):
    """One detected breach, with the evidence from the contract."""

    clause_type: ClauseType
    description: str = Field(min_length=1)
    source: Source
    expected_amount: Decimal | None = Field(default=None, ge=0)
    billed_amount: Decimal | None = Field(default=None, ge=0)
    difference: Decimal = Field(default=Decimal(0), ge=0)  # PKR overbilled


class AuditResult(BaseModel):
    """Final report for one contract + PO + invoice set."""

    status: AuditStatus
    billed_total: Decimal = Field(ge=0)
    correct_payable: Decimal = Field(ge=0)
    total_difference: Decimal = Field(ge=0)
    findings: list[Finding] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def status_must_match_details(self):
        if self.status == "COMPLIANT" and (self.findings or self.review_reasons):
            raise ValueError("COMPLIANT result cannot have findings or review reasons")
        if self.status == "NON_COMPLIANT" and not self.findings:
            raise ValueError("NON_COMPLIANT result needs at least one finding")
        if self.status == "NEEDS_REVIEW" and not self.review_reasons:
            raise ValueError("NEEDS_REVIEW result needs at least one review reason")
        return self
