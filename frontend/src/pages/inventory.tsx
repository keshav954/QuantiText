/**
 * Inventory page — stock table, status badges, EOQ, ABC class, reorder suggestions.
 * Phase 5.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Package,
  AlertTriangle,
  TrendingDown,
  BarChart2,
  ShoppingCart,
  ChevronUp,
  ChevronDown,
  Sliders,
  Sparkles,
  ArrowRight,
} from 'lucide-react'
import {
  fetchInventorySummary,
  fetchInventoryList,
  fetchReorderSuggestions,
  simulateWhatIf,
  type InventoryItem,
  type WhatIfResponse,
} from '@/api/inventory'

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'low', label: 'Low' },
  { value: 'ok', label: 'OK' },
  { value: 'overstock', label: 'Overstock' },
]

const ABC_COLORS: Record<string, string> = {
  A: 'text-emerald-400 bg-emerald-400/10',
  B: 'text-amber-400 bg-amber-400/10',
  C: 'text-slate-400 bg-slate-400/10',
}

const STATUS_STYLES: Record<string, string> = {
  critical: 'text-red-400 bg-red-400/10 border border-red-400/20',
  low: 'text-amber-400 bg-amber-400/10 border border-amber-400/20',
  ok: 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/20',
  overstock: 'text-blue-400 bg-blue-400/10 border border-blue-400/20',
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'text-foreground',
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  sub?: string
  color?: string
}) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex items-center gap-4">
      <div className="p-3 bg-muted rounded-xl">
        <Icon className={`h-5 w-5 ${color}`} />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export function InventoryPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [showReorder, setShowReorder] = useState(false)
  const [showWhatIf, setShowWhatIf] = useState(false)
  const [demandPct, setDemandPct] = useState(20)
  const [delayDays, setDelayDays] = useState(7)
  const [whatIfData, setWhatIfData] = useState<WhatIfResponse | null>(null)
  const [isSimulating, setIsSimulating] = useState(false)

  const handleRunSimulation = async () => {
    setIsSimulating(true)
    try {
      const res = await simulateWhatIf({
        demand_change_pct: demandPct,
        lead_time_delay_days: delayDays,
      })
      setWhatIfData(res)
    } catch {
      // Fallback silently if offline or request fails
    } finally {
      setIsSimulating(false)
    }
  }

  const summaryQuery = useQuery({
    queryKey: ['inventory-summary'],
    queryFn: fetchInventorySummary,
  })

  const listQuery = useQuery({
    queryKey: ['inventory-list', statusFilter],
    queryFn: () => fetchInventoryList({ status: statusFilter || undefined, limit: 100 }),
  })

  const reorderQuery = useQuery({
    queryKey: ['reorder-suggestions'],
    queryFn: () => fetchReorderSuggestions(20),
    enabled: showReorder,
  })

  const summary = summaryQuery.data
  const items = listQuery.data?.items ?? []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <Package className="h-6 w-6 text-primary" />
            Inventory Analysis
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Safety stock · EOQ · ABC classification ·{' '}
            <span className="text-amber-400">⚠️ Data is SYNTHETIC</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            id="what-if-btn"
            onClick={() => {
              const next = !showWhatIf
              setShowWhatIf(next)
              if (next && !whatIfData) {
                handleRunSimulation()
              }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground border border-border rounded-xl text-sm font-medium hover:bg-secondary/80 transition-colors"
          >
            <Sliders className="h-4 w-4 text-primary" />
            What-If Scenario
            {showWhatIf ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          <button
            id="reorder-suggestions-btn"
            onClick={() => setShowReorder((v) => !v)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <ShoppingCart className="h-4 w-4" />
            Reorder Suggestions
            {showReorder ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>
      </div>


      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          icon={Package}
          label="Total Products"
          value={summary?.total_products ?? '–'}
        />
        <SummaryCard
          icon={AlertTriangle}
          label="Critical Stock"
          value={summary?.critical_count ?? '–'}
          color="text-red-400"
        />
        <SummaryCard
          icon={TrendingDown}
          label="Low Stock"
          value={summary?.low_stock_count ?? '–'}
          color="text-amber-400"
        />
        <SummaryCard
          icon={BarChart2}
          label="Inventory Value"
          value={
            summary?.total_inventory_value !== undefined
              ? `£${(summary.total_inventory_value / 1000).toFixed(0)}k`
              : '–'
          }
          sub="at unit cost"
          color="text-indigo-400"
        />
      </div>

      {/* Reorder suggestions panel */}
      {showReorder && (
        <div className="bg-card border border-amber-400/20 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <ShoppingCart className="h-4 w-4 text-amber-400" />
            Reorder Suggestions
          </h2>
          {reorderQuery.isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-12 bg-muted animate-pulse rounded-lg" />
              ))}
            </div>
          ) : (reorderQuery.data?.length ?? 0) === 0 ? (
            <p className="text-muted-foreground text-sm">No products require immediate reordering.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    {['SKU', 'Product', 'Stock', 'Reorder Point', 'EOQ', 'Suggested Qty', 'Est. Cost', 'Urgency'].map(
                      (h) => (
                        <th key={h} className="text-left text-xs text-muted-foreground py-2 pr-4 font-medium">
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {reorderQuery.data?.map((s) => (
                    <tr key={s.product_id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 pr-4 font-mono text-xs text-muted-foreground">{s.sku}</td>
                      <td className="py-2.5 pr-4 text-foreground font-medium">{s.product_name}</td>
                      <td className="py-2.5 pr-4 text-red-400 font-bold">{s.current_stock}</td>
                      <td className="py-2.5 pr-4 text-muted-foreground">{s.reorder_point}</td>
                      <td className="py-2.5 pr-4 text-muted-foreground">{s.eoq}</td>
                      <td className="py-2.5 pr-4 text-indigo-400 font-bold">{s.suggested_qty}</td>
                      <td className="py-2.5 pr-4 text-foreground">£{s.estimated_cost.toFixed(0)}</td>
                      <td className="py-2.5 pr-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            s.urgency === 'immediate'
                              ? 'text-red-400 bg-red-400/10'
                              : 'text-amber-400 bg-amber-400/10'
                          }`}
                        >
                          {s.urgency}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* What-If Scenario Simulator Panel */}
      {showWhatIf && (
        <div className="bg-card border border-primary/20 rounded-2xl p-5 space-y-4 shadow-lg shadow-primary/5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
            <div>
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Sliders className="h-4 w-4 text-primary" />
                Inventory What-If Simulator
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Stress-test inventory buffers under simulated demand surges and supply chain lead time delays.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20 font-mono">
                SYNTHETIC SIMULATION
              </span>
              <button
                id="run-simulation-btn"
                onClick={handleRunSimulation}
                disabled={isSimulating}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {isSimulating ? 'Simulating...' : 'Run Shock Simulation'}
              </button>
            </div>
          </div>

          {/* Interactive Sliders */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 p-4 bg-muted/40 rounded-xl border border-border/50">
            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="font-medium text-foreground">Demand Shock (% change):</span>
                <span className={`font-mono font-bold ${demandPct >= 0 ? 'text-primary' : 'text-blue-400'}`}>
                  {demandPct >= 0 ? `+${demandPct}%` : `${demandPct}%`}
                </span>
              </div>
              <input
                type="range"
                min="-50"
                max="100"
                step="5"
                value={demandPct}
                onChange={(e) => setDemandPct(Number(e.target.value))}
                className="w-full accent-primary cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                <span>-50% (drop)</span>
                <span>0% (baseline)</span>
                <span>+50% (surge)</span>
                <span>+100% (doubled)</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="font-medium text-foreground">Supplier Lead Time Delay (days):</span>
                <span className="font-mono font-bold text-amber-400">+{delayDays} days</span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="1"
                value={delayDays}
                onChange={(e) => setDelayDays(Number(e.target.value))}
                className="w-full accent-amber-400 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                <span>+0d (on time)</span>
                <span>+7d (1 week lag)</span>
                <span>+14d (2 weeks)</span>
                <span>+30d (crisis)</span>
              </div>
            </div>
          </div>

          {/* Simulation Outcome Cards */}
          {whatIfData && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3 bg-muted/50 rounded-xl border border-border/60">
                  <p className="text-xs text-muted-foreground">Scenario</p>
                  <p className="text-sm font-semibold text-foreground mt-0.5">{whatIfData.scenario_name}</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-xl border border-border/60">
                  <p className="text-xs text-muted-foreground">Stockout Risk Items</p>
                  <p className="text-lg font-bold text-red-400 mt-0.5">{whatIfData.total_stockout_risks} products</p>
                </div>
                <div className="p-3 bg-muted/50 rounded-xl border border-border/60">
                  <p className="text-xs text-muted-foreground">Est. Capital Required to Buffer</p>
                  <p className="text-lg font-bold text-indigo-400 mt-0.5">£{whatIfData.estimated_capital_impact.toLocaleString()}</p>
                </div>
              </div>

              {/* Simulation Comparison Table */}
              <div className="overflow-x-auto max-h-72 border border-border rounded-xl">
                <table className="w-full text-xs">
                  <thead className="bg-muted/80 sticky top-0">
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-3 font-medium text-muted-foreground">SKU / Product</th>
                      <th className="text-right py-2 px-3 font-medium text-muted-foreground">Stock</th>
                      <th className="text-center py-2 px-3 font-medium text-muted-foreground">Safety Stock (Base → Sim)</th>
                      <th className="text-center py-2 px-3 font-medium text-muted-foreground">Reorder Point (Base → Sim)</th>
                      <th className="text-center py-2 px-3 font-medium text-muted-foreground">Days of Stock</th>
                      <th className="text-center py-2 px-3 font-medium text-muted-foreground">Stockout Risk</th>
                      <th className="text-right py-2 px-3 font-medium text-muted-foreground">Buffer Reorder Qty</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {whatIfData.items.map((it) => (
                      <tr key={it.product_id} className="hover:bg-muted/40 transition-colors">
                        <td className="py-2 px-3">
                          <span className="font-mono text-muted-foreground mr-1.5">{it.sku}</span>
                          <span className="font-medium text-foreground">{it.product_name}</span>
                        </td>
                        <td className="text-right py-2 px-3 font-medium">{it.baseline_stock_on_hand}</td>
                        <td className="text-center py-2 px-3 font-mono">
                          <span className="text-muted-foreground">{it.baseline_safety_stock}</span>
                          <ArrowRight className="inline h-3 w-3 mx-1 text-muted-foreground" />
                          <span className="text-amber-400 font-bold">{it.simulated_safety_stock}</span>
                        </td>
                        <td className="text-center py-2 px-3 font-mono">
                          <span className="text-muted-foreground">{it.baseline_reorder_point}</span>
                          <ArrowRight className="inline h-3 w-3 mx-1 text-muted-foreground" />
                          <span className="text-indigo-400 font-bold">{it.simulated_reorder_point}</span>
                        </td>
                        <td className="text-center py-2 px-3">
                          <span className={it.simulated_days_of_stock < 14 ? 'text-red-400 font-bold' : 'text-foreground'}>
                            {it.simulated_days_of_stock >= 9999 ? '∞' : `${it.simulated_days_of_stock}d`}
                          </span>
                        </td>
                        <td className="text-center py-2 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              it.stockout_risk === 'high'
                                ? 'text-red-400 bg-red-400/10 border border-red-400/30'
                                : it.stockout_risk === 'medium'
                                  ? 'text-amber-400 bg-amber-400/10 border border-amber-400/30'
                                  : it.stockout_risk === 'low'
                                    ? 'text-blue-400 bg-blue-400/10 border border-blue-400/30'
                                    : 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/30'
                            }`}
                          >
                            {it.stockout_risk}
                          </span>
                        </td>
                        <td className="text-right py-2 px-3 font-bold text-foreground">
                          {it.projected_reorder_qty > 0 ? (
                            <span className="text-primary">+{it.projected_reorder_qty}</span>
                          ) : (
                            <span className="text-muted-foreground">0</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Filter:</span>
        <div className="flex gap-1">
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              id={`status-filter-${opt.value || 'all'}`}
              onClick={() => setStatusFilter(opt.value)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                statusFilter === opt.value
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground bg-muted hover:bg-muted/80'
              }`}
            >
              {opt.label}
              {opt.value === 'critical' && summary?.critical_count
                ? ` (${summary.critical_count})`
                : ''}
              {opt.value === 'low' && summary?.low_stock_count
                ? ` (${summary.low_stock_count})`
                : ''}
            </button>
          ))}
        </div>
      </div>

      {/* Inventory table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden">
        {listQuery.isLoading ? (
          <div className="p-6 space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-10 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-muted/30">
                <tr>
                  {[
                    'SKU', 'Product', 'Category', 'Stock', 'Safety Stock', 'Reorder Pt',
                    'EOQ', 'Avg Demand/day', 'Days Stock', 'ABC', 'Status',
                  ].map((h) => (
                    <th key={h} className="text-left text-xs text-muted-foreground px-4 py-3 font-medium whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="text-center py-12 text-muted-foreground text-sm">
                      No inventory data. Run the seed script first.
                    </td>
                  </tr>
                ) : (
                  items.map((item: InventoryItem) => (
                    <tr
                      key={item.product_id}
                      className="border-b border-border/50 hover:bg-muted/20 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
                        {item.sku}
                      </td>
                      <td className="px-4 py-3 text-foreground font-medium max-w-[200px] truncate">
                        {item.product_name}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                        {item.category ?? '–'}
                      </td>
                      <td
                        className={`px-4 py-3 font-bold whitespace-nowrap ${
                          item.status === 'critical'
                            ? 'text-red-400'
                            : item.status === 'low'
                            ? 'text-amber-400'
                            : 'text-foreground'
                        }`}
                      >
                        {item.stock_on_hand}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{item.safety_stock ?? '–'}</td>
                      <td className="px-4 py-3 text-muted-foreground">{item.reorder_point}</td>
                      <td className="px-4 py-3 text-indigo-400 font-medium">{item.eoq ?? '–'}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {item.avg_daily_demand !== null ? item.avg_daily_demand?.toFixed(1) : '–'}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {item.days_of_stock !== null
                          ? item.days_of_stock! > 900
                            ? '∞'
                            : item.days_of_stock?.toFixed(0)
                          : '–'}
                      </td>
                      <td className="px-4 py-3">
                        {item.abc_class ? (
                          <span className={`px-2 py-0.5 rounded font-bold text-xs ${ABC_COLORS[item.abc_class]}`}>
                            {item.abc_class}
                          </span>
                        ) : (
                          '–'
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                            STATUS_STYLES[item.status] ?? ''
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {listQuery.data && (
        <p className="text-xs text-muted-foreground text-right">
          Showing {items.length} of {listQuery.data.total} products
        </p>
      )}
    </div>
  )
}
