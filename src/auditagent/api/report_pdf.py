"""The PDF report of a finished audit, written for a person who is not a technician.

The words come from api/plain.py, the same place that feeds the screen, so the two never
disagree. Technical details (report number, model) sit in small print at the end.
Every dynamic text is escaped.
"""

from datetime import datetime
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

from auditagent.api.plain import PlainProblem, day, pkr, rule_line
from auditagent.api.schemas import AuditOut

SOURCE_LABELS = {
    "contract": "About the contract",
    "invoice": "About the invoice",
    "purchase_order": "About the purchase order",
    "audit": "General",
}
BACKGROUNDS = {"COMPLIANT": "#f0fdf4", "NON_COMPLIANT": "#fef2f2", "NEEDS_REVIEW": "#fffbeb"}
ACCENTS = {"COMPLIANT": "#16a34a", "NON_COMPLIANT": "#dc2626", "NEEDS_REVIEW": "#d97706"}
CONTENT_WIDTH = 170 * mm
GREY = colors.HexColor("#cbd5e1")
MUTED = colors.HexColor("#475569")


def when(value: datetime) -> str:
    """A timestamp as 15 Nov 2026, 16:28 in Pakistan time."""
    try:
        local = value.astimezone(ZoneInfo("Asia/Karachi"))
    except ZoneInfoNotFoundError:  # no time zone data on this machine: show the time as it is
        local = value
    return f"{local.day} {local:%b %Y}, {local:%H:%M}"


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
    accent = ACCENTS[out.status]
    cell = [
        Paragraph(
            f'<font color="{accent}">{escape(out.plain.headline)}</font>', styles["headline"]
        ),
        Spacer(1, 4),
        Paragraph(escape(out.plain.advice), styles["advice"]),
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


def _problem(number: int, problem: PlainProblem, styles: dict) -> KeepTogether:
    head = Table(
        [
            [
                Paragraph(f"{number}. {escape(problem.title)}", styles["item"]),
                Paragraph(
                    f'<font color="#b91c1c">{escape(problem.amount_text)}</font>', styles["amount"]
                ),
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
                    Paragraph(f"What the contract says (page {problem.page})", styles["label"]),
                    Paragraph(escape(problem.quote), styles["quote"]),
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
    story += [Paragraph(escape(text), styles["body"]) for text in problem.paragraphs]
    story += [Spacer(1, 2), quote, Spacer(1, 14)]
    return KeepTogether(story)


def _problems(out: AuditOut, styles: dict) -> list:
    story: list = [Paragraph("What is wrong", styles["h2"])]
    if out.plain.problems:
        for number, problem in enumerate(out.plain.problems, start=1):
            story.append(_problem(number, problem, styles))
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
        story.append(Paragraph(escape(rule_line(rule)), styles["body"], bulletText="•"))
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
