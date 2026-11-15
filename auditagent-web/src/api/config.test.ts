import { describe, expect, it } from 'vitest'
import { normalizeBaseUrl } from './config'

describe('normalizeBaseUrl', () => {
  it('uses the local backend when nothing is set', () => {
    expect(normalizeBaseUrl(undefined)).toBe('http://localhost:8000')
  })

  it('keeps an empty value empty: the same origin', () => {
    expect(normalizeBaseUrl('')).toBe('')
  })

  it('removes a trailing slash and spaces', () => {
    expect(normalizeBaseUrl('http://example.test:9000/')).toBe('http://example.test:9000')
    expect(normalizeBaseUrl('  http://example.test//  ')).toBe('http://example.test')
  })

  it('keeps a normal address as it is', () => {
    expect(normalizeBaseUrl('https://audit.example.test')).toBe('https://audit.example.test')
  })
})