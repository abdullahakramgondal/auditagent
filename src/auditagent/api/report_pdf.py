"""The PDF report of a finished audit, written for a person who is not a technician.

Every sentence comes from api/plain.py, the same place that feeds the screen, so the two never
disagree: the status label, the problems, the working-out, the checklist and the open points.
Technical details (report number, model, raw messages) sit in small print.
Every dynamic text is escaped. The standard PDF fonts have no minus sign, so it is written as "-".
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

STATUS_LABELS = {
    "COMPLIANT": "COMPLIANT",
    "NON_COMPLIANT": "NON-COMPLIANT",
    "NEEDS_REVIEW": "NEEDS HUMAN REVIEW",
}
BACKGROUNDS = {"COMPLIANT": "#f0fdf4", "NON_COMPLIANT": "#fef2f2", "NEEDS_REVIEW": "#fffbeb"}
ACCENTS = {"COMPLIANT": "#16a34a", "NON_COMPLIANT": "#dc2626", "NEEDS_REVIEW": "#d97706"}
AMOUNT_COLOURS = {
    "start": "#0f172a",
    "base": "#0f172a",
    "minus": "#b91c1c",
    "result": "#166534",
    "difference": "#b91c1c",
}
CHECK_LOOK = {
    "ok": ("Checked, no problem", "#15803d"),
    "problem": ("Problem found", "#b91c1c"),
    "unchecked": ("Could not check", "#b45309"),
    "none": ("No rule found", "#475569"),
}
CONTENT_WIDTH = 170 * mm
GREY = colors.HexColor("#cbd5e1")
MUTED = colors.HexColor("#475569")


def _t(text: str) -> str:
    """Text for a paragraph: escaped, and with a plain minus sign (the PDF font has no U+2212)."""
    return escape(text.replace("\u2212", "-"))


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
        "bullet": ParagraphStyle(
            "bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3
        ),
        "small": ParagraphStyle("small", parent=body, fontSize=8.5, leading=12, textColor=MUTED),
        "label": ParagraphStyle("label", parent=body, fontSize=9, leading=12, textColor=MUTED),
        "quote": ParagraphStyle("quote", parent=body, fontName="Helvetica-Oblique", fontSize=10),
        "money": ParagraphStyle(
            "money", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=20
        ),
        "status": ParagraphStyle(
            "status", parent=body, fontName="Helvetica-Bold", fontSize=9, leading=12, spaceAfter=2
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
            f'<font color="{accent}">{_t(STATUS_LABELS[out.status])}</font>', styles["status"]
        ),
        Paragraph(f'<font color="{accent}">{_t(out.plain.headline)}</font>', styles["headline"]),
        Spacer(1, 4),
        Paragraph(_t(out.plain.advice), styles["advice"]),
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
    ]
    if out.status == "NON_COMPLIANT":  # only a result with a mistake shows the overcharge
        cells.append(("Overcharged by", out.total_difference))
    width = CONTENT_WIDTH / len(cells)
    table = Table(
        [
            [Paragraph(_t(label), styles["label"]) for label, _ in cells],
            [Paragraph(_t(pkr(value)), styles["money"]) for _, value in cells],
        ],
        colWidths=[width] * len(cells),
    )
    commands = [
        ("BOX", (0, 0), (-1, -1), 0.5, GREY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GREY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    if len(cells) == 3:
        commands.append(("BOX", (2, 0), (2, 1), 1.2, colors.HexColor("#0f172a")))
    table.setStyle(TableStyle(commands))
    return table


def _problem(number: int, problem: PlainProblem, styles: dict) -> KeepTogether:
    head = Table(
        [
            [
                Paragraph(f"{number}. {_t(problem.title)}", styles["item"]),
                Paragraph(
                    f'<font color="#b91c1c">{_t(problem.amount_text)}</font>', styles["amount"]
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
                    Paragraph(_t(problem.quote), styles["quote"]),
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
    story += [Paragraph(_t(text), styles["body"]) for text in problem.paragraphs]
    story += [Spacer(1, 2), quote, Spacer(1, 14)]
    return KeepTogether(story)


def _problems(out: AuditOut, styles: dict) -> list:
    """The mistakes. With no mistake nothing is shown: 'What we checked' says the rest."""
    if not out.plain.problems:
        return []
    story: list = [Paragraph("What is wrong", styles["h2"])]
    for number, problem in enumerate(out.plain.problems, start=1):
        story.append(_problem(number, problem, styles))
    return story


def _calculation(out: AuditOut, styles: dict) -> list:
    steps = out.plain.calculation
    if not steps:
        return []
    head_right = ParagraphStyle("head_right", parent=styles["label"], alignment=2)
    rows = [
        [
            Paragraph("<b>Step</b>", styles["label"]),
            Paragraph("<b>How we got it</b>", styles["label"]),
            Paragraph("<b>Amount</b>", head_right),
        ]
    ]
    for step in steps:
        colour = AMOUNT_COLOURS[step.kind]
        rows.append(
            [
                Paragraph(f"<b>{_t(step.label)}</b>", styles["body"]),
                Paragraph(_t(step.detail), styles["small"]),
                Paragraph(
                    f'<font color="{colour}">{_t(step.amount_text)}</font>', styles["amount"]
                ),
            ]
        )
    table = Table(
        rows,
        colWidths=[CONTENT_WIDTH * 0.27, CONTENT_WIDTH * 0.46, CONTENT_WIDTH * 0.27],
        repeatRows=1,
    )
    commands = [
        ("BOX", (0, 0), (-1, -1), 0.5, GREY),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, GREY),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for index, step in enumerate(steps, start=1):  # row 0 is the header
        if step.kind == "result":
            commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#f8fafc")))
    table.setStyle(TableStyle(commands))
    return [
        Paragraph("How we worked it out", styles["h2"]),
        Paragraph("Step by step, with the numbers of your documents.", styles["body"]),
        table,
    ]


def _checks(out: AuditOut, styles: dict) -> list:
    items = out.plain.checks
    if not items:
        return []
    rows = []
    for item in items:
        text, colour = CHECK_LOOK[item.state]
        rows.append(
            [
                [
                    Paragraph(
                        f'<b>{_t(item.label)}</b> - <font color="{colour}">{text}</font>',
                        styles["body"],
                    ),
                    Paragraph(_t(item.detail), styles["small"]),
                ]
            ]
        )
    table = Table(rows, colWidths=[CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, GREY),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [
        Paragraph("What we checked", styles["h2"]),
        Paragraph(
            "We check four things: the price, the volume discount, the delivery date and the "
            "payment deadline. Tax and extra charges are not checked.",
            styles["body"],
        ),
        table,
    ]


def _reasons(out: AuditOut, styles: dict) -> list:
    notes = out.plain.review_notes
    if not notes:
        return []
    story: list = [
        Paragraph("What a person should check", styles["h2"]),
        Paragraph(
            "The system did not guess. Each point says what we could not confirm "
            "and what to do about it.",
            styles["body"],
        ),
    ]
    groups: dict[str, list] = {}
    for note in notes:
        groups.setdefault(note.group, []).append(note)
    for group, rows in groups.items():
        story.append(Paragraph(_t(group), styles["h3"]))
        for note in rows:
            story.append(
                KeepTogether(
                    [
                        Paragraph(f"<b>{_t(note.title)}</b>", styles["body"]),
                        Paragraph(_t(note.what), styles["body"]),
                        Paragraph(f"<b>What to do:</b> {_t(note.todo)}", styles["body"]),
                        Paragraph(f"Technical details: {_t(note.technical)}", styles["small"]),
                        Spacer(1, 8),
                    ]
                )
            )
    return story


def _rules(out: AuditOut, styles: dict) -> list:
    story: list = [Paragraph("The contract rules we checked", styles["h2"])]
    if not out.contract.rules:
        story.append(Paragraph("No rule could be proven in the contract.", styles["body"]))
    for rule in out.contract.rules:
        story.append(Paragraph(_t(rule_line(rule)), styles["bullet"], bulletText="•"))
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
        story.append(Paragraph(_t(f"{text}. Total {pkr(inv.total_amount)}."), styles["body"]))
    else:
        story.append(Paragraph("Invoice: could not be read with certainty.", styles["body"]))
    if out.purchase_order:
        po = out.purchase_order
        text = f"Purchase order {po.po_number}, dated {day(po.po_date)}"
        if po.delivery_due_date:
            text += f", delivery wanted by {day(po.delivery_due_date)}"
        story.append(Paragraph(_t(f"{text}. Total {pkr(po.total_amount)}."), styles["body"]))
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
            f"Report number {_t(out.audit_id)} · checked by {_t(out.llm_model)}",
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
    """The report of one finished audit as PDF bytes (the same order as the screen)."""
    styles = _styles()
    subtitle = f"Checked on {when(out.created_at)}"
    if out.invoice:
        subtitle += f" · Invoice {out.invoice.invoice_number}"
    story: list = [
        Paragraph("Invoice check report", styles["title"]),
        Paragraph(_t(subtitle), styles["small"]),
        Spacer(1, 12),
        _verdict_box(out, styles),
    ]
    if out.status == "NEEDS_REVIEW":
        story += _reasons(out, styles)
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
    story += _problems(out, styles)
    story += _calculation(out, styles)
    story += _checks(out, styles)
    if out.status != "NEEDS_REVIEW":
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
