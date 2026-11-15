import { Link } from 'react-router'
import type { JobInfo } from '@/api/types'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'

function copyOf(job: JobInfo): string {
  if (job.error_kind === 'provider_unavailable') {
    return 'The language model service is busy. Try again in a few minutes.'
  }
  if (job.error_kind === 'bad_file') {
    return job.error ?? 'One of the files cannot be used.'
  }
  return job.error ?? 'Unexpected error while auditing.'
}

/** The text comes from the kind of error, never from guessing at the wording of a message. */
export function FailedView({ job }: { job: JobInfo }) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold tracking-tight">The audit could not finish</h1>
      <ErrorNotice message={copyOf(job)} />
      <Link
        to="/"
        className="self-start rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Start a new audit
      </Link>
    </div>
  )
}