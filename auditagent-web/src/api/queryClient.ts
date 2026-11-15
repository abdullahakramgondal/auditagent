import { QueryClient } from '@tanstack/react-query'
import { shouldRetry } from './retry'

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, refetchOnWindowFocus: false },
    },
  })
}