import { describe, expect, it } from 'vitest'
import { badgeOf } from './badgeMeta'

describe('badgeOf', () => {
  it('uses the look of the verdict for a finished audit', () => {
    expect(badgeOf('done', 'NON_COMPLIANT')).toMatchObject({
      label: 'Non-compliant',
      status: 'NON_COMPLIANT',
      busy: false,
    })
    expect(badgeOf('done', 'COMPLIANT').label).toBe('Compliant')
    expect(badgeOf('done', 'NEEDS_REVIEW').label).toBe('Needs human review')
  })

  it('is neutral and busy while a job waits or runs', () => {
    expect(badgeOf('queued', null)).toMatchObject({ label: 'Waiting', status: null, busy: true })
    expect(badgeOf('running', null)).toMatchObject({ label: 'Running', status: null, busy: true })
  })

  it('is neutral for a failed job, never a verdict colour', () => {
    const failed = badgeOf('failed', null)
    expect(failed).toMatchObject({ label: 'Failed', status: null, busy: false })
    expect(failed.className).toContain('slate')
  })

  it('does not claim a verdict for a finished job that has none', () => {
    expect(badgeOf('done', null)).toMatchObject({ label: 'Finished', status: null })
  })
})