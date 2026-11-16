// Golden example B: delivered on time, nothing to report.
export const compliant: Record<string, unknown> = {
  audit_id: 'b81e4d0c7a2f49d3a6c15e9f0b7d2a64',
  created_at: '2026-11-14T10:05:30.118204Z',
  status: 'COMPLIANT',
  billed_total: '10000000.00',
  correct_payable: '10000000.00',
  total_difference: '0.00',
  amounts_provisional: false,
  plain: {
    headline: 'This invoice is correct',
    advice: 'It matches the contract. You can go ahead and pay it.',
    problems: [],
  },
  findings: [],
  review_reasons: [],
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
  invoice: {
    invoice_number: 'INV-001',
    invoice_date: '2026-10-15',
    delivery_date: '2026-10-14',
    due_date: null,
    line_items: [
      { item_name: 'Server', quantity: 10, unit_price: '1000000', line_total: '10000000' },
    ],
    adjustments: [],
    total_amount: '10000000',
    currency: 'PKR',
  },
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
  llm_model: 'gemini-3.1-flash-lite',
  seconds: 48.9,
}
