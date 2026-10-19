/**
 * Dashboard page — main BI dashboard with KPI cards, charts, and tables.
 *
 * Layout:
 * - 4 KPI cards (responsive grid)
 * - Revenue trend chart (full width)
 * - Top products table + alerts strip (two-column)
 */

import { useKPISummary } from '@/api/kpi'
import { formatCurrency, formatCompact } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/kpi-card'
import { RevenueTrendChart } from '@/components/dashboard/revenue-trend-chart'
import { TopProductsTable } from '@/components/dashboard/top-products-table'
import { AlertsStrip } from '@/components/dashboard/alerts-strip'
import { DollarSign, ShoppingCart, Receipt, Users } from 'lucide-react'

export function Dashboard() {
  const { data: kpi, isLoading, isError, error } = useKPISummary()

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Dashboard
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Real-time business intelligence overview
        </p>
      </div>

      {/* Error banner */}
      {isError && (
        <div className="rounded-lg border border-critical/30 bg-critical/10 px-4 py-3" role="alert">
          <p className="text-sm text-critical">
            Failed to load KPIs: {(error as Error)?.message ?? 'Unknown error'}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Check that the backend is running at /api/v1 and you are authenticated.
          </p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          id="kpi-revenue"
          title="Total Revenue"
          value={isLoading ? '—' : formatCurrency(kpi?.total_revenue ?? 0)}
          trend={kpi?.revenue_trend ?? null}
          icon={DollarSign}
          iconColor="text-emerald-500"
          loading={isLoading}
        />
        <KPICard
          id="kpi-orders"
          title="Total Orders"
          value={isLoading ? '—' : formatCompact(kpi?.total_orders ?? 0)}
          trend={kpi?.orders_trend ?? null}
          icon={ShoppingCart}
          iconColor="text-blue-500"
          loading={isLoading}
        />
        <KPICard
          id="kpi-aov"
          title="Avg Order Value"
          value={isLoading ? '—' : formatCurrency(kpi?.avg_order_value ?? 0)}
          trend={null}
          icon={Receipt}
          iconColor="text-purple-500"
          loading={isLoading}
        />
        <KPICard
          id="kpi-customers"
          title="Unique Customers"
          value={isLoading ? '—' : formatCompact(kpi?.unique_customers ?? 0)}
          trend={null}
          icon={Users}
          iconColor="text-amber-500"
          loading={isLoading}
        />
      </div>

      {/* Revenue Trend Chart */}
      <RevenueTrendChart />

      {/* Bottom section: Products table + Alerts */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <TopProductsTable />
        </div>
        <div className="xl:col-span-1">
          <AlertsStrip />
        </div>
      </div>
    </div>
  )
}
