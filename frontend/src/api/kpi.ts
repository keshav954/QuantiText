/**
 * KPI API hooks — TanStack Query wrappers for the /kpi endpoints.
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useDateRange } from '@/store/date-range-context'
import { format } from 'date-fns'

// ── Types ────────────────────────────────────────────────

export interface KPISummary {
  total_revenue: number
  total_orders: number
  avg_order_value: number
  unique_customers: number
  revenue_trend: number | null
  orders_trend: number | null
}

export interface RevenueTrendPoint {
  date: string
  revenue: number
  order_count: number
}

export interface RevenueTrendResponse {
  data: RevenueTrendPoint[]
  period: string
}

export interface TopProduct {
  product_id: string
  sku: string
  product_name: string
  category: string
  total_revenue: number
  total_qty: number
}

export interface TopProductsResponse {
  products: TopProduct[]
  limit: number
}

// ── Helpers ──────────────────────────────────────────────

function dateParams(from: Date, to: Date): string {
  return `start_date=${format(from, 'yyyy-MM-dd')}&end_date=${format(to, 'yyyy-MM-dd')}`
}

// ── Hooks ────────────────────────────────────────────────

export function useKPISummary() {
  const { range } = useDateRange()
  return useQuery({
    queryKey: ['kpi', 'summary', range.from.toISOString(), range.to.toISOString()],
    queryFn: () => api.get<KPISummary>(`/kpi/summary?${dateParams(range.from, range.to)}`),
  })
}

export function useRevenueTrend() {
  const { range } = useDateRange()
  return useQuery({
    queryKey: ['kpi', 'revenue-trend', range.from.toISOString(), range.to.toISOString()],
    queryFn: () =>
      api.get<RevenueTrendResponse>(`/kpi/revenue-trend?${dateParams(range.from, range.to)}`),
  })
}

export function useTopProducts(limit = 10) {
  return useQuery({
    queryKey: ['kpi', 'top-products', limit],
    queryFn: () => api.get<TopProductsResponse>(`/kpi/top-products?limit=${limit}`),
  })
}
