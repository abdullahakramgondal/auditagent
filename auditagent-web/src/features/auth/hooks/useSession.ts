import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { login, logout, register } from '@/api/auth'
import { authKeys } from '@/api/queryKeys'
import type { User } from '@/api/types'

type Credentials = { email: string; password: string }

/** Everything cached except the login itself belongs to the person who just left: throw it away. */
function forgetPrivateData(queryClient: QueryClient) {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== authKeys.me[0] })
}

function useStartSession(call: (input: Credentials) => Promise<User>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: call,
    onSuccess: (user) => {
      forgetPrivateData(queryClient)
      queryClient.setQueryData(authKeys.me, user)
    },
  })
}

export function useLogin() {
  return useStartSession(({ email, password }) => login(email, password))
}

export function useRegister() {
  return useStartSession(({ email, password }) => register(email, password))
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => logout(),
    onSuccess: () => {
      forgetPrivateData(queryClient)
      queryClient.setQueryData(authKeys.me, null)
    },
  })
}