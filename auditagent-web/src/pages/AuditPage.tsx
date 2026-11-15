import { useParams } from 'react-router'
import { AuditView } from '@/features/audit'
import { NotFoundPage } from './NotFoundPage'

export function AuditPage() {
  const { id } = useParams()
  return id ? <AuditView id={id} /> : <NotFoundPage />
}