import { AuthForm } from '@/features/auth'

export function LoginPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Log in</h1>
        <p className="mt-1 text-sm text-slate-600 md:text-base">
          Log in to see your own audits. Nobody else can see them.
        </p>
      </div>
      <AuthForm mode="login" />
    </div>
  )
}