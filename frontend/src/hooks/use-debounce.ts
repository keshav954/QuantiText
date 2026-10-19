/**
 * useDebounce — delays updating a value until input stops changing.
 * Useful for search inputs, filters, and API call throttling.
 */

import { useState, useEffect } from 'react'

export function useDebounce<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}
