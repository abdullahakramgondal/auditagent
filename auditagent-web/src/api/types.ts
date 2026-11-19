import type { z } from 'zod'
import type {
  AdjustmentSchema,
  AuditResultSchema,
  AuditStatusSchema,
  CalcStepSchema,
  CheckItemSchema,
  ClauseTypeSchema,
  ContractRuleSchema,
  ErrorKindSchema,
  ExtractedContractSchema,
  FindingSchema,
  InvoiceSchema,
  JobInfoSchema,
  JobStateSchema,
  LineItemSchema,
  PlainProblemSchema,
  PlainSummarySchema,
  PurchaseOrderSchema,
  ReviewNoteSchema,
  ReviewReasonSchema,
  SourceSchema,
  SubmittedSchema,
  SummarySchema,
  UserSchema,
} from './schemas'

export type AuditStatus = z.infer<typeof AuditStatusSchema>
export type ClauseType = z.infer<typeof ClauseTypeSchema>
export type JobState = z.infer<typeof JobStateSchema>
export type ErrorKind = z.infer<typeof ErrorKindSchema>
export type Source = z.infer<typeof SourceSchema>
export type Finding = z.infer<typeof FindingSchema>
export type ReviewReason = z.infer<typeof ReviewReasonSchema>
export type ContractRule = z.infer<typeof ContractRuleSchema>
export type ExtractedContract = z.infer<typeof ExtractedContractSchema>
export type LineItem = z.infer<typeof LineItemSchema>
export type Adjustment = z.infer<typeof AdjustmentSchema>
export type Invoice = z.infer<typeof InvoiceSchema>
export type PurchaseOrder = z.infer<typeof PurchaseOrderSchema>
export type Submitted = z.infer<typeof SubmittedSchema>
export type JobInfo = z.infer<typeof JobInfoSchema>
export type AuditResult = z.infer<typeof AuditResultSchema>
export type Summary = z.infer<typeof SummarySchema>
export type PlainProblem = z.infer<typeof PlainProblemSchema>
export type PlainSummary = z.infer<typeof PlainSummarySchema>
export type CalcStep = z.infer<typeof CalcStepSchema>
export type CheckItem = z.infer<typeof CheckItemSchema>
export type ReviewNote = z.infer<typeof ReviewNoteSchema>
export type User = z.infer<typeof UserSchema>
