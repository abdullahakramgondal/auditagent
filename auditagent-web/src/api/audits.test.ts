import { describe, expect, it } from 'vitest'
import { compliant } from '@/mocks/fixtures/compliant'
import { history } from '@/mocks/fixtures/history'
import { fetchMock, installFetchMock, respondJson } from '@/test/fetchMock'
import {
  createAudit,
  getAuditResult,
  getAuditState,
  listAudits,
  resultJsonUrl,
} from './audits'

installFetchMock()

function pdf(name: string): File {
  return new File(['%PDF-1.4'], name, { type: 'application/pdf' })
}

const files = {
  contract: pdf('contract.pdf'),
  purchase_order: pdf('po.pdf'),
  invoice: pdf('invoice.pdf'),
}

describe('createAudit', () => {
  it('posts the three files as multipart fields and returns the audit id', async () => {
    respondJson({ audit_id: 'abc123' }, 202)
    const result = await createAudit({ files })
    expect(result.audit_id).toBe('abc123')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://localhost:8000/audits')
    expect(init?.method).toBe('POST')
    expect(init?.headers).toBeUndefined() // the browser sets the multipart boundary
    const body = init?.body as FormData
    expect((body.get('contract') as File).name).toBe('contract.pdf')
    expect((body.get('purchase_order') as File).name).toBe('po.pdf')
    expect((body.get('invoice') as File).name).toBe('invoice.pdf')
    expect(body.has('provider')).toBe(false)
    expect(body.has('model')).toBe(false)
  })

  it('sends the provider and the model only when they are given', async () => {
    respondJson({ audit_id: 'abc123' }, 202)
    await createAudit({ files, provider: 'ollama', model: 'qwen2.5:7b' })
    const body = fetchMock.mock.calls[0][1]?.body as FormData
    expect(body.get('provider')).toBe('ollama')
    expect(body.get('model')).toBe('qwen2.5:7b')
  })
})

describe('getAuditState', () => {
  it('reads the state of one job', async () => {
    respondJson(history[3])
    const job = await getAuditState('3f9c2a7e5b1d4c8a9e0f6b2d7a1c4e83')
    expect(job.state).toBe('done')
    expect(job.status).toBe('NON_COMPLIANT')
    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8000/audits/3f9c2a7e5b1d4c8a9e0f6b2d7a1c4e83',
    )
  })

  it('writes an unusual id so that it cannot change the address', async () => {
    respondJson(history[3])
    await getAuditState('a/b?c')
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/audits/a%2Fb%3Fc')
  })
})

describe('getAuditResult', () => {
  it('reads the finished audit', async () => {
    respondJson(compliant)
    const result = await getAuditResult('abc')
    expect(result.status).toBe('COMPLIANT')
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/audits/abc/result')
  })
})

describe('listAudits', () => {
  it('reads the history', async () => {
    respondJson(history)
    const rows = await listAudits()
    expect(rows).toHaveLength(5)
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/audits')
  })
})

describe('resultJsonUrl', () => {
  it('is the address of the JSON download', () => {
    expect(resultJsonUrl('abc')).toBe('http://localhost:8000/audits/abc/result.json')
    expect(resultJsonUrl('a/b')).toBe('http://localhost:8000/audits/a%2Fb/result.json')
  })
})