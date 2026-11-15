import { useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { MAX_BYTES, formatSize } from '../lib/validation'

type Props = {
  id: string
  label: string
  file: File | null
  error: string | null
  onSelect: (file: File) => void
  onRemove: () => void
}

function toneOf(file: File | null, error: string | null, dragging: boolean): string {
  if (error) return 'border-solid border-red-600 bg-red-50'
  if (file) return 'border-solid border-green-600 bg-green-50'
  if (dragging) return 'border-dashed border-blue-600 bg-blue-50'
  return 'border-dashed border-slate-300 bg-white'
}

export function FileSlot({ id, label, file, error, onSelect, onRemove }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const name = label.toLowerCase()

  function onChange(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0]
    if (chosen) onSelect(chosen)
    event.target.value = '' // the same file can be chosen again after a removal
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    const dropped = event.dataTransfer.files[0]
    if (dropped) onSelect(dropped)
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex min-h-44 flex-col justify-between gap-4 rounded-lg border-2 p-4 focus-within:ring-2 focus-within:ring-blue-600 md:p-6 ${toneOf(file, error, dragging)}`}
      >
        <label htmlFor={id} className="text-base font-semibold">
          {label}
        </label>
        <input
          ref={input}
          id={id}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          onChange={onChange}
        />

        {file ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-start gap-2">
              <svg
                aria-hidden="true"
                viewBox="0 0 20 20"
                className="mt-0.5 size-5 shrink-0 text-green-700"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.7-9.3a1 1 0 00-1.4-1.4L9 10.6 7.7 9.3a1 1 0 00-1.4 1.4l2 2a1 1 0 001.4 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="min-w-0">
                <p className="break-all text-sm font-medium">{file.name}</p>
                <p className="text-sm text-slate-600">{formatSize(file.size)}</p>
              </div>
            </div>
            <button
              type="button"
              aria-label={`Remove ${name} file`}
              onClick={onRemove}
              className="self-start rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-100"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-slate-600">Drop a PDF here, or</p>
            <button
              type="button"
              aria-label={`Choose ${name} file`}
              onClick={() => input.current?.click()}
              className="self-start rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-100"
            >
              Choose file
            </button>
            <p className="text-xs text-slate-500">PDF, up to {MAX_BYTES / 1024 / 1024} MB</p>
          </div>
        )}
      </div>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}