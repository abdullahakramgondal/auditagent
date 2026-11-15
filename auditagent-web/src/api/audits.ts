import { request } from './client'
import { env } from './config'
import { AuditResultSchema, HistorySchema, JobInfoSchema, SubmittedSchema } from './schemas'

export type AuditFiles = {
  contract: File
  purchase_order: File
  invoice: File
}

export type CreateAuditInput = {
  files: AuditFiles
  /** Optional: "gemini" or "ollama". Without it the backend uses its own settings. */
  provider?: string
  /** Optional model name for the chosen provider. */
  model?: string
}

/** POST /audits: starts an audit, answers 202 with its id. */
export function createAudit(input: CreateAuditInput) {
  const body = new FormData()
  body.append('contract', input.files.contract)
  body.append('purchase_order', input.files.purchase_order)
  body.append('invoice', input.files.invoice)
  if (input.provider) body.append('provider', input.provider)
  if (input.model) body.append('model', input.model)
  // No Content-Type header: the browser adds the multipart boundary itself.
  return request('/audits', SubmittedSchema, { method: 'POST', body })
}

/** GET /audits/{id}: the state of one job. */
export function getAuditState(id: string) {
  return request(`/audits/${encodeURIComponent(id)}`, JobInfoSchema)
}

/** GET /audits/{id}/result: the finished audit (409 while the job is not done). */
export function getAuditResult(id: string) {
  return request(`/audits/${encodeURIComponent(id)}/result`, AuditResultSchema)
}

/** GET /audits: the history, newest first. */
export function listAudits() {
  return request('/audits', HistorySchema)
}

/** The address of the JSON download (a plain link: the backend sends it as an attachment). */
export function resultJsonUrl(id: string): string {
  return `${env.apiBaseUrl}/audits/${encodeURIComponent(id)}/result.json`
}