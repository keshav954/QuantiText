/**
 * API client for Inventory endpoints.
 */

import { apiFetch } from './client'

export interface InventoryItem {
  product_id: string
  sku: string
  product_name: string
  category: string | null
  stock_on_hand: number
  reorder_point: number
  lead_time_days: number
  min_order_qty: number
  unit_cost: number
  holding_cost_pct: number
  avg_daily_demand: number | null
  safety_stock: number | null
  eoq: number | null
  days_of_stock: number | null
  abc_class: string | null
  status: 'ok' | 'low' | 'critical' | 'overstock'
  last_updated: string | null
}

export interface InventoryListResponse {
  items: InventoryItem[]
  total: number
  low_stock_count: number
  critical_count: number
}

export interface InventorySummary {
  total_products: number
  low_stock_count: number
  critical_count: number
  overstock_count: number
  total_inventory_value: number
}

export interface ReorderSuggestion {
  product_id: string
  sku: string
  product_name: string
  current_stock: number
  reorder_point: number
  eoq: number
  suggested_qty: number
  estimated_cost: number
  urgency: 'immediate' | 'soon' | 'watch'
}

export function fetchInventorySummary(): Promise<InventorySummary> {
  return apiFetch('/inventory/summary')
}

export function fetchInventoryList(params: {
  status?: string
  category?: string
  limit?: number
  offset?: number
} = {}): Promise<InventoryListResponse> {
  const q = new URLSearchParams()
  if (params.status) q.set('status', params.status)
  if (params.category) q.set('category', params.category)
  if (params.limit) q.set('limit', String(params.limit))
  if (params.offset) q.set('offset', String(params.offset))
  return apiFetch(`/inventory/?${q}`)
}

export function fetchReorderSuggestions(limit = 20): Promise<ReorderSuggestion[]> {
  return apiFetch(`/inventory/reorder-suggestions?limit=${limit}`)
}
