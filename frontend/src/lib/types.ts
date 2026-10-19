/**
 * Shared TypeScript types used across multiple pages and components.
 * Centralizes common interfaces to avoid duplication and drift.
 */

/** Standard API paginated response envelope. */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

/** Generic API error payload. */
export interface ApiError {
  detail: string
  status_code?: number
}

/** Severity levels used across alerts and anomalies. */
export type Severity = 'critical' | 'warning' | 'info'

/** Inventory status levels. */
export type StockStatus = 'critical' | 'low' | 'ok' | 'overstock'

/** ABC classification for inventory items. */
export type AbcClass = 'A' | 'B' | 'C'

/** Recommendation decision statuses. */
export type RecommendationStatus = 'pending' | 'approved' | 'rejected' | 'implemented'

/** Report generation status. */
export type ReportStatus = 'generating' | 'ready' | 'error'

/** Anomaly detector identifiers. */
export type DetectorType = 'zscore' | 'iforest' | 'data_quality'

/** Anomaly type identifiers. */
export type AnomalyType = 'revenue_spike' | 'revenue_drop' | 'zero_sales' | 'inventory_critical'

/** Chart type hints returned from the copilot. */
export type ChartType = 'line' | 'bar' | 'pie' | 'table'

/** Date range preset keys used in the date-range-context store. */
export type DateRangePreset = '7d' | '30d' | '90d' | 'ytd' | 'custom'

/** Sort direction for table columns. */
export type SortDir = 'asc' | 'desc'
