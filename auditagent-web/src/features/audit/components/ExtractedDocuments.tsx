import type { ExtractedContract, Invoice, LineItem, PurchaseOrder } from '@/api/types'
import { formatDate } from '@/shared/lib/dates'
import { formatPkr } from '@/shared/lib/money'
import { clauseLabels } from '../lib/clauseLabels'
import { ruleSummary } from '../lib/ruleSummary'

type Props = {
  contract: ExtractedContract
  invoice: Invoice | null
  purchaseOrder: PurchaseOrder | null
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details className="rounded-lg border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer font-medium">{title}</summary>
      <div className="mt-3 flex flex-col gap-3 text-sm">{children}</div>
    </details>
  )
}

function Missing() {
  return <p className="text-slate-600">Not available: this document could not be proven.</p>
}

function Items({ items }: { items: LineItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b text-left text-slate-600">
            <th scope="col" className="py-2 pr-3 font-medium">
              Item
            </th>
            <th scope="col" className="py-2 pr-3 text-right font-medium">
              Qty
            </th>
            <th scope="col" className="py-2 pr-3 text-right font-medium">
              Unit price
            </th>
            <th scope="col" className="py-2 text-right font-medium">
              Amount
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.item_name}-${index}`} className="border-b">
              <th scope="row" className="py-2 pr-3 text-left font-normal">
                {item.item_name}
              </th>
              <td className="py-2 pr-3 text-right tabular-nums">{item.quantity}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatPkr(item.unit_price)}</td>
              <td className="py-2 text-right tabular-nums">{formatPkr(item.line_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ExtractedDocuments({ contract, invoice, purchaseOrder }: Props) {
  return (
    <section aria-labelledby="documents-heading" className="flex flex-col gap-3">
      <h2 id="documents-heading" className="text-lg font-semibold">
        The documents we read
      </h2>
      <p className="text-sm text-slate-600">
        What the system read from your PDFs. Compare it with the originals.
      </p>

      <Panel title="Contract rules">
        {contract.rules.length === 0 ? (
          <p className="text-slate-600">No rule was proven in the contract.</p>
        ) : (
          <ul className="space-y-3">
            {contract.rules.map((rule, index) => (
              <li key={`${rule.clause_type}-${index}`}>
                <p className="font-medium">{clauseLabels[rule.clause_type]}</p>
                <p>{ruleSummary(rule)}</p>
                <p className="text-slate-600">Contract, page {rule.source.page}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Purchase order">
        {purchaseOrder ? (
          <>
            <p>
              {purchaseOrder.po_number} · ordered {formatDate(purchaseOrder.po_date)} · delivery
              required by {formatDate(purchaseOrder.delivery_due_date)}
            </p>
            <Items items={purchaseOrder.line_items} />
            <p className="font-medium">Total: {formatPkr(purchaseOrder.total_amount)}</p>
          </>
        ) : (
          <Missing />
        )}
      </Panel>

      <Panel title="Invoice">
        {invoice ? (
          <>
            <p>
              {invoice.invoice_number} · issued {formatDate(invoice.invoice_date)} · delivered{' '}
              {formatDate(invoice.delivery_date)} · due {formatDate(invoice.due_date)}
            </p>
            <Items items={invoice.line_items} />
            {invoice.adjustments.length > 0 && (
              <ul className="space-y-1">
                {invoice.adjustments.map((adjustment, index) => (
                  <li key={`${adjustment.label}-${index}`}>
                    {adjustment.label}: {formatPkr(adjustment.amount)}
                  </li>
                ))}
              </ul>
            )}
            <p className="font-medium">Total: {formatPkr(invoice.total_amount)}</p>
          </>
        ) : (
          <Missing />
        )}
      </Panel>
    </section>
  )
}
