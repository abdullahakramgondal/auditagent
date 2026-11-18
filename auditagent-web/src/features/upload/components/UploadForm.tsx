import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useCreateAudit } from '../hooks/useCreateAudit'
import { sameFile, validatePdf } from '../lib/validation'
import { FileSlot } from './FileSlot'

type SlotKey = 'contract' | 'purchase_order' | 'invoice'
type SlotState = { file: File | null; error: string | null }

const SLOTS: { key: SlotKey; label: string; hint: string }[] = [
  {
    key: 'contract',
    label: 'Contract',
    hint: 'The agreement you signed with the vendor. It holds the price, discount, delivery and payment rules.',
  },
  {
    key: 'purchase_order',
    label: 'Purchase order',
    hint: 'What you ordered: the items, the quantity and the delivery date you asked for.',
  },
  {
    key: 'invoice',
    label: 'Invoice',
    hint: 'The bill the vendor sent you, with the amount they want you to pay.',
  },
]

const EMPTY: Record<SlotKey, SlotState> = {
  contract: { file: null, error: null },
  purchase_order: { file: null, error: null },
  invoice: { file: null, error: null },
}

export function UploadForm() {
  const [slots, setSlots] = useState(EMPTY)
  const navigate = useNavigate()
  const create = useCreateAudit()

  async function choose(key: SlotKey, file: File) {
    const problem = await validatePdf(file)
    setSlots((current) => {
      let error = problem
      if (!error) {
        const twin = SLOTS.find(({ key: other }) => {
          const existing = current[other].file
          return other !== key && existing !== null && sameFile(existing, file)
        })
        if (twin) error = `This is the same file as the ${twin.label.toLowerCase()}.`
      }
      return { ...current, [key]: { file: error ? null : file, error } }
    })
  }

  function remove(key: SlotKey) {
    setSlots((current) => ({ ...current, [key]: { file: null, error: null } }))
  }

  const { contract, purchase_order, invoice } = {
    contract: slots.contract.file,
    purchase_order: slots.purchase_order.file,
    invoice: slots.invoice.file,
  }
  const ready = contract !== null && purchase_order !== null && invoice !== null
  const chosen = [contract, purchase_order, invoice].filter((file) => file !== null).length

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!contract || !purchase_order || !invoice) return
    create.mutate(
      { files: { contract, purchase_order, invoice } },
      { onSuccess: (started) => void navigate(`/audits/${started.audit_id}`) },
    )
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-6">
      <div className="grid gap-4 md:grid-cols-3">
        {SLOTS.map(({ key, label, hint }) => (
          <FileSlot
            key={key}
            id={`file-${key}`}
            label={label}
            hint={hint}
            file={slots[key].file}
            error={slots[key].error}
            onSelect={(file) => void choose(key, file)}
            onRemove={() => remove(key)}
          />
        ))}
      </div>

      {create.isError && <ErrorNotice message={create.error.message} />}

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <p aria-live="polite" className="text-sm text-slate-600">
          {ready ? 'All three files are ready.' : `${chosen} of 3 files chosen.`}
        </p>
        <button
          type="submit"
          disabled={!ready || create.isPending}
          className="min-h-11 w-full rounded-md bg-slate-900 px-5 py-3 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300 md:w-auto"
        >
          {create.isPending ? 'Uploading…' : 'Start audit'}
        </button>
      </div>
    </form>
  )
}