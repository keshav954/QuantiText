/**
 * useMediaQuery — reactive CSS media query hook.
 * Returns true when the viewport matches the given query string.
 */

import { useState, useEffect } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false,
  )

  useEffect(() => {
    const mql = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)

    setMatches(mql.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])

  return matches
}

/** Convenience: true when viewport ≥ 768px (Tailwind md). */
export function useIsMobile(): boolean {
  return !useMediaQuery('(min-width: 768px)')
}
