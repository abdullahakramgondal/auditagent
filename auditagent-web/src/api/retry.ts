import { ApiError } from './client'

const MAX_RETRIES = 2

/**
 * Whether TanStack Query tries a failed call again. A network error or a 5xx may pass by itself.
 * A 4xx (unknown audit, result not ready, file refused) and a bad response never change by waiting.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false
  if (error instanceof ApiError) {
    if (error.kind === 'bad_response') return false
    if (error.kind === 'http' && error.status !== null && error.status < 500) return false
  }
  return true
}