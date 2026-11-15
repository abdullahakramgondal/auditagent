import { afterEach, beforeEach, vi } from 'vitest'

export const fetchMock = vi.fn<typeof fetch>()

/** Call once at the top of a test file: every test gets a clean fake fetch. */
export function installFetchMock(): void {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })
}

export function respondJson(body: unknown, status = 200): void {
  fetchMock.mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )
}

export function respondText(text: string, status = 200): void {
  fetchMock.mockImplementation(() => Promise.resolve(new Response(text, { status })))
}

export function failNetwork(): void {
  fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
}