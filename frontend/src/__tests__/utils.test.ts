/**
 * Tests for utility functions.
 */

import { describe, it, expect } from 'vitest'
import { formatCurrency, formatCompact, formatTrend, cn } from '@/lib/utils'

describe('formatCurrency', () => {
  it('formats a whole number as USD currency', () => {
    expect(formatCurrency(1234)).toBe('$1,234')
    expect(formatCurrency(1000000)).toBe('$1,000,000')
    expect(formatCurrency(0)).toBe('$0')
  })
})

describe('formatCompact', () => {
  it('formats large numbers compactly', () => {
    expect(formatCompact(1200)).toBe('1.2K')
    expect(formatCompact(1500000)).toBe('1.5M')
    expect(formatCompact(42)).toBe('42')
  })
})

describe('formatTrend', () => {
  it('formats positive trends with a + sign', () => {
    expect(formatTrend(12.5)).toBe('+12.5%')
  })

  it('formats negative trends without extra sign', () => {
    expect(formatTrend(-5.3)).toBe('-5.3%')
  })

  it('returns — for null', () => {
    expect(formatTrend(null)).toBe('—')
  })
})

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('a', 'b')).toBe('a b')
  })

  it('handles conditional classes', () => {
    const isHidden = false
    expect(cn('base', isHidden && 'hidden', 'active')).toBe('base active')
  })

  it('deduplicates Tailwind classes correctly', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4')
  })
})
