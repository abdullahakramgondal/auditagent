import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useCreateAudit } from '../hooks/useCreateAudit'
import { sameFile, validatePdf } from '../lib/validation'
import { FileSlot } from './FileSlot'

type SlotKey = 'contract' | 'purchase_order' | 'invoice'
type SlotState = { file: File | null; error: string | null }

const SLOTS: { key: SlotKey; label: string }[] = [
  { key: 'contract', label: 'Contract' },
  { key: 'purchase_order', label: 'Purchase order' },
  { key: 'invoice', label: 'Invoice' },
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
        {SLOTS.map(({ key, label }) => (
          <FileSlot
            key={key}
            id={`file-${key}`}
            label={label}
            file={slots[key].file}
            error={slots[key].error}
            onSelect={(file) => void choose(key, file)}
            onRemove={() => remove(key)}
          />
        ))}
      </div>

      {create.isError && <ErrorNotice message={create.error.message} />}

      <button
        type="submit"
        disabled={!ready || create.isPending}
        className="w-full rounded-md bg-slate-900 px-5 py-3 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300 md:w-auto md:self-end"
      >
        {create.isPending ? 'Uploading…' : 'Start audit'}
      </button>
    </form>
  )
}