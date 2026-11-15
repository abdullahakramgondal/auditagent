import { describe, expect, it } from 'vitest'
import { MAX_BYTES, formatSize, sameFile, validatePdf } from './validation'

function pdf(name = 'a.pdf', content = '%PDF-1.4 test'): File {
  return new File([content], name, { type: 'application/pdf' })
}

describe('validatePdf', () => {
  it('accepts a file that starts with %PDF', async () => {
    expect(await validatePdf(pdf())).toBeNull()
  })

  it('refuses an empty file', async () => {
    expect(await validatePdf(pdf('a.pdf', ''))).toBe('This file is empty.')
  })

  it('refuses a file above the size limit', async () => {
    const big = pdf()
    Object.defineProperty(big, 'size', { value: MAX_BYTES + 1 })
    expect(await validatePdf(big)).toBe('This file is larger than 10 MB.')
  })

  it('accepts a file exactly at the size limit', async () => {
    const edge = pdf()
    Object.defineProperty(edge, 'size', { value: MAX_BYTES })
    expect(await validatePdf(edge)).toBeNull()
  })

  it('refuses a text file even when it is called .pdf', async () => {
    expect(await validatePdf(pdf('fake.pdf', 'hello world'))).toBe('This is not a PDF file.')
  })

  it('does not trust the browser type: a PDF without a type is accepted', async () => {
    const untyped = new File(['%PDF-1.7 x'], 'a.pdf')
    expect(await validatePdf(untyped)).toBeNull()
  })
})

describe('formatSize', () => {
  it.each([
    [0, '0 B'],
    [500, '500 B'],
    [2048, '2 KB'],
    [1572864, '1.5 MB'],
  ])('writes %d bytes as %s', (bytes, text) => {
    expect(formatSize(bytes)).toBe(text)
  })
})

describe('sameFile', () => {
  it('knows the same file again', () => {
    const file = pdf('a.pdf')
    expect(sameFile(file, file)).toBe(true)
  })

  it('tells two different files apart', () => {
    expect(sameFile(pdf('a.pdf'), pdf('b.pdf'))).toBe(false)
    expect(sameFile(pdf('a.pdf', '%PDF-1'), pdf('a.pdf', '%PDF-1 longer'))).toBe(false)
  })
})