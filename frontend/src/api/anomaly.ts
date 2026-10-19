/**
 * API client for Anomaly and Alert endpoints.
 */

import { apiFetch } from './client'

export interface AnomalyItem {
  id: string
  product_id: string | null
  sku: string | null
  product_name: string | null
  detected_date: string
  anomaly_type: string
  detector: string
  severity_score: number
  estimated_impact: number | null
  details: Record<string, unknown> | null
  is_dismissed: boolean
  created_at: string
}

export interface AnomalyListResponse {
  items: AnomalyItem[]
  total: number
}

export interface AlertItem {
  id: string
  anomaly_id: string | null
  title: string
  description: string | null
  severity: 'critical' | 'warning' | 'info'
  is_read: boolean
  created_at: string
}

export interface AlertListResponse {
  items: AlertItem[]
  unread_count: number
}

export interface DetectionRunResult {
  new_anomalies: number
  new_alerts: number
  period_checked: string
}

export function fetchAnomalies(params: {
  only_active?: boolean
  limit?: number
  offset?: number
} = {}): Promise<AnomalyListResponse> {
  const q = new URLSearchParams()
  q.set('only_active', String(params.only_active ?? true))
  if (params.limit) q.set('limit', String(params.limit))
  if (params.offset) q.set('offset', String(params.offset))
  return apiFetch(`/anomaly/?${q}`)
}

export function dismissAnomaly(id: string): Promise<{ status: string }> {
  return apiFetch(`/anomaly/${id}/dismiss`, { method: 'POST' })
}

export function fetchAlerts(params: {
  only_unread?: boolean
  limit?: number
  offset?: number
} = {}): Promise<AlertListResponse> {
  const q = new URLSearchParams()
  if (params.only_unread) q.set('only_unread', 'true')
  if (params.limit) q.set('limit', String(params.limit))
  if (params.offset) q.set('offset', String(params.offset))
  return apiFetch(`/alerts/?${q}`)
}

export function markAlertsRead(alertIds: string[]): Promise<{ marked_read: number }> {
  return apiFetch('/alerts/mark-read', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alert_ids: alertIds }),
  })
}

export function triggerDetection(lookback_days = 30): Promise<DetectionRunResult> {
  return apiFetch(`/anomaly/detect?lookback_days=${lookback_days}`, { method: 'POST' })
}
