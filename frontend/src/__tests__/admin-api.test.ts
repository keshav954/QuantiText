/**
 * Tests for admin API module — column mapping and upload types.
 */

import { describe, it, expect } from 'vitest'
import type { ColumnMapping, UploadPreviewResponse, UploadValidationResult, UploadResult } from '@/api/admin'

describe('Admin API Types', () => {
  it('ColumnMapping has the correct shape', () => {
    const mapping: ColumnMapping = {
      source_column: 'InvoiceNo',
      target_column: 'invoice_no',
      transform: null,
    }
    expect(mapping.source_column).toBe('InvoiceNo')
    expect(mapping.target_column).toBe('invoice_no')
    expect(mapping.transform).toBeNull()
  })

  it('UploadPreviewResponse has required fields', () => {
    const preview: UploadPreviewResponse = {
      filename: 'test.csv',
      row_count: 1000,
      detected_columns: ['Col1', 'Col2'],
      suggested_mappings: [],
      sample_rows: [{ Col1: 'a', Col2: 'b' }],
    }
    expect(preview.row_count).toBe(1000)
    expect(preview.detected_columns).toHaveLength(2)
    expect(preview.sample_rows).toHaveLength(1)
  })

  it('UploadValidationResult distinguishes valid/invalid', () => {
    const valid: UploadValidationResult = {
      is_valid: true,
      total_rows: 500,
      valid_rows: 500,
      error_count: 0,
      errors: [],
      warnings: ['2 rows have zero price'],
    }
    expect(valid.is_valid).toBe(true)
    expect(valid.warnings).toHaveLength(1)

    const invalid: UploadValidationResult = {
      is_valid: false,
      total_rows: 500,
      valid_rows: 480,
      error_count: 20,
      errors: ['Column "quantity" has 20 non-numeric values'],
      warnings: [],
    }
    expect(invalid.is_valid).toBe(false)
    expect(invalid.error_count).toBe(20)
  })

  it('UploadResult tracks loaded counts', () => {
    const result: UploadResult = {
      success: true,
      rows_loaded: 450,
      products_created: 12,
      orders_created: 200,
      message: 'Successfully loaded 450 rows.',
    }
    expect(result.success).toBe(true)
    expect(result.rows_loaded).toBe(450)
    expect(result.products_created).toBe(12)
  })
})
