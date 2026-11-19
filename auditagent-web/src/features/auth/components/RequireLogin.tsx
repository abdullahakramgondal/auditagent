import { Navigate, Outlet } from 'react-router'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useMe } from '../hooks/useMe'

/** A route wrapper: the pages inside it are for logged-in people only. */
export function RequireLogin() {
  const me = useMe()
  if (me.isPending) return <p role="status">Loading…</p>
  if (me.isError) {
    return <ErrorNotice message={me.error.message} onRetry={() => void me.refetch()} />
  }
  if (me.data === null) return <Navigate to="/login" replace />
  return <Outlet />
}