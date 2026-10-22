/**
 * Reports API hooks — TanStack Query wrappers for /reports endpoints.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

// ── Types ────────────────────────────────────────────────

export interface ReportOut {
  id: string
  org_id: string
  generated_by: string | null
  title: string
  report_type: string
  narrative: string | null
  file_path: string | null
  created_at: string
  has_data: boolean
}

export interface ReportDetail extends ReportOut {
  aggregated_data: Record<string, unknown> | null
}

export interface ReportListResponse {
  items: ReportOut[]
  total: number
}

export interface RecommendationOut {
  id: string
  org_id: string
  product_id: string | null
  product_name: string | null
  sku: string | null
  action_type: string
  reason: string
  parameters: Record<string, unknown> | null
  status: string
  approved_by: string | null
  decided_at: string | null
  created_at: string
}

export interface RecommendationListResponse {
  items: RecommendationOut[]
  total: number
  pending_count: number
}

// ── Hooks ────────────────────────────────────────────────

export function useReports(limit = 20) {
  return useQuery({
    queryKey: ['reports', limit],
    queryFn: () => api.get<ReportListResponse>(`/reports?limit=${limit}`),
  })
}

export function useReport(id: string | null) {
  return useQuery({
    queryKey: ['reports', id],
    queryFn: () => api.get<ReportDetail>(`/reports/${id}`),
    enabled: !!id,
  })
}

export function useGenerateReport() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { title?: string; report_type?: string }) =>
      api.post<ReportDetail>('/reports/generate', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  })
}

export function useRecommendations(status?: string) {
  const params = status ? `?status=${status}` : ''
  return useQuery({
    queryKey: ['recommendations', status],
    queryFn: () => api.get<RecommendationListResponse>(`/reports/recommendations${params}`),
  })
}

export function useDecideRecommendation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' }) =>
      api.post(`/reports/recommendations/${id}/decide`, { action }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recommendations'] }),
  })
}

export async function downloadPurchaseOrder(recommendationId: string): Promise<void> {
  const token = localStorage.getItem('quantitext-token')
  const res = await fetch(`/api/v1/reports/recommendations/${recommendationId}/po`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('Failed to download purchase order')
  const text = await res.text()
  const blob = new Blob([text], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `PO_${recommendationId.slice(0, 8)}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
