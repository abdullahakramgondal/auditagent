import { useQuery } from '@tanstack/react-query'
import { getMe } from '@/api/auth'
import { authKeys } from '@/api/queryKeys'

const FIVE_MINUTES = 5 * 60 * 1000

/** Who is logged in: the person, or null. One answer is shared by the whole app. */
export function useMe() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: getMe,
    staleTime: FIVE_MINUTES,
  })
}