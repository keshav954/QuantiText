/**
 * useDismissible — generic hook for dismissing items by ID.
 *
 * Extracted from the AlertsStrip component. Useful for any list where items
 * can be dismissed / hidden client-side.
 */

import { useState, useCallback, useMemo } from 'react'

/**
 * Tracks a set of dismissed item IDs and returns a filtered list.
 *
 * @param items The full list of items.
 * @param keyFn Extracts a unique string key from each item (defaults to `item.id`).
 */
export function useDismissible<T extends { id: string }>(
  items: T[],
  keyFn: (item: T) => string = (item) => item.id,
) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const dismiss = useCallback((key: string) => {
    setDismissed((prev) => new Set([...prev, key]))
  }, [])

  const reset = useCallback(() => {
    setDismissed(new Set())
  }, [])

  const visible = useMemo(
    () => items.filter((item) => !dismissed.has(keyFn(item))),
    [items, dismissed, keyFn],
  )

  return { visible, dismiss, reset, dismissedCount: dismissed.size }
}
