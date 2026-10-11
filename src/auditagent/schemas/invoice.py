from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    item_name: str = Field(min_length=1)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(gt=0)
    line_total: Decimal = Field(ge=0)


class Adjustment(BaseModel):
    """A deduction or charge printed on the invoice, e.g. 'Less: volume discount'."""

    label: str = Field(min_length=1)
    amount: Decimal  # negative = credit to the buyer


class InvoiceData(BaseModel):
    """Output of Agent 2 for one invoice."""

    invoice_number: str = Field(min_length=1)
    invoice_date: date
    delivery_date: date | None = None
    due_date: date | None = None
    line_items: list[LineItem] = Field(min_length=1)
    adjustments: list[Adjustment] = Field(default_factory=list)
    total_amount: Decimal = Field(gt=0)
    currency: Literal["PKR"] = "PKR"
    


class PurchaseOrderData(BaseModel):
    """Output of Agent 2 for one purchase order."""

    po_number: str = Field(min_length=1)
    po_date: date
    delivery_due_date: date | None = None
    line_items: list[LineItem] = Field(min_length=1)
    total_amount: Decimal = Field(gt=0)
    currency: Literal["PKR"] = "PKR"