import { UploadForm } from '@/features/upload'

export function UploadPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Start a new audit</h1>
        <p className="mt-1 text-sm text-slate-600 md:text-base">
          Upload the three documents of one purchase: the contract, the purchase order and the
          invoice.
        </p>
        <p className="mt-2 text-sm text-slate-600">
          Use PDFs that you can select text in. A scan or a photo of paper cannot be read.
        </p>
      </div>
      <UploadForm />
    </div>
  )
}