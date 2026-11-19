import { useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router'
import { ErrorNotice } from '@/shared/ui/ErrorNotice'
import { useLogin, useRegister } from '../hooks/useSession'
import { useMe } from '../hooks/useMe'

type Props = { mode: 'login' | 'register' }

const INPUT =
  'min-h-11 rounded-md border border-slate-300 bg-white px-3 py-2 text-base focus:border-blue-600'

/** One form for both pages. When somebody is already logged in it leads them to the dashboard. */
export function AuthForm({ mode }: Props) {
  const me = useMe()
  const login = useLogin()
  const register = useRegister()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const action = mode === 'login' ? login : register

  if (me.data) return <Navigate to="/" replace />

  function submit(event: FormEvent) {
    event.preventDefault()
    action.mutate({ email, password })
  }

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="auth-email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="auth-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className={INPUT}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="auth-password" className="text-sm font-medium">
          Password
        </label>
        <input
          id="auth-password"
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          required
          minLength={mode === 'register' ? 8 : undefined}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className={INPUT}
        />
        {mode === 'register' && (
          <p className="text-sm text-slate-600">Use at least 8 characters.</p>
        )}
      </div>

      {action.isError && <ErrorNotice message={action.error.message} />}

      <button
        type="submit"
        disabled={action.isPending}
        className="min-h-11 rounded-md bg-slate-900 px-5 py-3 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {action.isPending ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
      </button>

      <p className="text-sm text-slate-600">
        {mode === 'login' ? (
          <>
            No account yet?{' '}
            <Link to="/register" className="text-blue-700 underline">
              Create one
            </Link>
          </>
        ) : (
          <>
            Already have an account?{' '}
            <Link to="/login" className="text-blue-700 underline">
              Log in
            </Link>
          </>
        )}
      </p>
    </form>
  )
}