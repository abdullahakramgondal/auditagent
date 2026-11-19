import { z } from 'zod'

// The shapes of the real backend (src/auditagent/api/schemas.py). They are the contract:
// a failed parse is a bug between backend and front end, never a reason to show half a result.

// Money and percentages arrive as strings ("4462500.00", "2.5"). They stay strings.
const decimalString = z.string().regex(/^-?\d+(\.\d+)?$/)
const isoDate = z.iso.date()
const isoDateTime = z.iso.datetime({ offset: true })

export const AuditStatusSchema = z.enum(['COMPLIANT', 'NON_COMPLIANT', 'NEEDS_REVIEW'])
export const ClauseTypeSchema = z.enum([
  'late_penalty',
  'volume_discount',
  'payment_terms',
  'unit_price',
])
export const JobStateSchema = z.enum(['queued', 'running', 'done', 'failed'])
export const ErrorKindSchema = z.enum(['bad_file', 'provider_unavailable', 'internal'])
export const ReasonSourceSchema = z.enum(['contract', 'invoice', 'purchase_order', 'audit'])

export const SourceSchema = z.object({
  page: z.number().int().min(1),
  text: z.string().min(1),
})

export const FindingSchema = z.object({
  clause_type: ClauseTypeSchema,
  description: z.string(),
  source: SourceSchema,
  expected_amount: decimalString.nullable(),
  billed_amount: decimalString.nullable(),
  difference: decimalString,
})

export const ReviewReasonSchema = z.object({
  source: ReasonSourceSchema,
  field: z.string(),
  reason: z.string(),
})

// ---- the documents that the agents read ----

const LatePenaltyRuleSchema = z.object({
  clause_type: z.literal('late_penalty'),
  deadline: isoDate,
  mode: z.enum(['flat_percent', 'per_day_percent']),
  percent: decimalString,
  cap_percent: decimalString.nullable(),
  grace_days: z.number().int().min(0),
  source: SourceSchema,
  deadline_source: SourceSchema.nullable(),
})

const VolumeDiscountRuleSchema = z.object({
  clause_type: z.literal('volume_discount'),
  min_quantity: z.number().int().min(1),
  discount_percent: decimalString,
  source: SourceSchema,
})

const PaymentTermsRuleSchema = z.object({
  clause_type: z.literal('payment_terms'),
  net_days: z.number().int().min(0),
  source: SourceSchema,
})

const UnitPriceRuleSchema = z.object({
  clause_type: z.literal('unit_price'),
  item_name: z.string().min(1),
  agreed_unit_price: decimalString,
  source: SourceSchema,
})

export const ContractRuleSchema = z.discriminatedUnion('clause_type', [
  LatePenaltyRuleSchema,
  VolumeDiscountRuleSchema,
  PaymentTermsRuleSchema,
  UnitPriceRuleSchema,
])

export const ExtractedContractSchema = z.object({
  rules: z.array(ContractRuleSchema),
})

export const LineItemSchema = z.object({
  item_name: z.string().min(1),
  quantity: z.number().int().min(1),
  unit_price: decimalString,
  line_total: decimalString,
})

export const AdjustmentSchema = z.object({
  label: z.string().min(1),
  amount: decimalString, // negative = credit to the buyer
})

export const InvoiceSchema = z.object({
  invoice_number: z.string().min(1),
  invoice_date: isoDate,
  delivery_date: isoDate.nullable(),
  due_date: isoDate.nullable(),
  line_items: z.array(LineItemSchema).min(1),
  adjustments: z.array(AdjustmentSchema),
  total_amount: decimalString,
  currency: z.literal('PKR'),
})

export const PurchaseOrderSchema = z.object({
  po_number: z.string().min(1),
  po_date: isoDate,
  delivery_due_date: isoDate.nullable(),
  line_items: z.array(LineItemSchema).min(1),
  total_amount: decimalString,
  currency: z.literal('PKR'),
})

// ---- the endpoints ----

/** POST /audits answers 202 with this. */
export const SubmittedSchema = z.object({
  audit_id: z.string(),
})

/** GET /audits/{id} (the state of one job) and every row of GET /audits (the history). */
export const JobInfoSchema = z.object({
  audit_id: z.string(),
  state: JobStateSchema,
  created_at: isoDateTime,
  provider: z.string().nullable(),
  model: z.string().nullable(),
  error: z.string().nullable(),
  error_kind: ErrorKindSchema.nullable(),
  status: AuditStatusSchema.nullable(),
  total_difference: decimalString.nullable(),
  llm_model: z.string().nullable(),
})

export const HistorySchema = z.array(JobInfoSchema)

// ---- the result in plain words (made by the backend, shown as it is) ----

export const PlainProblemSchema = z.object({
  clause_type: ClauseTypeSchema,
  title: z.string(),
  amount_text: z.string(),
  paragraphs: z.array(z.string()),
  page: z.number().int().min(1),
  quote: z.string().min(1),
})

/** One line of the working-out (the sums are made by the backend). */
export const CalcStepSchema = z.object({
  kind: z.enum(['start', 'base', 'minus', 'result', 'difference']),
  label: z.string(),
  detail: z.string(),
  amount_text: z.string(),
})

/** One of the four things that the system checks, and how it went. */
export const CheckItemSchema = z.object({
  clause_type: ClauseTypeSchema,
  label: z.string(),
  state: z.enum(['ok', 'problem', 'unchecked', 'none']),
  detail: z.string(),
})

/** One thing the system could not prove, in plain words. */
export const ReviewNoteSchema = z.object({
  group: z.string(),
  title: z.string(),
  what: z.string(),
  todo: z.string(),
  technical: z.string(),
})

export const PlainSummarySchema = z.object({
  headline: z.string(),
  advice: z.string(),
  problems: z.array(PlainProblemSchema),
  calculation: z.array(CalcStepSchema).default([]),
  checks: z.array(CheckItemSchema).default([]),
  review_notes: z.array(ReviewNoteSchema).default([]),
})

/** GET /audits/{id}/result. The amounts are null when no invoice could be proven. */
export const AuditResultSchema = z.object({
  audit_id: z.string(),
  created_at: isoDateTime,
  status: AuditStatusSchema,
  billed_total: decimalString.nullable(),
  correct_payable: decimalString.nullable(),
  total_difference: decimalString.nullable(),
  amounts_provisional: z.boolean(),
  plain: PlainSummarySchema,
  findings: z.array(FindingSchema),
  review_reasons: z.array(ReviewReasonSchema),
  contract: ExtractedContractSchema,
  invoice: InvoiceSchema.nullable(),
  purchase_order: PurchaseOrderSchema.nullable(),
  llm_model: z.string(),
  seconds: z.number(),
})

/** GET /audits/summary: counted and added by the backend, the front end never adds money. */
export const SummarySchema = z.object({
  total: z.number().int().min(0),
  in_progress: z.number().int().min(0),
  failed: z.number().int().min(0),
  compliant: z.number().int().min(0),
  non_compliant: z.number().int().min(0),
  needs_review: z.number().int().min(0),
  total_difference: decimalString,
})

/** GET /auth/me, POST /auth/login and /auth/register: the person who is logged in. */
export const UserSchema = z.object({
  email: z.string(),
})

/** POST /auth/logout. */
export const LoggedOutSchema = z.object({
  status: z.string(),
})