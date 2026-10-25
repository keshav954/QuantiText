/**
 * Revenue Trend Chart — area chart with gradient fill using Recharts.
 * Shows daily revenue and order count over the selected date range.
 */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { useRevenueTrend } from '@/api/kpi'
import { formatCurrency, formatCompact } from '@/lib/utils'

export function RevenueTrendChart() {
  const { data, isLoading, isError, error } = useRevenueTrend()

  if (isLoading) return <ChartSkeleton />

  if (isError) {
    return (
      <div className="glass rounded-xl p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Revenue Trend</h3>
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <p className="text-sm text-critical">Failed to load chart</p>
            <p className="text-xs text-muted-foreground mt-1">{(error as Error)?.message}</p>
          </div>
        </div>
      </div>
    )
  }

  const chartData = data?.data ?? []

  if (chartData.length === 0) {
    return (
      <div className="glass rounded-xl p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Revenue Trend</h3>
        <div className="flex h-64 items-center justify-center">
          <p className="text-sm text-muted-foreground">No data for selected period</p>
        </div>
      </div>
    )
  }

  return (
    <div id="revenue-trend-chart" className="glass rounded-xl p-6 animate-fade-in">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Revenue Trend</h3>
        <p className="text-xs text-muted-foreground">{data?.period}</p>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
          <defs>
            <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(243, 75%, 59%)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="hsl(243, 75%, 59%)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="ordersGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(152, 69%, 41%)" stopOpacity={0.2} />
              <stop offset="95%" stopColor="hsl(152, 69%, 41%)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.6} />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => {
              const date = new Date(d)
              if (chartData.length > 365) {
                return date.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
              }
              return `${date.getMonth() + 1}/${date.getDate()}`
            }}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            yAxisId="revenue"
            tickFormatter={(v: number) => formatCompact(v)}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            yAxisId="orders"
            orientation="right"
            tickFormatter={(v: number) => String(v)}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            hide
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '0.75rem',
              fontSize: '12px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
            }}
            itemStyle={{ color: 'hsl(var(--foreground))' }}
            labelStyle={{ color: 'hsl(var(--muted-foreground))', marginBottom: '4px' }}
            formatter={(value: number, name: string) =>
              name === 'revenue' ? formatCurrency(value) : value
            }
            labelFormatter={(label: string) => {
              const d = new Date(label)
              return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
            }}
          />
          <Area
            yAxisId="revenue"
            type="monotone"
            dataKey="revenue"
            stroke="hsl(243, 75%, 59%)"
            strokeWidth={2}
            fill="url(#revenueGradient)"
            name="revenue"
          />
          <Area
            yAxisId="orders"
            type="monotone"
            dataKey="order_count"
            stroke="hsl(152, 69%, 41%)"
            strokeWidth={1.5}
            fill="url(#ordersGradient)"
            name="orders"
            strokeDasharray="4 2"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-4 rounded-sm bg-primary" />
          Revenue
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-4 rounded-sm bg-healthy" />
          Orders
        </div>
      </div>
    </div>
  )
}

function ChartSkeleton() {
  return (
    <div className="glass rounded-xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="skeleton h-4 w-28" />
        <div className="skeleton h-3 w-36" />
      </div>
      <div className="skeleton h-[280px] rounded-lg" />
    </div>
  )
}
