import { useEffect, useRef } from 'react'
import type { AuditResult } from '@/api/types'
import { formatDateTime } from '@/shared/lib/dates'
import { bannerMessage } from '../lib/bannerMessage'
import { ExportButtons } from './ExportButtons'
import { ExtractedDocuments } from './ExtractedDocuments'
import { FindingsTable } from './FindingsTable'
import { MoneySummary } from './MoneySummary'
import { ReviewReasons } from './ReviewReasons'
import { StatusBanner } from './StatusBanner'

export function AuditResultView({ result }: { result: AuditResult }) {
  const heading = useRef<HTMLHeadingElement>(null)

  // Focus moves to the heading when the result appears.
  useEffect(() => {
    heading.current?.focus()
  }, [])

  const reasons =
    result.review_reasons.length > 0 ? <ReviewReasons reasons={result.review_reasons} /> : null
  const needsReview = result.status === 'NEEDS_REVIEW'

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold tracking-tight">
            Audit result
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Audit {result.audit_id} · {formatDateTime(result.created_at)} · {result.llm_model}
          </p>
        </div>
        <ExportButtons id={result.audit_id} />
      </div>

      <StatusBanner
        status={result.status}
        message={bannerMessage(result.status, result.total_difference)}
      />
      {needsReview && reasons}
      <MoneySummary
        billedTotal={result.billed_total}
        correctPayable={result.correct_payable}
        totalDifference={result.total_difference}
        provisional={result.amounts_provisional}
      />
      {!needsReview && reasons}
      <FindingsTable findings={result.findings} />
      <ExtractedDocuments
        contract={result.contract}
        invoice={result.invoice}
        purchaseOrder={result.purchase_order}
      />
    </div>
  )
}