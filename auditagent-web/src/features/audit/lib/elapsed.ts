export const SLOW_AFTER_MS = 5 * 60 * 1000

/** How long a job has been running, from its creation time on the server (not from a timer here). */
export function elapsedMs(createdAt: string, now: number): number {
  const start = Date.parse(createdAt)
  return Number.isNaN(start) ? 0 : Math.max(0, now - start)
}

export function isSlow(createdAt: string, now: number): boolean {
  return elapsedMs(createdAt, now) > SLOW_AFTER_MS
}

/** 45000 -> "45 s"; 125000 -> "2 min 05 s". */
export function formatElapsed(ms: number): string {
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds} s`
  const rest = String(seconds % 60).padStart(2, '0')
  return `${Math.floor(seconds / 60)} min ${rest} s`
}