import { useEffect, useRef } from 'react'
import type { AuditResult } from '@/api/types'
import { formatDateTime } from '@/shared/lib/dates'
import { CalculationSummary } from './CalculationSummary'
import { Checklist } from './Checklist'
import { ExportButtons } from './ExportButtons'
import { ExtractedDocuments } from './ExtractedDocuments'
import { MoneySummary } from './MoneySummary'
import { ProblemList } from './ProblemList'
import { ReviewReasons } from './ReviewReasons'
import { StatusBanner } from './StatusBanner'

export function AuditResultView({ result }: { result: AuditResult }) {
  const heading = useRef<HTMLHeadingElement>(null)

  // Focus moves to the heading when the result appears.
  useEffect(() => {
    heading.current?.focus()
  }, [])

  const { plain } = result
  const reasons =
    plain.review_notes.length > 0 ? <ReviewReasons notes={plain.review_notes} /> : null
  const needsReview = result.status === 'NEEDS_REVIEW'
  const invoice = result.invoice ? ` · Invoice ${result.invoice.invoice_number}` : ''

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1
            ref={heading}
            tabIndex={-1}
            className="text-2xl font-semibold tracking-tight focus:outline-none"
          >
            Invoice check result
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Checked on {formatDateTime(result.created_at)}
            {invoice}
          </p>
        </div>
        <ExportButtons id={result.audit_id} />
      </div>

      <StatusBanner status={result.status} headline={plain.headline} advice={plain.advice} />
      {needsReview && reasons}
      {result.billed_total !== null && (
        <MoneySummary
          billedTotal={result.billed_total}
          correctPayable={result.correct_payable}
          totalDifference={result.total_difference}
          provisional={result.amounts_provisional}
          showDifference={result.status === 'NON_COMPLIANT'}
        />
      )}
      <ProblemList problems={plain.problems} />
      <CalculationSummary steps={plain.calculation} />
      <Checklist items={plain.checks} />
      {!needsReview && reasons}
      <ExtractedDocuments
        contract={result.contract}
        invoice={result.invoice}
        purchaseOrder={result.purchase_order}
      />

      <p className="text-xs text-slate-500">
        Report number {result.audit_id} · checked by {result.llm_model}
      </p>
    </div>
  )
}