// A real result: tb_09 with gemini-3.1-flash-lite (billed 4,462,500, correct 3,421,250, overbilled 1,041,250).
export const nonCompliant: Record<string, unknown> = {
  audit_id: '3f9c2a7e5b1d4c8a9e0f6b2d7a1c4e83',
  created_at: '2026-11-14T09:41:12.482913Z',
  status: 'NON_COMPLIANT',
  billed_total: '4462500.00',
  correct_payable: '3421250.00',
  total_difference: '1041250.00',
  amounts_provisional: false,
  findings: [
    {
      clause_type: 'unit_price',
      description:
        'Dell UltraSharp U2723QE Monitor is billed above the agreed unit price of PKR 85,000.00: PKR 212,500.00 overbilled.',
      source: {
        page: 6,
        text: 'The agreed unit price for each Dell UltraSharp U2723QE Monitor is PKR 85,000 per unit. The Vendor shall ensure that the unit amount shown on an Invoice does not exceed that agreed figure.',
      },
      expected_amount: '4250000.00',
      billed_amount: '4462500.00',
      difference: '212500.00',
    },
    {
      clause_type: 'late_penalty',
      description:
        'Delivered on 9 March 2027, 9 days after 28 February 2027: a penalty of 12.5% (PKR 531,250.00) applies and was not deducted.',
      source: {
        page: 4,
        text: 'If delivery is delayed beyond the Delivery Deadline, the first four (4) calendar days of delay shall not attract a late-delivery penalty. From the next day, a penalty of 2.5% of the value of the delayed Equipment shown on the relevant Invoice shall apply for each day of delay, subject to an aggregate ceiling of 15% of that Invoice value.',
      },
      expected_amount: '3718750.00',
      billed_amount: '4250000.00',
      difference: '531250.00',
    },
    {
      clause_type: 'volume_discount',
      description:
        'The invoice has 50 units, the contract gives 7% from 30 units: PKR 297,500.00 discount not applied.',
      source: {
        page: 6,
        text: 'A single Order containing 30 or more units qualifies for a volume discount of 7% on the Equipment value of that Order.',
      },
      expected_amount: '3952500.00',
      billed_amount: '4250000.00',
      difference: '297500.00',
    },
    {
      clause_type: 'payment_terms',
      description:
        'The invoice is due on 30 March 2027, earlier than 9 April 2027 (Net 28 days from the invoice date).',
      source: {
        page: 6,
        text: 'The Buyer shall pay each valid and undisputed Invoice within 28 days of the invoice date.',
      },
      expected_amount: null,
      billed_amount: null,
      difference: '0',
    },
  ],
  review_reasons: [],
  contract: {
    rules: [
      {
        clause_type: 'late_penalty',
        deadline: '2027-02-28',
        mode: 'per_day_percent',
        percent: '2.5',
        cap_percent: '15',
        grace_days: 4,
        source: {
          page: 4,
          text: 'If delivery is delayed beyond the Delivery Deadline, the first four (4) calendar days of delay shall not attract a late-delivery penalty. From the next day, a penalty of 2.5% of the value of the delayed Equipment shown on the relevant Invoice shall apply for each day of delay, subject to an aggregate ceiling of 15% of that Invoice value.',
        },
        deadline_source: {
          page: 4,
          text: 'For Orders governed by this Agreement, the required delivery date is 28 February 2027 (the “Delivery Deadline”), unless a later or different date is expressly agreed in a written amendment signed by both Parties.',
        },
      },
      {
        clause_type: 'volume_discount',
        min_quantity: 30,
        discount_percent: '7',
        source: {
          page: 6,
          text: 'A single Order containing 30 or more units qualifies for a volume discount of 7% on the Equipment value of that Order.',
        },
      },
      {
        clause_type: 'unit_price',
        item_name: 'Dell UltraSharp U2723QE Monitor',
        agreed_unit_price: '85000',
        source: {
          page: 6,
          text: 'The agreed unit price for each Dell UltraSharp U2723QE Monitor is PKR 85,000 per unit. The Vendor shall ensure that the unit amount shown on an Invoice does not exceed that agreed figure.',
        },
      },
      {
        clause_type: 'payment_terms',
        net_days: 28,
        source: {
          page: 6,
          text: 'The Buyer shall pay each valid and undisputed Invoice within 28 days of the invoice date.',
        },
      },
    ],
  },
  invoice: {
    invoice_number: 'INV-2026-0902',
    invoice_date: '2027-03-12',
    delivery_date: '2027-03-09',
    due_date: '2027-03-30',
    line_items: [
      {
        item_name: 'Dell UltraSharp U2723QE Monitor',
        quantity: 50,
        unit_price: '89250',
        line_total: '4462500',
      },
    ],
    adjustments: [],
    total_amount: '4462500',
    currency: 'PKR',
  },
  purchase_order: {
    po_number: 'PO-2026-0901',
    po_date: '2027-01-09',
    delivery_due_date: '2027-02-28',
    line_items: [
      {
        item_name: 'Dell UltraSharp U2723QE Monitor',
        quantity: 50,
        unit_price: '85000',
        line_total: '4250000',
      },
    ],
    total_amount: '4250000',
    currency: 'PKR',
  },
  llm_model: 'gemini-3.1-flash-lite',
  seconds: 71.4,
}