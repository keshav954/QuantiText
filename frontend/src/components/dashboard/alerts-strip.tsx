/**
 * Alerts Strip — compact horizontal strip showing recent alerts.
 * 
 * Phase 6 will wire this to the anomaly detection backend.
 * For now, shows placeholder alerts with proper styling.
 */

import { cn } from '@/lib/utils'
import { AlertTriangle, Info, AlertCircle, X } from 'lucide-react'
import { useState } from 'react'

interface Alert {
  id: string
  title: string
  severity: 'critical' | 'warning' | 'info'
  time: string
}

// Placeholder alerts for Phase 3 — will be replaced by real API data in Phase 6
const PLACEHOLDER_ALERTS: Alert[] = [
  {
    id: '1',
    title: 'Revenue spike detected — Electronics category +42% above forecast',
    severity: 'warning',
    time: '2h ago',
  },
  {
    id: '2',
    title: 'Low stock alert — 3 products below reorder point',
    severity: 'critical',
    time: '4h ago',
  },
  {
    id: '3',
    title: 'Weekly forecast updated — model retrained with latest data',
    severity: 'info',
    time: '1d ago',
  },
]

const severityConfig = {
  critical: {
    icon: AlertCircle,
    bg: 'bg-critical/10',
    border: 'border-critical/30',
    text: 'text-critical',
    dot: 'bg-critical',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-warning/10',
    border: 'border-warning/30',
    text: 'text-warning',
    dot: 'bg-warning',
  },
  info: {
    icon: Info,
    bg: 'bg-forecast/10',
    border: 'border-forecast/30',
    text: 'text-forecast',
    dot: 'bg-forecast',
  },
}

export function AlertsStrip() {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const visibleAlerts = PLACEHOLDER_ALERTS.filter((a) => !dismissed.has(a.id))

  if (visibleAlerts.length === 0) return null

  return (
    <div id="alerts-strip" className="space-y-2 animate-fade-in">
      <h3 className="text-sm font-semibold text-foreground">Recent Alerts</h3>
      <div className="space-y-2">
        {visibleAlerts.map((alert) => {
          const config = severityConfig[alert.severity]
          const Icon = config.icon

          return (
            <div
              key={alert.id}
              className={cn(
                'flex items-center gap-3 rounded-lg border px-4 py-3 transition-all',
                config.bg,
                config.border,
              )}
              role="alert"
            >
              <div className={cn('h-2 w-2 rounded-full shrink-0 animate-pulse-glow', config.dot)} />
              <Icon className={cn('h-4 w-4 shrink-0', config.text)} />
              <p className="flex-1 text-sm text-foreground">{alert.title}</p>
              <span className="text-xs text-muted-foreground shrink-0">{alert.time}</span>
              <button
                onClick={() => setDismissed((prev) => new Set([...prev, alert.id]))}
                className="p-1 rounded hover:bg-accent/50 transition-colors focus-ring shrink-0"
                aria-label={`Dismiss alert: ${alert.title}`}
              >
                <X className="h-3 w-3 text-muted-foreground" />
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
