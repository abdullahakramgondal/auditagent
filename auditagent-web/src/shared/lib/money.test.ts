import { describe, expect, it } from 'vitest'
import { formatPercent, formatPkr } from './money'

describe('formatPkr', () => {
  it.each([
    ['0', 'PKR 0'],
    ['0.00', 'PKR 0'],
    ['999', 'PKR 999'],
    ['1000000', 'PKR 1,000,000'],
    ['10000000', 'PKR 10,000,000'],
    ['40000.0', 'PKR 40,000'],
    ['1041250.00', 'PKR 1,041,250'],
    ['1234.5', 'PKR 1,234.50'],
    ['1234.567', 'PKR 1,234.57'],
    ['-1736000', '-PKR 1,736,000'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatPkr(input)).toBe(expected)
  })

  it('shows a dash for a value that is not known, never zero', () => {
    expect(formatPkr(null)).toBe('—')
    expect(formatPkr(undefined)).toBe('—')
  })

  it('does not crash on text that is not a number', () => {
    expect(formatPkr('abc')).toBe('—')
    expect(formatPkr('')).toBe('—')
  })

  it('keeps every digit of an amount that a JavaScript number cannot hold', () => {
    expect(formatPkr('9007199254740993')).toBe('PKR 9,007,199,254,740,993')
  })
})

describe('formatPercent', () => {
  it.each([
    ['15.0', '15%'],
    ['2.50', '2.5%'],
    ['0.5', '0.5%'],
    ['100', '100%'],
    ['12.5', '12.5%'],
  ])('formats %s as %s', (input, expected) => {
    expect(formatPercent(input)).toBe(expected)
  })

  it('shows a dash for nothing or for text that is not a number', () => {
    expect(formatPercent(null)).toBe('—')
    expect(formatPercent('abc')).toBe('—')
  })
})