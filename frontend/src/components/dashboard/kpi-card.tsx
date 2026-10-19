/**
 * KPI Card — displays a single metric with trend indicator.
 *
 * Supports loading (skeleton) and error states.
 * Color-coded trend: green for positive, red for negative.
 */

import { cn, formatTrend } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from 'lucide-react'

interface KPICardProps {
  id: string
  title: string
  value: string
  trend: number | null
  icon: LucideIcon
  iconColor?: string
  loading?: boolean
}

export function KPICard({ id, title, value, trend, icon: Icon, iconColor = 'text-primary', loading }: KPICardProps) {
  if (loading) {
    return <KPICardSkeleton />
  }

  const trendPositive = trend !== null && trend > 0
  const trendNegative = trend !== null && trend < 0
  const trendNeutral = trend === null || trend === 0

  return (
    <div
      id={id}
      className="glass rounded-xl p-5 kpi-glow animate-fade-in"
      role="article"
      aria-label={`${title}: ${value}`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {title}
          </p>
          <p className="text-2xl font-bold tracking-tight text-foreground">
            {value}
          </p>
        </div>
        <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10', iconColor)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>

      {/* Trend indicator */}
      <div className="mt-3 flex items-center gap-1.5">
        {trendPositive && <TrendingUp className="h-4 w-4 text-healthy" />}
        {trendNegative && <TrendingDown className="h-4 w-4 text-critical" />}
        {trendNeutral && <Minus className="h-4 w-4 text-muted-foreground" />}
        <span
          className={cn(
            'text-sm font-medium',
            trendPositive && 'text-healthy',
            trendNegative && 'text-critical',
            trendNeutral && 'text-muted-foreground',
          )}
        >
          {formatTrend(trend)}
        </span>
        <span className="text-xs text-muted-foreground">vs prev period</span>
      </div>
    </div>
  )
}

function KPICardSkeleton() {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <div className="skeleton h-3 w-20" />
          <div className="skeleton h-7 w-28" />
        </div>
        <div className="skeleton h-10 w-10 rounded-lg" />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <div className="skeleton h-4 w-16" />
        <div className="skeleton h-3 w-20" />
      </div>
    </div>
  )
}
