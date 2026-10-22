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

export interface WhatIfRequest {
  demand_change_pct: number
  lead_time_delay_days: number
  product_id?: string | null
}

export interface WhatIfItemResult {
  product_id: string
  sku: string
  product_name: string
  baseline_stock_on_hand: number
  baseline_safety_stock: number
  baseline_reorder_point: number
  baseline_days_of_stock: number
  simulated_safety_stock: number
  simulated_reorder_point: number
  simulated_days_of_stock: number
  stockout_risk: 'high' | 'medium' | 'low' | 'none'
  stockout_in_days: number | null
  projected_reorder_qty: number
  projected_additional_cost: number
}

export interface WhatIfResponse {
  scenario_name: string
  demand_change_pct: number
  lead_time_delay_days: number
  items: WhatIfItemResult[]
  total_stockout_risks: number
  estimated_capital_impact: number
  synthetic_notice: string
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

export function simulateWhatIf(payload: WhatIfRequest): Promise<WhatIfResponse> {
  return apiFetch('/inventory/what-if', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

