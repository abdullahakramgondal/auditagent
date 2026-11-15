import { z } from 'zod'
import { env } from './config'

export type ApiErrorKind = 'network' | 'http' | 'bad_response'

/**
 * Everything that can go wrong with a call to the backend:
 *   network       the service cannot be reached
 *   http          the service answered with an error status (404, 409, 413, 500, ...)
 *   bad_response  the answer does not have the shape of the contract (a bug, never shown as a result)
 */
export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null

  constructor(kind: ApiErrorKind, message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

/** FastAPI answers {"detail": "..."} for an error. A 422 has a list there: not shown to people. */
async function messageOf(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      typeof body.detail === 'string' &&
      body.detail !== ''
    ) {
      return body.detail
    }
  } catch {
    // the body is not JSON: use the general message below
  }
  return `The service answered with an error (${response.status}).`
}

/** One call to the backend. The answer must match the schema, or the call fails with an ApiError. */
export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, init)
  } catch {
    throw new ApiError('network', 'The service is not reachable. Check that the backend is running.')
  }

  if (!response.ok) {
    throw new ApiError('http', await messageOf(response), response.status)
  }

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new ApiError('bad_response', 'The service sent an unexpected response.')
  }

  const parsed = schema.safeParse(body)
  if (!parsed.success) {
    console.error('Unexpected response from', path, z.prettifyError(parsed.error))
    throw new ApiError('bad_response', 'The service sent an unexpected response.')
  }
  return parsed.data
}