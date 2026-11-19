import { useLogout } from '../hooks/useSession'

export function LogoutButton() {
  const logout = useLogout()
  return (
    <button
      type="button"
      onClick={() => logout.mutate()}
      disabled={logout.isPending}
      className="inline-flex min-h-11 items-center rounded-md border border-slate-300 bg-white px-3 text-sm font-medium hover:bg-slate-100 disabled:opacity-60"
    >
      Log out
    </button>
  )
}