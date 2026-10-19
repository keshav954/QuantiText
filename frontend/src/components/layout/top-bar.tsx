/**
 * Top bar — global date range picker, dark/light toggle, and mobile menu.
 */

import { useTheme } from '@/store/theme-context'
import { useDateRange } from '@/store/date-range-context'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import {
  Sun,
  Moon,
  Calendar,
  ChevronDown,
  Menu,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'

const presets = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 365 days', days: 365 },
]

export function TopBar() {
  const { theme, toggleTheme } = useTheme()
  const { range, setRange, presetLabel, setPresetLabel } = useDateRange()
  const [showPresets, setShowPresets] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handlePreset = (label: string, days: number) => {
    const to = new Date()
    const from = new Date()
    from.setDate(from.getDate() - days)
    setRange({ from, to })
    setPresetLabel(label)
    setShowPresets(false)
  }

  return (
    <>
      <header className="flex h-16 items-center justify-between border-b border-border/50 bg-card/30 backdrop-blur-md px-4 md:px-6">
        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-accent focus-ring"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Mobile logo */}
        <div className="flex md:hidden items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-purple-600">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-bold text-gradient">QuantiText</span>
        </div>

        {/* Page title area (hidden on mobile) */}
        <div className="hidden md:block" />

        {/* Right controls */}
        <div className="flex items-center gap-2">
          {/* Date range picker */}
          <div className="relative">
            <button
              id="date-range-picker"
              onClick={() => setShowPresets(!showPresets)}
              className={cn(
                'flex items-center gap-2 rounded-lg border border-border/50 bg-card/50 px-3 py-2 text-sm transition-all hover:bg-accent focus-ring',
                showPresets && 'ring-2 ring-primary/30',
              )}
              aria-expanded={showPresets}
              aria-haspopup="listbox"
            >
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="hidden sm:inline text-foreground">{presetLabel}</span>
              <span className="hidden lg:inline text-muted-foreground text-xs">
                {format(range.from, 'MMM d')} – {format(range.to, 'MMM d, yyyy')}
              </span>
              <ChevronDown className={cn('h-3 w-3 text-muted-foreground transition-transform', showPresets && 'rotate-180')} />
            </button>

            {showPresets && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowPresets(false)} />
                <div className="absolute right-0 top-full z-50 mt-2 w-56 rounded-xl border border-border/50 bg-popover p-2 shadow-xl shadow-black/10 animate-fade-in">
                  {presets.map(({ label, days }) => (
                    <button
                      key={label}
                      onClick={() => handlePreset(label, days)}
                      className={cn(
                        'flex w-full items-center rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent focus-ring',
                        presetLabel === label ? 'bg-primary/10 text-primary font-medium' : 'text-foreground',
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Theme toggle */}
          <button
            id="theme-toggle"
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border/50 bg-card/50 transition-all hover:bg-accent focus-ring"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4 text-amber-400 transition-transform hover:rotate-45" />
            ) : (
              <Moon className="h-4 w-4 text-indigo-500 transition-transform hover:-rotate-12" />
            )}
          </button>
        </div>
      </header>

      {/* Mobile navigation drawer */}
      {mobileMenuOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/60 md:hidden" onClick={() => setMobileMenuOpen(false)} />
          <div className="fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border md:hidden animate-slide-in-left">
            <div className="flex h-16 items-center gap-3 px-4 border-b border-border/50">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-gradient">QuantiText</h1>
                <p className="text-[10px] text-muted-foreground">Copilot</p>
              </div>
            </div>
            <nav className="p-3 space-y-1">
              {[
                { to: '/dashboard', label: 'Dashboard' },
                { to: '/copilot', label: 'AI Copilot' },
                { to: '/forecasts', label: 'Forecasts' },
                { to: '/inventory', label: 'Inventory' },
                { to: '/alerts', label: 'Alerts' },
                { to: '/reports', label: 'Reports' },
                { to: '/admin', label: 'Admin' },
              ].map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                      isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent',
                    )
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
        </>
      )}
    </>
  )
}
