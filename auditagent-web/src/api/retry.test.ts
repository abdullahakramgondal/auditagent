import { describe, expect, it } from 'vitest'
import { ApiError } from './client'
import { shouldRetry } from './retry'

describe('shouldRetry', () => {
  it('tries a network error again, but not forever', () => {
    const error = new ApiError('network', 'down')
    expect(shouldRetry(0, error)).toBe(true)
    expect(shouldRetry(1, error)).toBe(true)
    expect(shouldRetry(2, error)).toBe(false)
  })

  it('tries a server error (5xx) again', () => {
    expect(shouldRetry(0, new ApiError('http', 'x', 500))).toBe(true)
    expect(shouldRetry(0, new ApiError('http', 'x', 503))).toBe(true)
  })

  it('never tries a client error (4xx) again', () => {
    expect(shouldRetry(0, new ApiError('http', 'x', 404))).toBe(false)
    expect(shouldRetry(0, new ApiError('http', 'x', 409))).toBe(false)
    expect(shouldRetry(0, new ApiError('http', 'x', 413))).toBe(false)
  })

  it('never tries a bad response again', () => {
    expect(shouldRetry(0, new ApiError('bad_response', 'x'))).toBe(false)
  })

  it('tries an unknown error again', () => {
    expect(shouldRetry(0, new Error('something else'))).toBe(true)
  })
})