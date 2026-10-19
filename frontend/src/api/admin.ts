/**
 * Admin API hooks — upload and data onboarding.
 */

import { useMutation } from '@tanstack/react-query'

const API_BASE = '/api/v1'

// ── Types ────────────────────────────────────────────────

export interface ColumnMapping {
  source_column: string
  target_column: string
  transform: string | null
}

export interface UploadPreviewResponse {
  filename: string
  row_count: number
  detected_columns: string[]
  suggested_mappings: ColumnMapping[]
  sample_rows: Record<string, unknown>[]
}

export interface UploadValidationResult {
  is_valid: boolean
  total_rows: number
  valid_rows: number
  error_count: number
  errors: string[]
  warnings: string[]
}

export interface UploadResult {
  success: boolean
  rows_loaded: number
  products_created: number
  orders_created: number
  message: string
}

// ── Functions ────────────────────────────────────────────

export async function uploadFile(file: File): Promise<{ filename: string; size_bytes: number }> {
  const token = localStorage.getItem('quantitext-token')
  const form = new FormData()
  form.append('file', file)

  const res = await fetch(`${API_BASE}/admin/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? 'Upload failed')
  }
  return res.json()
}

export async function previewUpload(filename: string): Promise<UploadPreviewResponse> {
  const token = localStorage.getItem('quantitext-token')
  const res = await fetch(`${API_BASE}/admin/upload/preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ filename }),
  })
  if (!res.ok) throw new Error('Preview failed')
  return res.json()
}

export async function validateUpload(
  filename: string,
  mappings: ColumnMapping[],
): Promise<UploadValidationResult> {
  const token = localStorage.getItem('quantitext-token')
  const res = await fetch(`${API_BASE}/admin/upload/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ filename, mappings }),
  })
  if (!res.ok) throw new Error('Validation failed')
  return res.json()
}

export async function confirmUpload(
  filename: string,
  mappings: ColumnMapping[],
  replaceExisting: boolean,
): Promise<UploadResult> {
  const token = localStorage.getItem('quantitext-token')
  const res = await fetch(`${API_BASE}/admin/upload/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ filename, mappings, replace_existing: replaceExisting }),
  })
  if (!res.ok) throw new Error('Load failed')
  return res.json()
}

// ── Hooks ────────────────────────────────────────────────

export function useUploadFile() {
  return useMutation({ mutationFn: uploadFile })
}

export function usePreviewUpload() {
  return useMutation({ mutationFn: (filename: string) => previewUpload(filename) })
}
