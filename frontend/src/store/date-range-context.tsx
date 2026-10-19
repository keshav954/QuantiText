/**
 * Date range store — global filter state shared across dashboard components.
 */

import { createContext, useContext, useState, type ReactNode } from 'react'

export interface DateRange {
  from: Date
  to: Date
}

interface DateRangeContextValue {
  range: DateRange
  setRange: (range: DateRange) => void
  presetLabel: string
  setPresetLabel: (label: string) => void
}

// Default: last 30 days
function defaultRange(): DateRange {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - 30)
  return { from, to }
}

const DateRangeContext = createContext<DateRangeContextValue | undefined>(undefined)

export function DateRangeProvider({ children }: { children: ReactNode }) {
  const [range, setRange] = useState<DateRange>(defaultRange)
  const [presetLabel, setPresetLabel] = useState('Last 30 days')

  return (
    <DateRangeContext.Provider value={{ range, setRange, presetLabel, setPresetLabel }}>
      {children}
    </DateRangeContext.Provider>
  )
}

export function useDateRange(): DateRangeContextValue {
  const ctx = useContext(DateRangeContext)
  if (!ctx) throw new Error('useDateRange must be used within DateRangeProvider')
  return ctx
}
