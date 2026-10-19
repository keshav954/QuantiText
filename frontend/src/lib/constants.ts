/**
 * Application-wide constants.
 * Centralizes magic numbers, labels, and configuration that were previously
 * scattered across page files.
 */

// ── Severity / alert config ──────────────────────────────────────────────────

import { AlertCircle, AlertTriangle, Info } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface SeverityConfig {
  icon: LucideIcon
  class: string
  dot: string
  label: string
}

export const SEVERITY_CONFIG: Record<string, SeverityConfig> = {
  critical: {
    icon: AlertCircle,
    class: 'text-red-400 bg-red-400/10 border-red-400/20',
    dot: 'bg-red-400',
    label: 'Critical',
  },
  warning: {
    icon: AlertTriangle,
    class: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    dot: 'bg-amber-400',
    label: 'Warning',
  },
  info: {
    icon: Info,
    class: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    dot: 'bg-blue-400',
    label: 'Info',
  },
} as const

// ── Inventory ────────────────────────────────────────────────────────────────

export const ABC_COLORS: Record<string, string> = {
  A: 'text-emerald-400 bg-emerald-400/10',
  B: 'text-amber-400 bg-amber-400/10',
  C: 'text-slate-400 bg-slate-400/10',
} as const

export const STOCK_STATUS_STYLES: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10 border border-red-400/20',
  low: 'text-amber-400 bg-amber-400/10 border border-amber-400/20',
  ok: 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20',
  overstock: 'text-blue-400 bg-blue-400/10 border border-blue-400/20',
} as const

export const STOCK_FILTER_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'low', label: 'Low' },
  { value: 'ok', label: 'OK' },
  { value: 'overstock', label: 'Overstock' },
] as const

// ── Anomaly / detector labels ────────────────────────────────────────────────

export const DETECTOR_LABELS: Record<string, string> = {
  zscore: 'Z-Score',
  iforest: 'Isolation Forest',
  data_quality: 'Data Quality',
} as const

export const ANOMALY_TYPE_LABELS: Record<string, string> = {
  revenue_spike: 'Revenue Spike',
  revenue_drop: 'Revenue Drop',
  zero_sales: 'Zero Sales Streak',
  inventory_critical: 'Critical Stock',
} as const

// ── Forecasting ──────────────────────────────────────────────────────────────

export const HORIZON_OPTIONS = [7, 14, 30, 60, 90] as const

export const SHAP_COLORS = [
  '#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe',
] as const

// ── Pagination ───────────────────────────────────────────────────────────────

export const DEFAULT_PAGE_SIZE = 25
export const MAX_PAGE_SIZE = 200

// ── Date format ──────────────────────────────────────────────────────────────

export const SHORT_DATE_FORMAT = 'dd MMM yyyy'
export const CHART_DATE_FORMAT: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
}
