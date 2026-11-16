const all = ['audits'] as const

/** Query keys of the audit data. Features invalidate by key and never import each other. */
export const auditKeys = {
  all,
  list: () => [...all, 'list'] as const,
  summary: () => [...all, 'summary'] as const,
  detail: (id: string) => [...all, 'detail', id] as const,
  result: (id: string) => [...all, 'result', id] as const,
}