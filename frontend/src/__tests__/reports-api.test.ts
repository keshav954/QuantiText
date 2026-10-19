/**
 * Tests for report API types and hooks structure.
 */

import { describe, it, expect } from 'vitest'
import type {
  ReportOut,
  ReportDetail,
  ReportListResponse,
  RecommendationOut,
  RecommendationListResponse,
} from '@/api/reports'

describe('Reports API Types', () => {
  it('ReportOut has required fields', () => {
    const report: ReportOut = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      org_id: '123e4567-e89b-12d3-a456-426614174001',
      generated_by: null,
      title: 'Weekly Report',
      report_type: 'weekly',
      narrative: 'Revenue increased by 15%...',
      file_path: null,
      created_at: '2024-01-01T00:00:00Z',
      has_data: true,
    }
    expect(report.report_type).toBe('weekly')
    expect(report.has_data).toBe(true)
    expect(report.generated_by).toBeNull()
  })

  it('ReportDetail extends ReportOut with aggregated_data', () => {
    const detail: ReportDetail = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      org_id: '123e4567-e89b-12d3-a456-426614174001',
      generated_by: '123e4567-e89b-12d3-a456-426614174002',
      title: 'Weekly Report',
      report_type: 'on_demand',
      narrative: 'Revenue decreased...',
      file_path: null,
      created_at: '2024-01-01T00:00:00Z',
      has_data: true,
      aggregated_data: {
        kpi_summary: { total_revenue: 125000, total_orders: 500 },
        top_products: [{ name: 'Widget A', revenue: 15000 }],
      },
    }
    expect(detail.aggregated_data).toBeDefined()
    expect(detail.aggregated_data!.kpi_summary).toBeDefined()
  })

  it('ReportListResponse has items and total', () => {
    const response: ReportListResponse = {
      items: [],
      total: 0,
    }
    expect(response.items).toHaveLength(0)
    expect(response.total).toBe(0)
  })

  it('RecommendationOut tracks approval state', () => {
    const pending: RecommendationOut = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      org_id: '123e4567-e89b-12d3-a456-426614174001',
      product_id: '123e4567-e89b-12d3-a456-426614174002',
      product_name: 'Widget A',
      sku: 'WDG-001',
      action_type: 'reorder',
      reason: 'Stock below reorder point',
      parameters: { quantity: 100 },
      status: 'pending',
      approved_by: null,
      decided_at: null,
      created_at: '2024-01-01T00:00:00Z',
    }
    expect(pending.status).toBe('pending')
    expect(pending.approved_by).toBeNull()

    const approved: RecommendationOut = {
      ...pending,
      status: 'approved',
      approved_by: '123e4567-e89b-12d3-a456-426614174003',
      decided_at: '2024-01-02T10:00:00Z',
    }
    expect(approved.status).toBe('approved')
    expect(approved.decided_at).toBeTruthy()
  })

  it('RecommendationListResponse tracks pending count', () => {
    const response: RecommendationListResponse = {
      items: [],
      total: 15,
      pending_count: 3,
    }
    expect(response.pending_count).toBe(3)
    expect(response.total).toBe(15)
  })
})
