import { ApiError, request } from './client'
import { LoggedOutSchema, UserSchema } from './schemas'
import type { User } from './types'

function postJson(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

/** GET /auth/me: the person who is logged in, or null when nobody is (401 is not an error here). */
export async function getMe(): Promise<User | null> {
  try {
    return await request('/auth/me', UserSchema)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}

export function login(email: string, password: string) {
  return request('/auth/login', UserSchema, postJson({ email, password }))
}

export function register(email: string, password: string) {
  return request('/auth/register', UserSchema, postJson({ email, password }))
}

export function logout() {
  return request('/auth/logout', LoggedOutSchema, { method: 'POST' })
}