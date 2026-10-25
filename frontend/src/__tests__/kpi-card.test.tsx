/**
 * Unit tests for KPICard component interactive behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { KPICard } from '@/components/dashboard/kpi-card'
import { DollarSign } from 'lucide-react'

// @ts-expect-error React act testing flag
globalThis.IS_REACT_ACT_ENVIRONMENT = true

describe('KPICard', () => {
  let container: HTMLDivElement

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
  })

  it('renders metric title and value', () => {
    const root = createRoot(container)
    act(() => {
      root.render(
        <KPICard
          id="kpi-revenue"
          title="Total Revenue"
          value="$2,035,112"
          trend={11.8}
          icon={DollarSign}
        />,
      )
    })

    expect(container.textContent).toContain('Total Revenue')
    expect(container.textContent).toContain('$2,035,112')
    expect(container.textContent).toContain('+11.8%')

    const card = container.querySelector('#kpi-revenue')
    expect(card?.getAttribute('role')).toBe('article')
    expect(card?.getAttribute('tabindex')).toBeNull()
  })

  it('renders interactive button when onClick is provided', () => {
    const handleClick = vi.fn()
    const root = createRoot(container)
    act(() => {
      root.render(
        <KPICard
          id="kpi-revenue-clickable"
          title="Total Revenue"
          value="$2,035,112"
          trend={11.8}
          icon={DollarSign}
          onClick={handleClick}
        />,
      )
    })

    const card = container.querySelector('#kpi-revenue-clickable') as HTMLElement
    expect(card).not.toBeNull()
    expect(card.getAttribute('role')).toBe('button')
    expect(card.getAttribute('tabindex')).toBe('0')
    expect(container.textContent).toContain('Details')

    // Click trigger
    act(() => {
      card.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    expect(handleClick).toHaveBeenCalledTimes(1)

    // Keyboard trigger (Enter key)
    act(() => {
      card.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    })
    expect(handleClick).toHaveBeenCalledTimes(2)
  })
})
