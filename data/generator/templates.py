"""Turn contract rules into English clause text (three wording variants each)."""

import random
from datetime import date
from decimal import Decimal

VARIANTS = (1, 2, 3)


def fmt_date(d: date) -> str:
    return f"{d.day} {d:%B %Y}"


def fmt_pct(value) -> str:
    return format(Decimal(str(value)).normalize(), "f")


def fmt_pkr(value) -> str:
    return f"PKR {Decimal(str(value)):,.0f}"


_LATE_FLAT = {
    1: "If delivery of the goods is later than {deadline}, a penalty of {percent}% shall apply to the final invoice.",
    2: "Should the Vendor fail to deliver the goods on or before {deadline}, the Buyer may deduct {percent}% of the invoice value as liquidated damages.",
    3: "Delivery after {deadline} shall attract a deduction of {percent}% from the total amount payable under this Agreement.",
}

_LATE_PER_DAY = {
    1: "For each day of delay beyond {deadline}, a penalty of {percent}% of the invoice value shall apply{cap}.",
    2: "The Vendor shall pay liquidated damages at {percent}% of the total order value for every day of delay after {deadline}{cap}.",
    3: "Late delivery after {deadline} will be penalised at {percent}% per day of delay{cap}.",
}

_VOLUME = {
    1: "If the Buyer orders {qty} or more units in a single order, a discount of {pct}% shall be applied to the invoice.",
    2: "Orders of at least {qty} units qualify for a volume discount of {pct}% on the total price.",
    3: "A volume discount of {pct}% is granted on any order of {qty} units or above.",
}

_PAYMENT = {
    1: "Payment of each invoice shall be made within {days} days of the invoice date.",
    2: "The Buyer shall settle invoices on Net {days} terms, counted from the invoice date.",
    3: "All invoices are payable {days} calendar days after the date of invoice.",
}

_PRICE = {
    1: "The agreed unit price for {item} is {price} per unit and shall not be exceeded.",
    2: "The Vendor shall supply {item} at a fixed rate of {price} per unit.",
    3: "Unit price of {item}: {price}. No price increase is permitted during the term of this Agreement.",
}


def _late_penalty(rule: dict, variant: int) -> str:
    deadline = fmt_date(date.fromisoformat(rule["deadline"]))
    percent = fmt_pct(rule["percent"])
    grace = int(rule.get("grace_days", 0))

    if rule["mode"] == "flat_percent":
        text = _LATE_FLAT[variant].format(deadline=deadline, percent=percent)
        if grace:
            text += f" No penalty applies if the delay is not more than {grace} days."
        return text

    cap = rule.get("cap_percent")
    cap_text = f", up to a maximum of {fmt_pct(cap)}%" if cap else ""
    text = _LATE_PER_DAY[variant].format(deadline=deadline, percent=percent, cap=cap_text)
    if grace:
        text += f" The first {grace} days of delay shall not be penalised."
    return text


def render_clause(rule: dict, variant: int) -> str:
    kind = rule["clause_type"]
    if kind == "late_penalty":
        return _late_penalty(rule, variant)
    if kind == "volume_discount":
        return _VOLUME[variant].format(
            qty=rule["min_quantity"], pct=fmt_pct(rule["discount_percent"])
        )
    if kind == "payment_terms":
        return _PAYMENT[variant].format(days=rule["net_days"])
    if kind == "unit_price":
        return _PRICE[variant].format(
            item=rule["item_name"], price=fmt_pkr(rule["agreed_unit_price"])
        )
    raise ValueError(f"Unknown clause type: {kind}")


_RULE_TITLES = {
    "late_penalty": "Delivery and Late Delivery",
    "volume_discount": "Volume Discount",
    "payment_terms": "Payment Terms",
    "unit_price": "Pricing",
}

# Filler clauses. "liability" and "late_payment_charge" are decoys:
# they contain numbers or penalty-like words but are NOT audit rules.
FILLERS = {
    "confidentiality": (
        "Confidentiality",
        "Each party shall keep the terms of this Agreement and all business information of the other party confidential.",
    ),
    "termination": (
        "Termination",
        "Either party may terminate this Agreement with thirty days written notice.",
    ),
    "warranty": (
        "Warranty",
        "The Vendor warrants that all goods are new, genuine and free from defects for twelve months from delivery.",
    ),
    "liability": (
        "Limitation of Liability",
        "The total liability of either party under this Agreement shall not exceed 10% of the total order value.",
    ),
    "late_payment_charge": (
        "Late Payment by Buyer",
        "If the Buyer delays payment beyond the due date, a late payment charge of 2% per month applies to the unpaid amount.",
    ),
}


def build_contract_sections(spec: dict) -> list[dict]:
    """Return the contract as an ordered list of {key, title, text}."""
    variant = spec["layout"]["wording_variant"]
    rng = random.Random(spec["seed"])

    body = []
    for rule in spec["rules"]:
        key = rule["clause_type"]
        body.append({"key": key, "title": _RULE_TITLES[key], "text": render_clause(rule, variant)})
    for name in spec["layout"].get("filler_clauses", []):
        title, text = FILLERS[name]
        body.append({"key": name, "title": title, "text": text})
    rng.shuffle(body)

    head = [
        {
            "key": "parties",
            "title": "Parties",
            "text": f"This Agreement is made between {spec['buyer']} (the Buyer) and {spec['vendor']} (the Vendor).",
        },
        {
            "key": "scope",
            "title": "Scope of Supply",
            "text": "The Vendor shall supply the goods listed in each Purchase Order issued by the Buyer.",
        },
    ]
    return head + body
