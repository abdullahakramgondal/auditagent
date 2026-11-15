import Decimal from 'decimal.js'

const NOT_KNOWN = '—'

/**
 * "10000000" -> "PKR 10,000,000"; "40000.0" -> "PKR 40,000"; "1234.5" -> "PKR 1,234.50";
 * "-1736000" -> "-PKR 1,736,000"; null -> "—" (not known, never zero).
 * Money arrives as a string and is never turned into a JavaScript number.
 */
export function formatPkr(value: string | null | undefined): string {
  if (value === null || value === undefined) return NOT_KNOWN
  let amount: Decimal
  try {
    amount = new Decimal(value)
  } catch {
    return NOT_KNOWN
  }
  if (!amount.isFinite()) return NOT_KNOWN

  const absolute = amount.abs()
  const text = absolute.toFixed(absolute.isInteger() ? 0 : 2)
  const [whole, fraction] = text.split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const isZero = /^0(\.0+)?$/.test(text)
  const sign = amount.isNegative() && !isZero ? '-' : ''
  return fraction ? `${sign}PKR ${grouped}.${fraction}` : `${sign}PKR ${grouped}`
}

/** "15.0" -> "15%"; "2.50" -> "2.5%"; null -> "—". */
export function formatPercent(value: string | null | undefined): string {
  if (value === null || value === undefined) return NOT_KNOWN
  try {
    return `${new Decimal(value).toFixed()}%`
  } catch {
    return NOT_KNOWN
  }
}