"""The forms the LLM fills in for Agent 2: one for an invoice and one for a purchase order.

Flat and simple like the Agent 1 forms: every key must be present (the Gemini response schema does not
like defaults) and there are no exclusive bounds. Dates are asked as YYYY-MM-DD; code checks them
against the document text.
"""

from pydantic import BaseModel, Field


class LineItemForm(BaseModel):
    """One row of the items table."""

    item_name: str = Field(min_length=1, description="The item name exactly as printed on the row")
    quantity: int = Field(ge=1, description="Number of units on the row")
    unit_price: float = Field(ge=0.01, description="PKR per unit, digits only, no commas")
    line_total: float = Field(
        ge=0, description="The amount printed for the row in PKR, digits only"
    )


class AdjustmentForm(BaseModel):
    """A discount, credit or charge printed under the items."""

    label: str = Field(
        min_length=1, description="The label exactly as printed, e.g. 'Less: discount'"
    )
    amount: float = Field(description="PKR, digits only, negative when it reduces the total")


class InvoiceForm(BaseModel):
    """What the model reads from an invoice."""

    invoice_number: str = Field(min_length=1, description="The invoice number exactly as printed")
    invoice_date: str = Field(description="The date the invoice was issued, as YYYY-MM-DD")
    delivery_date: str | None = Field(
        description="The date of delivery as YYYY-MM-DD, or null if the invoice shows none"
    )
    due_date: str | None = Field(
        description="The payment due date as YYYY-MM-DD, or null if the invoice shows none"
    )
    line_items: list[LineItemForm]
    adjustments: list[AdjustmentForm]
    total_amount: float = Field(
        ge=0.01, description="The total payable printed on the invoice, in PKR"
    )


class PurchaseOrderForm(BaseModel):
    """What the model reads from a purchase order."""

    po_number: str = Field(min_length=1, description="The purchase order number exactly as printed")
    po_date: str = Field(description="The date the order was raised, as YYYY-MM-DD")
    delivery_due_date: str | None = Field(
        description="The date delivery is required by as YYYY-MM-DD, or null if the order shows none"
    )
    line_items: list[LineItemForm]
    total_amount: float = Field(ge=0.01, description="The total printed on the order, in PKR")
