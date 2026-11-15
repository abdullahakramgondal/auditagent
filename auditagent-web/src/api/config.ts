const DEFAULT_API_BASE_URL = 'http://localhost:8000'

/**
 * The base URL of the backend. Not set -> the local backend. Set but empty -> the same origin
 * (the production build is served by the backend itself). A trailing slash is removed.
 */
export function normalizeBaseUrl(raw: unknown): string {
  if (typeof raw !== 'string') return DEFAULT_API_BASE_URL
  return raw.trim().replace(/\/+$/, '')
}

export const env = {
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL),
}