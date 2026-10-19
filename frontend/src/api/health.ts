/**
 * Health API — checks backend /health endpoint.
 */

import { useQuery } from '@tanstack/react-query'

interface HealthResponse {
  status: string
  db: string
  redis: string
  version: string
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch('/health')
      if (!res.ok) throw new Error('Backend unreachable')
      return res.json() as Promise<HealthResponse>
    },
    staleTime: 30_000,
    retry: 1,
  })
}
