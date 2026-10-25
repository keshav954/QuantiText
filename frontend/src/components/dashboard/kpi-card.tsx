/**
 * KPI Card — displays a single metric with trend indicator.
 *
 * Supports loading (skeleton) and error states.
 * Color-coded trend: green for positive, red for negative.
 */

import { cn, formatTrend } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus, ArrowUpRight, type LucideIcon } from 'lucide-react'

interface KPICardProps {
  id: string
  title: string
  value: string
  trend: number | null
  icon: LucideIcon
  iconColor?: string
  loading?: boolean
  onClick?: () => void
}

export function KPICard({
  id,
  title,
  value,
  trend,
  icon: Icon,
  iconColor = 'text-primary',
  loading,
  onClick,
}: KPICardProps) {
  if (loading) {
    return <KPICardSkeleton />
  }

  const trendPositive = trend !== null && trend > 0
  const trendNegative = trend !== null && trend < 0
  const trendNeutral = trend === null || trend === 0

  return (
    <div
      id={id}
      onClick={onClick}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onClick()
        }
      }}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : 'article'}
      className={cn(
        'glass rounded-xl p-5 kpi-glow animate-fade-in relative transition-all duration-200 select-none',
        onClick &&
          'cursor-pointer group hover:-translate-y-1 hover:border-primary/50 hover:shadow-xl hover:shadow-primary/5 active:scale-[0.99] focus-ring',
      )}
      aria-label={`${title}: ${value}${onClick ? '. Press to view detailed analytics.' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground group-hover:text-primary transition-colors">
            {title}
          </p>
          <p className="text-2xl font-bold tracking-tight text-foreground">
            {value}
          </p>
        </div>
        <div
          className={cn(
            'flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 transition-transform duration-200 group-hover:scale-110',
            iconColor,
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>

      {/* Trend indicator & Details trigger */}
      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
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

        {onClick && (
          <span className="inline-flex items-center gap-0.5 text-xs font-medium text-primary/80 group-hover:text-primary transition-colors">
            Details
            <ArrowUpRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </span>
        )}
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
