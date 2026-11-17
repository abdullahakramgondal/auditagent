// The invoice could not be proven (cb_07 style): no amounts, two review reasons.
export const needsReview: Record<string, unknown> = {
  audit_id: 'c5d2f7a19e3b4086b4a7d1e8c0f93b25',
  created_at: '2026-11-14T10:20:44.906112Z',
  status: 'NEEDS_REVIEW',
  billed_total: null,
  correct_payable: null,
  total_difference: null,
  amounts_provisional: false,
  plain: {
    headline: 'We could not fully check this invoice',
    advice: 'Please ask a person to look at it before you pay.',
    problems: [],
    calculation: [],
    checks: [
      {
        clause_type: 'unit_price',
        label: 'Price per item',
        state: 'none',
        detail: 'The contract has no rule about this.',
      },
      {
        clause_type: 'volume_discount',
        label: 'Volume discount',
        state: 'none',
        detail: 'The contract has no rule about this.',
      },
      {
        clause_type: 'late_penalty',
        label: 'Delivery on time',
        state: 'unchecked',
        detail: 'The invoice could not be read.',
      },
      {
        clause_type: 'payment_terms',
        label: 'Payment deadline',
        state: 'none',
        detail: 'The contract has no rule about this.',
      },
    ],
    review_notes: [
      {
        group: 'About the invoice',
        title: 'We could not read the delivery date',
        what: 'The invoice seems to show a delivery date, but the system could not read it with certainty.',
        todo: 'Open the invoice PDF and check it by hand.',
        technical:
          'delivery_date: delivery_date: the document shows a date next to a label for it but the model returned none: needs review',
      },
      {
        group: 'General',
        title: 'The invoice could not be read with certainty',
        what: 'Because of this, no amount was checked.',
        todo: 'Open the invoice PDF and check it by hand, or upload a clearer copy.',
        technical: 'The invoice could not be proven from its text, so no amount was checked.',
      },
    ],
  },
  findings: [],
  review_reasons: [
    {
      source: 'invoice',
      field: 'delivery_date',
      reason:
        'delivery_date: the document shows a date next to a label for it but the model returned none: needs review',
    },
    {
      source: 'audit',
      field: '',
      reason: 'The invoice could not be proven from its text, so no amount was checked.',
    },
  ],
  contract: {
    rules: [
      {
        clause_type: 'late_penalty',
        deadline: '2026-10-15',
        mode: 'flat_percent',
        percent: '10',
        cap_percent: null,
        grace_days: 0,
        source: {
          page: 4,
          text: 'If delivery of the goods is later than 15 October 2026, a penalty of 10% shall apply to the final invoice.',
        },
        deadline_source: null,
      },
    ],
  },
  invoice: null,
  purchase_order: {
    po_number: 'PO-2026-001',
    po_date: '2026-09-01',
    delivery_due_date: '2026-10-15',
    line_items: [
      { item_name: 'Server', quantity: 10, unit_price: '1000000', line_total: '10000000' },
    ],
    total_amount: '10000000',
    currency: 'PKR',
  },
  llm_model: 'qwen2.5:7b',
  seconds: 312.6,
}