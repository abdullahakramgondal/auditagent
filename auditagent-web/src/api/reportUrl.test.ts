import { describe, expect, it } from 'vitest'
import { reportPdfUrl } from './audits'

describe('reportPdfUrl', () => {
  it('is the address of the PDF report', () => {
    expect(reportPdfUrl('abc')).toBe('http://localhost:8000/audits/abc/report.pdf')
  })

  it('writes an unusual id so that it cannot change the address', () => {
    expect(reportPdfUrl('a/b')).toBe('http://localhost:8000/audits/a%2Fb/report.pdf')
  })
})