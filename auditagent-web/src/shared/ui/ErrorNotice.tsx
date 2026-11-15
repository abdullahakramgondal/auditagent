type Props = {
  message: string
  onRetry?: () => void
}

export function ErrorNotice({ message, onRetry }: Props) {
  return (
    <div role="alert" className="rounded-lg border-l-4 border-red-600 bg-red-50 p-4 text-red-900">
      <p className="font-semibold">Something went wrong</p>
      <p className="mt-1 text-sm">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-red-600 px-3 py-1.5 text-sm font-medium hover:bg-red-100"
        >
          Try again
        </button>
      )}
    </div>
  )
}