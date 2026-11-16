"""The PDF report of a finished audit, written for a person who is not a technician.

The words are plain: what is wrong, how much too much, where the contract says so. Technical
details (report number, model) sit in small print at the end. Built from the same AuditOut that
the screen shows, so the report and the screen never disagree. Every dynamic text is escaped.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from auditagent.api.schemas import AuditOut
from auditagent.rules.engine import same_item
from auditagent.schemas.audit import Finding
from auditagent.schemas.contract import (
    LatePenaltyRule,
    PaymentTermsRule,
    UnitPriceRule,
    VolumeDiscountRule,
)

TITLES = {
    "unit_price": "The price per item is higher than agreed",
    "late_penalty": "The delivery was late, but no penalty was taken off",
    "volume_discount": "A discount for a big order was not given",
    "payment_terms": "The payment deadline is shorter than agreed",
}
SOURCE_LABELS = {
    "contract": "About the contract",
    "invoice": "About the invoice",
    "purchase_order": "About the purchase order",
    "audit": "General",
}
BACKGROUNDS = {"COMPLIANT": "#f0fdf4", "NON_COMPLIANT": "#fef2f2", "NEEDS_REVIEW": "#fffbeb"}
ACCENTS = {"COMPLIANT": "#16a34a", "NON_COMPLIANT": "#dc2626", "NEEDS_REVIEW": "#d97706"}
CONTENT_WIDTH = 170 * mm
NOT_KNOWN = "—"
GREY = colors.HexColor("#cbd5e1")
MUTED = colors.HexColor("#475569")


def pkr(value: Decimal | None) -> str:
    """4462500.00 -> PKR 4,462,500; 1234.5 -> PKR 1,234.50; None -> a dash (not known, never zero)."""
    if value is None:
        return NOT_KNOWN
    sign = "-" if value < 0 else ""
    amount = abs(value)
    text = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"{sign}PKR {text}"


def pct(value: Decimal) -> str:
    """A percentage without a trailing zero: 15.0 -> 15, 2.50 -> 2.5."""
    return format(value.normalize(), "f")


def day(value: date | None) -> str:
    """A date as 9 March 2027."""
    return NOT_KNOWN if value is None else f"{value.day} {value:%B %Y}"


def days(count: int) -> str:
    """1 -> 1 day; 9 -> 9 days."""
    return f"{count} day" if count == 1 else f"{count} days"


def when(value: datetime) -> str:
    """A timestamp as 15 Nov 2026, 16:28 in Pakistan time."""
    try:
        local = value.astimezone(ZoneInfo("Asia/Karachi"))
    except ZoneInfoNotFoundError:  # no time zone data on this machine: show the time as it is
        local = value
    return f"{local.day} {local:%b %Y}, {local:%H:%M}"


def verdict(out: AuditOut) -> tuple[str, str]:
    """The headline and one line of advice, in plain words."""
    if out.status == "COMPLIANT":
        return "This invoice is correct", "It matches the contract. You can go ahead and pay it."
    if out.status == "NEEDS_REVIEW":
        return (
            "We could not fully check this invoice",
            "Please ask a person to look at it before you pay.",
        )
    if out.total_difference is not None and out.total_difference != 0:
        return (
            "This invoice is too high",
            "Do not pay it as it is. Ask the vendor for a corrected invoice.",
        )
    return (
        "This invoice breaks a rule of the contract",
        "Ask the vendor to correct it before you pay.",
    )


# ---- plain words for each kind of problem ----


def _rule_for(out: AuditOut, finding: Finding):
    """The contract rule behind a finding: the one with the same clause text, else the first of its kind."""
    same_kind = [rule for rule in out.contract.rules if rule.clause_type == finding.clause_type]
    exact = next((rule for rule in same_kind if rule.source.text == finding.source.text), None)
    return exact or (same_kind[0] if same_kind else None)


def _penalty_terms(rule: LatePenaltyRule) -> str:
    """The penalty of the contract in plain words."""
    if rule.mode == "flat_percent":
        return f"{pct(rule.percent)}% of the invoice, once"
    text = f"{pct(rule.percent)}% of the invoice for each day of delay"
    if rule.grace_days:
        text += f" (the first {days(rule.grace_days)} are free)"
    if rule.cap_percent:
        text += f", up to a maximum of {pct(rule.cap_percent)}%"
    return text


def _explain_price(out: AuditOut, rule) -> list[str] | None:
    if not isinstance(rule, UnitPriceRule) or out.invoice is None:
        return None
    row = next((i for i in out.invoice.line_items if same_item(rule.item_name, i.item_name)), None)
    if row is None:
        return None
    return [
        (
            f"The contract says each {rule.item_name} costs {pkr(rule.agreed_unit_price)}. "
            f"The invoice charges {pkr(row.unit_price)} each for {row.quantity} items."
        )
    ]


def _explain_late(out: AuditOut, rule) -> list[str] | None:
    if not isinstance(rule, LatePenaltyRule) or out.invoice is None:
        return None
    delivered = out.invoice.delivery_date
    if delivered is None:
        return None
    late = (delivered - rule.deadline).days
    return [
        (
            f"The contract says the goods must arrive by {day(rule.deadline)}. "
            f"They arrived on {day(delivered)}, which is {days(late)} late."
        ),
        f"The contract's penalty for this is {_penalty_terms(rule)}.",
        "The invoice does not take the full penalty off, so the vendor is asking for too much.",
    ]


def _explain_volume(out: AuditOut, rule) -> list[str] | None:
    if not isinstance(rule, VolumeDiscountRule) or out.invoice is None:
        return None
    items = sum(row.quantity for row in out.invoice.line_items)
    return [
        (
            f"The contract gives a {pct(rule.discount_percent)}% discount on orders of "
            f"{rule.min_quantity} or more items. This order has {items} items, so the discount applies."
        ),
        "The invoice does not include the full discount.",
    ]


def _explain_payment(out: AuditOut, rule) -> list[str] | None:
    invoice = out.invoice
    if not isinstance(rule, PaymentTermsRule) or invoice is None or invoice.due_date is None:
        return None
    given = (invoice.due_date - invoice.invoice_date).days
    earliest = invoice.invoice_date + timedelta(days=rule.net_days)
    return [
        (
            f"The contract gives the buyer {days(rule.net_days)} to pay after the invoice date. "
            f"This invoice is dated {day(invoice.invoice_date)} and asks for payment by "
            f"{day(invoice.due_date)}, which is only {days(given)}."
        ),
        f"The buyer should have until {day(earliest)}.",
    ]


EXPLAINERS = {
    "unit_price": _explain_price,
    "late_penalty": _explain_late,
    "volume_discount": _explain_volume,
    "payment_terms": _explain_payment,
}


def explain(out: AuditOut, finding: Finding) -> list[str]:
    """What went wrong, in sentences. If a detail is missing, the plain sentence of the engine is used."""
    paragraphs = EXPLAINERS[finding.clause_type](out, _rule_for(out, finding))
    return paragraphs or [finding.description]


def _rule_line(rule) -> str:
    """One contract rule that the system used, in plain words."""
    if isinstance(rule, LatePenaltyRule):
        return f"Late delivery after {day(rule.deadline)}: a penalty of {_penalty_terms(rule)}."
    if isinstance(rule, VolumeDiscountRule):
        return f"Orders of {rule.min_quantity} or more items: a {pct(rule.discount_percent)}% discount."
    if isinstance(rule, PaymentTermsRule):
        return f"Payment: {days(rule.net_days)} after the invoice date."
    return f"{rule.item_name}: agreed price {pkr(rule.agreed_unit_price)} per item."


# ---- the pages ----


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["BodyText"], fontSize=10.5, leading=15, spaceAfter=4)
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=22, alignment=0),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=14, spaceBefore=16, spaceAfter=6
        ),
        "h3": ParagraphStyle("h3", parent=body, fontName="Helvetica-Bold", spaceBefore=6),
        "body": body,
        "small": ParagraphStyle("small", parent=body, fontSize=8.5, leading=12, textColor=MUTED),
        "label": ParagraphStyle("label", parent=body, fontSize=9, leading=12, textColor=MUTED),
        "quote": ParagraphStyle("quote", parent=body, fontName="Helvetica-Oblique", fontSize=10),
        "money": ParagraphStyle(
            "money", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=20
        ),
        "headline": ParagraphStyle(
            "headline", parent=body, fontName="Helvetica-Bold", fontSize=20, leading=24
        ),
        "advice": ParagraphStyle("advice", parent=body, fontSize=12, leading=16),
        "item": ParagraphStyle("item", parent=body, fontName="Helvetica-Bold", fontSize=11.5),
        "amount": ParagraphStyle("amount", parent=body, fontName="Helvetica-Bold", alignment=2),
    }


def _verdict_box(out: AuditOut, styles: dict) -> Table:
    headline, advice = verdict(out)
    accent = ACCENTS[out.status]
    cell = [
        Paragraph(f'<font color="{accent}">{escape(headline)}</font>', styles["headline"]),
        Spacer(1, 4),
        Paragraph(escape(advice), styles["advice"]),
    ]
    box = Table([[cell]], colWidths=[CONTENT_WIDTH])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BACKGROUNDS[out.status])),
                ("LINEBEFORE", (0, 0), (0, -1), 5, colors.HexColor(accent)),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return box


def _money_table(out: AuditOut, styles: dict) -> Table:
    cells = [
        ("The vendor is asking for", out.billed_total),
        ("The right amount is", out.correct_payable),
        ("Too much", out.total_difference),
    ]
    width = CONTENT_WIDTH / 3
    table = Table(
        [
            [Paragraph(escape(label), styles["label"]) for label, _ in cells],
            [Paragraph(escape(pkr(value)), styles["money"]) for _, value in cells],
        ],
        colWidths=[width] * 3,
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, GREY),
                ("BOX", (2, 0), (2, 1), 1.2, colors.HexColor("#0f172a")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _finding(number: int, finding: Finding, out: AuditOut, styles: dict) -> KeepTogether:
    if finding.difference != 0:
        amount = f'<font color="#b91c1c">{escape(pkr(finding.difference))} too much</font>'
    else:
        amount = "A rule was broken"
    head = Table(
        [
            [
                Paragraph(f"{number}. {escape(TITLES[finding.clause_type])}", styles["item"]),
                Paragraph(amount, styles["amount"]),
            ]
        ],
        colWidths=[CONTENT_WIDTH * 0.64, CONTENT_WIDTH * 0.36],
    )
    head.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    quote = Table(
        [
            [
                [
                    Paragraph(
                        f"What the contract says (page {finding.source.page})", styles["label"]
                    ),
                    Paragraph(escape(finding.source.text), styles["quote"]),
                ]
            ]
        ],
        colWidths=[CONTENT_WIDTH],
    )
    quote.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story: list = [head, Spacer(1, 6)]
    story += [Paragraph(escape(text), styles["body"]) for text in explain(out, finding)]
    story += [Spacer(1, 2), quote, Spacer(1, 14)]
    return KeepTogether(story)


def _problems(out: AuditOut, styles: dict) -> list:
    story: list = [Paragraph("What is wrong", styles["h2"])]
    if out.findings:
        for number, finding in enumerate(out.findings, start=1):
            story.append(_finding(number, finding, out, styles))
    elif out.status == "COMPLIANT":
        story.append(
            Paragraph(
                "Nothing is wrong. The invoice follows every rule that we found in the contract.",
                styles["body"],
            )
        )
    else:
        story.append(
            Paragraph(
                "No mistake was proven, but some things could not be checked (see the list "
                "of things we could not check).",
                styles["body"],
            )
        )
    return story


def _reasons(out: AuditOut, styles: dict) -> list:
    story: list = [
        Paragraph("Things we could not check", styles["h2"]),
        Paragraph(
            "The system did not guess. These points need a person to look at them.",
            styles["body"],
        ),
    ]
    for source, label in SOURCE_LABELS.items():
        rows = [reason for reason in out.review_reasons if reason.source == source]
        if not rows:
            continue
        story.append(Paragraph(label, styles["h3"]))
        for reason in rows:
            field = reason.field.replace("_", " ").capitalize() + ": " if reason.field else ""
            story.append(Paragraph(escape(field + reason.reason), styles["body"], bulletText="•"))
    return story


def _rules(out: AuditOut, styles: dict) -> list:
    story: list = [Paragraph("The contract rules we checked", styles["h2"])]
    if not out.contract.rules:
        story.append(Paragraph("No rule could be proven in the contract.", styles["body"]))
    for rule in out.contract.rules:
        story.append(Paragraph(escape(_rule_line(rule)), styles["body"], bulletText="•"))
    return story


def _documents(out: AuditOut, styles: dict) -> list:
    story: list = [Paragraph("The documents we read", styles["h2"])]
    if out.invoice:
        inv = out.invoice
        text = f"Invoice {inv.invoice_number}, dated {day(inv.invoice_date)}"
        if inv.delivery_date:
            text += f", delivered on {day(inv.delivery_date)}"
        if inv.due_date:
            text += f", payment due {day(inv.due_date)}"
        story.append(Paragraph(escape(f"{text}. Total {pkr(inv.total_amount)}."), styles["body"]))
    else:
        story.append(Paragraph("Invoice: could not be read with certainty.", styles["body"]))
    if out.purchase_order:
        po = out.purchase_order
        text = f"Purchase order {po.po_number}, dated {day(po.po_date)}"
        if po.delivery_due_date:
            text += f", delivery wanted by {day(po.delivery_due_date)}"
        story.append(Paragraph(escape(f"{text}. Total {pkr(po.total_amount)}."), styles["body"]))
    else:
        story.append(Paragraph("Purchase order: could not be read with certainty.", styles["body"]))
    return story


def _small_print(out: AuditOut, styles: dict) -> list:
    return [
        Spacer(1, 14),
        Paragraph(
            "This report was made automatically by AuditAgent AI. It checks an invoice against "
            "four kinds of contract rules: late delivery, volume discount, payment terms and the "
            "agreed price. A person should confirm important decisions before money is paid.",
            styles["small"],
        ),
        Paragraph(
            f"Report number {escape(out.audit_id)} · checked by {escape(out.llm_model)}",
            styles["small"],
        ),
    ]


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(20 * mm, 10 * mm, "Synthetic or test documents only. Made by AuditAgent AI.")
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report_pdf(out: AuditOut) -> bytes:
    """The report of one finished audit as PDF bytes."""
    styles = _styles()
    subtitle = f"Checked on {when(out.created_at)}"
    if out.invoice:
        subtitle += f" · Invoice {out.invoice.invoice_number}"
    story: list = [
        Paragraph("Invoice check report", styles["title"]),
        Paragraph(escape(subtitle), styles["small"]),
        Spacer(1, 12),
        _verdict_box(out, styles),
    ]
    if out.billed_total is not None:
        story += [Spacer(1, 14), _money_table(out, styles)]
        if out.amounts_provisional:
            story += [
                Spacer(1, 4),
                Paragraph(
                    "These amounts may be incomplete, because something could not be checked.",
                    styles["small"],
                ),
            ]
    if out.status == "NEEDS_REVIEW":
        story += _reasons(out, styles)
    story += _problems(out, styles)
    if out.status != "NEEDS_REVIEW" and out.review_reasons:
        story += _reasons(out, styles)
    story += _rules(out, styles)
    story += _documents(out, styles)
    story += _small_print(out, styles)

    buffer = BytesIO()
    SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Invoice check report {out.audit_id}",
        author="AuditAgent AI",
    ).build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
