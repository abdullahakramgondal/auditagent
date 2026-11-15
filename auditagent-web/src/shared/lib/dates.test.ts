import { describe, expect, it } from 'vitest'
import { formatDate, formatDateTime } from './dates'

describe('formatDate', () => {
  it.each([
    ['2026-10-15', '15 October 2026'],
    ['2027-03-09', '9 March 2027'],
    ['2027-02-28', '28 February 2027'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatDate(input)).toBe(expected)
  })

  it('shows a dash for nothing', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
    expect(formatDate('')).toBe('—')
  })

  it('refuses a date that does not exist or is not written as year-month-day', () => {
    expect(formatDate('2026-02-30')).toBe('—')
    expect(formatDate('15/10/2026')).toBe('—')
    expect(formatDate('2026-10-15T00:00:00Z')).toBe('—')
  })
})

describe('formatDateTime', () => {
  it('shows a UTC time in Pakistan time (UTC+5)', () => {
    expect(formatDateTime('2026-10-29T04:41:00Z')).toBe('29 Oct 2026, 09:41')
  })

  it('moves to the next day when Pakistan time passes midnight', () => {
    expect(formatDateTime('2026-11-14T19:00:00Z')).toBe('15 Nov 2026, 00:00')
  })

  it('reads a timestamp with a time zone offset and with microseconds', () => {
    expect(formatDateTime('2026-10-29T09:41:00+05:00')).toBe('29 Oct 2026, 09:41')
    expect(formatDateTime('2026-11-14T09:41:12.482913Z')).toBe('14 Nov 2026, 14:41')
  })

  it('writes September as Sep', () => {
    expect(formatDateTime('2026-09-05T10:00:00Z')).toBe('5 Sep 2026, 15:00')
  })

  it('shows a dash for nothing or for text that is not a time', () => {
    expect(formatDateTime(null)).toBe('—')
    expect(formatDateTime('not a date')).toBe('—')
  })
})