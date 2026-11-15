const NOT_KNOWN = '—'
const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/
const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]
const MONTHS_SHORT = MONTHS.map((name) => name.slice(0, 3))

const KARACHI = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Karachi',
  day: 'numeric',
  month: 'numeric',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/**
 * A date without a time, "2026-10-15" -> "15 October 2026".
 * The three numbers are read by hand: new Date("2026-10-15") is UTC midnight and can show the day before.
 */
export function formatDate(value: string | null | undefined): string {
  if (!value) return NOT_KNOWN
  const match = DATE_ONLY.exec(value)
  if (!match) return NOT_KNOWN
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const check = new Date(Date.UTC(year, month - 1, day))
  const real =
    check.getUTCFullYear() === year &&
    check.getUTCMonth() === month - 1 &&
    check.getUTCDate() === day
  return real ? `${day} ${MONTHS[month - 1]} ${year}` : NOT_KNOWN
}

/** A timestamp, "2026-10-29T04:41:00Z" -> "29 Oct 2026, 09:41" in Pakistan time. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return NOT_KNOWN
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return NOT_KNOWN
  const parts = Object.fromEntries(KARACHI.formatToParts(moment).map((p) => [p.type, p.value]))
  const month = MONTHS_SHORT[Number(parts.month) - 1]
  return `${Number(parts.day)} ${month} ${parts.year}, ${parts.hour}:${parts.minute}`
}