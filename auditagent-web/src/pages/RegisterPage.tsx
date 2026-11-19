import { AuthForm } from '@/features/auth'

export function RegisterPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Create an account</h1>
        <p className="mt-1 text-sm text-slate-600 md:text-base">
          Your audits are saved under your account, and only you can open them.
        </p>
      </div>
      <AuthForm mode="register" />
    </div>
  )
}