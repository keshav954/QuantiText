/**
 * Forecasts page — product forecast with confidence bands + SHAP importances.
 * Phase 4.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  Cell,
} from 'recharts'
import {
  TrendingUp,
  AlertCircle,
  Brain,
  Calendar,
} from 'lucide-react'
import { fetchForecastList, fetchForecast, type ForecastSummary } from '@/api/forecast'

const HORIZON_OPTIONS = [7, 14, 30, 60, 90]

const SHAP_COLORS = [
  '#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe',
]

export function ForecastsPage() {
  const [selectedProduct, setSelectedProduct] = useState<ForecastSummary | null>(null)
  const [horizon, setHorizon] = useState(30)
  const [_showProducts, _setShowProducts] = useState(false)

  // List of products with forecasts
  const listQuery = useQuery({
    queryKey: ['forecast-list'],
    queryFn: () => fetchForecastList(50),
  })

  // Forecast data for selected product
  const forecastQuery = useQuery({
    queryKey: ['forecast', selectedProduct?.product_id, horizon],
    queryFn: () => fetchForecast(selectedProduct!.product_id, horizon),
    enabled: !!selectedProduct,
  })

  const forecasts = forecastQuery.data
  const products = listQuery.data?.forecasts ?? []

  // Format chart data
  const chartData = (forecasts?.forecasts ?? []).map((f) => ({
    date: new Date(f.date).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }),
    predicted: Math.round(f.predicted_qty),
    lower: Math.round(f.lower_bound),
    upper: Math.round(f.upper_bound),
  }))

  // SHAP features data
  const shapData = Object.entries(forecasts?.shap_features ?? {})
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([name, value]) => ({ name, value: Math.round(value * 1000) / 10 }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-primary" />
            Demand Forecasts
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            LightGBM model with conformal prediction intervals • SHAP feature importance
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Horizon selector */}
          <div className="flex items-center gap-1 bg-card border border-border rounded-lg p-1">
            {HORIZON_OPTIONS.map((h) => (
              <button
                key={h}
                id={`horizon-btn-${h}`}
                onClick={() => setHorizon(h)}
                className={`px-3 py-1 rounded text-sm font-medium transition-all ${
                  horizon === h
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {h}d
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Product selector sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-card border border-border rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-foreground">Products</h2>
              <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                {products.length}
              </span>
            </div>

            {listQuery.isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-14 bg-muted animate-pulse rounded-lg" />
                ))}
              </div>
            ) : products.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">
                <Brain className="h-8 w-8 mx-auto mb-2 opacity-40" />
                <p>No forecasts yet.</p>
                <p className="text-xs mt-1">Seed data and trigger a retrain.</p>
              </div>
            ) : (
              <div className="space-y-1 max-h-[600px] overflow-y-auto pr-1">
                {products.map((p) => (
                  <button
                    key={p.product_id}
                    id={`product-btn-${p.product_id}`}
                    onClick={() => setSelectedProduct(p)}
                    className={`w-full text-left p-3 rounded-xl transition-all group ${
                      selectedProduct?.product_id === p.product_id
                        ? 'bg-primary/10 border border-primary/20'
                        : 'hover:bg-muted border border-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-foreground truncate">
                          {p.product_name}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">{p.sku}</p>
                      </div>
                      {p.avg_mape !== null && (
                        <span
                          className={`text-xs font-mono ml-2 shrink-0 ${
                            p.avg_mape < 15
                              ? 'text-emerald-400'
                              : p.avg_mape < 25
                              ? 'text-amber-400'
                              : 'text-red-400'
                          }`}
                        >
                          {p.avg_mape.toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {p.model_name}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main forecast area */}
        <div className="lg:col-span-3 space-y-6">
          {!selectedProduct ? (
            <div className="bg-card border border-border rounded-2xl p-12 text-center">
              <TrendingUp className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
              <h3 className="text-foreground font-medium mb-1">Select a product</h3>
              <p className="text-muted-foreground text-sm">
                Choose a product from the left panel to view its demand forecast.
              </p>
            </div>
          ) : (
            <>
              {/* Product header */}
              <div className="bg-card border border-border rounded-2xl p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-foreground">
                      {selectedProduct.product_name}
                    </h2>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      SKU: {selectedProduct.sku} · Model: {selectedProduct.model_name}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-right">
                    {forecasts?.mape !== null && forecasts?.mape !== undefined && (
                      <div>
                        <p className="text-xs text-muted-foreground">MAPE</p>
                        <p
                          className={`text-xl font-bold ${
                            forecasts.mape < 15
                              ? 'text-emerald-400'
                              : forecasts.mape < 25
                              ? 'text-amber-400'
                              : 'text-red-400'
                          }`}
                        >
                          {forecasts.mape.toFixed(1)}%
                        </p>
                      </div>
                    )}
                    {forecasts?.rmse !== null && forecasts?.rmse !== undefined && (
                      <div>
                        <p className="text-xs text-muted-foreground">RMSE</p>
                        <p className="text-xl font-bold text-foreground">
                          {forecasts.rmse.toFixed(1)}
                        </p>
                      </div>
                    )}
                    {forecasts?.from_cache && (
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-full">
                        cached
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Forecast chart */}
              <div className="bg-card border border-border rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-foreground mb-4">
                  {horizon}-Day Demand Forecast
                  <span className="text-muted-foreground font-normal ml-2 text-xs">
                    with 90% prediction interval
                  </span>
                </h3>

                {forecastQuery.isLoading ? (
                  <div className="h-64 bg-muted animate-pulse rounded-xl" />
                ) : forecasts?.error ? (
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    <AlertCircle className="h-5 w-5 mr-2" />
                    {forecasts.error}
                  </div>
                ) : chartData.length === 0 ? (
                  <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
                    No forecast data available
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="intervalGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.08} />
                          <stop offset="95%" stopColor="#a78bfa" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: '#6b7280' }}
                        tickLine={false}
                        axisLine={false}
                        interval={Math.floor(chartData.length / 6)}
                      />
                      <YAxis
                        tick={{ fontSize: 11, fill: '#6b7280' }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `${v}`}
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '12px',
                          color: 'hsl(var(--foreground))',
                          fontSize: '12px',
                        }}
                        formatter={(value: number, name: string) => [
                          `${value} units`,
                          name === 'predicted' ? 'Forecast' : name === 'lower' ? 'Lower bound' : 'Upper bound',
                        ]}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
                        formatter={(v) =>
                          v === 'predicted'
                            ? 'Predicted'
                            : v === 'lower'
                            ? 'Lower (90%)'
                            : 'Upper (90%)'
                        }
                      />
                      {/* Confidence interval band */}
                      <Area
                        type="monotone"
                        dataKey="upper"
                        stroke="none"
                        fill="url(#intervalGrad)"
                        fillOpacity={1}
                        legendType="none"
                      />
                      <Area
                        type="monotone"
                        dataKey="lower"
                        stroke="#a78bfa"
                        strokeWidth={1}
                        strokeDasharray="4 2"
                        fill="white"
                        fillOpacity={0}
                      />
                      {/* Main forecast line */}
                      <Area
                        type="monotone"
                        dataKey="predicted"
                        stroke="#6366f1"
                        strokeWidth={2.5}
                        fill="url(#forecastGrad)"
                        dot={false}
                        activeDot={{ r: 5, fill: '#6366f1' }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* SHAP feature importance */}
              {shapData.length > 0 && (
                <div className="bg-card border border-border rounded-2xl p-5">
                  <h3 className="text-sm font-semibold text-foreground mb-4">
                    Top Feature Importances
                    <span className="text-muted-foreground font-normal ml-2 text-xs">
                      SHAP values — what drives this forecast
                    </span>
                  </h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart
                      data={shapData}
                      layout="vertical"
                      margin={{ top: 0, right: 20, left: 80, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} axisLine={false} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 11, fill: '#9ca3af' }}
                        tickLine={false}
                        axisLine={false}
                        width={75}
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        formatter={(v: number) => [`${v.toFixed(1)}%`, 'Importance']}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                        {shapData.map((_, index) => (
                          <Cell key={index} fill={SHAP_COLORS[index % SHAP_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
