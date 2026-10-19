/**
 * StatusBadge — colored pill badge for status/severity indicators.
 * Replaces inline badge styling scattered across alerts, inventory, and reports pages.
 */

import { cn } from '@/lib/utils'

const VARIANT_STYLES: Record<string, string> = {
  // Severity / alert levels
  critical: 'text-red-400 bg-red-400/10 border-red-400/20',
  warning: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  info: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  // Inventory status
  low: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  ok: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  overstock: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  // Approval / report
  approved: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  rejected: 'text-red-400 bg-red-400/10 border-red-400/20',
  pending: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  // Generic
  success: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  error: 'text-red-400 bg-red-400/10 border-red-400/20',
  default: 'text-slate-400 bg-slate-400/10 border-slate-400/20',
}

interface StatusBadgeProps {
  variant: string
  label?: string
  className?: string
  children?: React.ReactNode
}

export function StatusBadge({ variant, label, className, children }: StatusBadgeProps) {
  const styles = VARIANT_STYLES[variant] ?? VARIANT_STYLES.default

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize',
        styles,
        className,
      )}
    >
      {children ?? label ?? variant}
    </span>
  )
}
