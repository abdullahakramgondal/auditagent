from auditagent.agents.legal_extractor import hint_fires


def test_a_price_adjustment_for_a_large_order_is_a_volume_discount_hint():
    """Regression (tb_16): 'a price adjustment equal to 6.5%' was no hint, so an empty answer stayed silent."""
    text = (
        "7.2 Volume-based price adjustment. If a single accepted purchase order covers 35 or more "
        "units of Equipment, the Buyer shall receive a price adjustment equal to 6.5% of the "
        "otherwise applicable amount."
    )
    assert hint_fires("volume_discount", text)


def test_a_service_credit_is_not_a_volume_discount_hint():
    """tb_11: a support service credit looks like a discount but is not a volume rule."""
    text = (
        "For each full day of delay in responding, the Buyer is entitled to a service credit "
        "equal to 3% of the monthly support fee."
    )
    assert not hint_fires("volume_discount", text)


def test_a_price_adjustment_without_a_percentage_is_not_a_hint():
    text = "Any price adjustment must be agreed in writing by both Parties."
    assert not hint_fires("volume_discount", text)
