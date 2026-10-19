/**
 * useAutoScroll — scrolls a target element into view whenever a dependency changes.
 *
 * Extracted from the Copilot chat page to make the pattern reusable.
 */

import { useRef, useEffect } from 'react'

/**
 * Returns a ref that should be attached to a sentinel element at the bottom
 * of a scrollable container. Whenever `deps` change, the sentinel is scrolled
 * into view with smooth behaviour.
 */
export function useAutoScroll<T extends HTMLElement = HTMLDivElement>(
  deps: unknown[],
  behavior: ScrollBehavior = 'smooth',
) {
  const ref = useRef<T>(null)

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}
