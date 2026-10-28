import json

from auditagent.agents.commercial_extractor import CommercialExtractor
from auditagent.ingestion.pdf_parser import parse_pdf
from auditagent.llm.fake import ScriptedProvider
from auditagent.schemas.invoice import InvoiceData, PurchaseOrderData
from data.generator.commercial_pdf import write_invoice_pdf, write_po_pdf
from data.generator.spec_generator import generate_all


def line_forms(items):
    """The rows of a spec as a perfect model would answer them."""
    return [
        {
            "item_name": item["item_name"],
            "quantity": item["quantity"],
            "unit_price": float(item["unit_price"]),
            "line_total": float(item["line_total"]),
        }
        for item in items
    ]


def ideal_invoice(invoice):
    """What a perfect model would answer for the invoice of a spec."""
    return {
        "invoice_number": invoice["invoice_number"],
        "invoice_date": invoice["invoice_date"],
        "delivery_date": invoice.get("delivery_date"),
        "due_date": invoice.get("due_date"),
        "line_items": line_forms(invoice["line_items"]),
        "adjustments": [
            {"label": a["label"], "amount": float(a["amount"])}
            for a in invoice.get("adjustments", [])
        ],
        "total_amount": float(invoice["total_amount"]),
    }


def ideal_order(order):
    """What a perfect model would answer for the purchase order of a spec."""
    return {
        "po_number": order["po_number"],
        "po_date": order["po_date"],
        "delivery_due_date": order.get("delivery_due_date"),
        "line_items": line_forms(order["line_items"]),
        "total_amount": float(order["total_amount"]),
    }


def test_a_perfect_model_is_reproduced_on_every_generated_invoice_and_order(tmp_path):
    """Plumbing check (parse, text lines, grounding, schema, arithmetic) on all three layouts."""
    for spec in generate_all():
        case = spec["case_id"]
        invoice_doc = parse_pdf(write_invoice_pdf(spec, tmp_path / f"{case}_invoice.pdf"))
        order_doc = parse_pdf(write_po_pdf(spec, tmp_path / f"{case}_po.pdf"))

        invoice_provider = ScriptedProvider([json.dumps(ideal_invoice(spec["invoice"]))])
        invoice = CommercialExtractor(invoice_provider).extract_invoice(invoice_doc)
        assert invoice.issues == [], (case, [i.reason for i in invoice.issues])
        assert invoice.invoice == InvoiceData.model_validate(spec["invoice"]), case

        order_provider = ScriptedProvider([json.dumps(ideal_order(spec["purchase_order"]))])
        order = CommercialExtractor(order_provider).extract_purchase_order(order_doc)
        assert order.issues == [], (case, [i.reason for i in order.issues])
        assert order.purchase_order == PurchaseOrderData.model_validate(spec["purchase_order"]), (
            case
        )
