/**
 * Admin page — data upload (BYOD onboarding) and system settings.
 *
 * Upload flow:
 * 1. Drop/select CSV/Excel file
 * 2. Preview auto-detected columns
 * 3. Adjust mappings
 * 4. Validate
 * 5. Confirm load
 */

import { useState, useCallback } from 'react'
import {
  Upload,
  FileUp,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ArrowRight,
  RotateCcw,
  Table,
} from 'lucide-react'
import {
  uploadFile,
  previewUpload,
  validateUpload,
  confirmUpload,
  type ColumnMapping,
  type UploadPreviewResponse,
  type UploadValidationResult,
  type UploadResult,
} from '@/api/admin'

type Step = 'upload' | 'preview' | 'validate' | 'result'

export function AdminPage() {
  const [step, setStep] = useState<Step>('upload')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // State across steps
  const [filename, setFilename] = useState('')
  const [preview, setPreview] = useState<UploadPreviewResponse | null>(null)
  const [mappings, setMappings] = useState<ColumnMapping[]>([])
  const [validation, setValidation] = useState<UploadValidationResult | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)

  const reset = () => {
    setStep('upload')
    setFilename('')
    setPreview(null)
    setMappings([])
    setValidation(null)
    setResult(null)
    setError(null)
  }

  const handleFileUpload = useCallback(async (file: File) => {
    setLoading(true)
    setError(null)
    try {
      const res = await uploadFile(file)
      setFilename(res.filename)

      // Auto-preview
      const prev = await previewUpload(res.filename)
      setPreview(prev)
      setMappings(prev.suggested_mappings)
      setStep('preview')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleValidate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await validateUpload(filename, mappings)
      setValidation(res)
      setStep('validate')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [filename, mappings])

  const handleConfirm = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await confirmUpload(filename, mappings, false)
      setResult(res)
      setStep('result')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [filename, mappings])

  return (
    <div className="space-y-6 max-w-[1200px] mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Admin</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload your own data and manage system settings
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 text-xs">
        {(['upload', 'preview', 'validate', 'result'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            {i > 0 && <ArrowRight className="h-3 w-3 text-muted-foreground/40" />}
            <span
              className={`px-3 py-1 rounded-full ${
                step === s
                  ? 'bg-primary/20 text-primary font-medium'
                  : 'bg-secondary/50 text-muted-foreground'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </span>
          </div>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-critical/30 bg-critical/10 px-4 py-3">
          <p className="text-sm text-critical">{error}</p>
        </div>
      )}

      {/* Steps */}
      {step === 'upload' && <UploadStep onUpload={handleFileUpload} loading={loading} />}
      {step === 'preview' && preview && (
        <PreviewStep
          preview={preview}
          mappings={mappings}
          onMappingsChange={setMappings}
          onValidate={handleValidate}
          loading={loading}
        />
      )}
      {step === 'validate' && validation && (
        <ValidateStep
          validation={validation}
          onConfirm={handleConfirm}
          onBack={() => setStep('preview')}
          loading={loading}
        />
      )}
      {step === 'result' && result && <ResultStep result={result} onReset={reset} />}
    </div>
  )
}

// ── Upload Step ──────────────────────────────────────────

function UploadStep({
  onUpload,
  loading,
}: {
  onUpload: (file: File) => void
  loading: boolean
}) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) onUpload(file)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
        isDragOver
          ? 'border-primary bg-primary/5'
          : 'border-border/50 bg-card hover:border-border'
      }`}
    >
      {loading ? (
        <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary/60" />
      ) : (
        <FileUp className="mx-auto h-12 w-12 text-muted-foreground/40" />
      )}
      <h3 className="mt-4 text-lg font-semibold text-foreground">
        {loading ? 'Processing...' : 'Upload your data'}
      </h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Drag and drop a CSV or Excel file, or click to browse
      </p>
      <p className="mt-1 text-xs text-muted-foreground/60">
        Supports .csv, .xlsx formats. Max file size: 50MB
      </p>
      <label className="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 cursor-pointer transition-colors">
        <Upload className="h-4 w-4" />
        Browse Files
        <input
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload-input"
        />
      </label>
    </div>
  )
}

// ── Preview Step ─────────────────────────────────────────

function PreviewStep({
  preview,
  mappings,
  onMappingsChange,
  onValidate,
  loading,
}: {
  preview: UploadPreviewResponse
  mappings: ColumnMapping[]
  onMappingsChange: (m: ColumnMapping[]) => void
  onValidate: () => void
  loading: boolean
}) {
  const targetOptions = [
    '', 'invoice_no', 'invoice_date', 'sku', 'product_name',
    'quantity', 'unit_price', 'customer_id', 'country',
  ]

  const updateMapping = (index: number, target: string) => {
    const updated = [...mappings]
    updated[index] = { ...updated[index], target_column: target }
    onMappingsChange(updated)
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border/50 bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Column Mapping</h3>
            <p className="text-xs text-muted-foreground">
              {preview.row_count.toLocaleString()} rows detected · {preview.detected_columns.length} columns
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {preview.detected_columns.map((col) => {
            const mapping = mappings.find((m) => m.source_column === col)
            return (
              <div key={col} className="flex items-center gap-3 py-2 px-3 rounded-lg bg-secondary/30">
                <span className="text-sm text-foreground min-w-[200px] font-mono">{col}</span>
                <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                <select
                  value={mapping?.target_column ?? ''}
                  onChange={(e) => {
                    if (mapping) {
                      const idx = mappings.indexOf(mapping)
                      updateMapping(idx, e.target.value)
                    } else {
                      onMappingsChange([
                        ...mappings,
                        { source_column: col, target_column: e.target.value, transform: null },
                      ])
                    }
                  }}
                  className="flex-1 rounded-md bg-background border border-border px-3 py-1.5 text-sm text-foreground"
                >
                  {targetOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt || '— skip —'}
                    </option>
                  ))}
                </select>
              </div>
            )
          })}
        </div>
      </div>

      {/* Sample data preview */}
      {preview.sample_rows.length > 0 && (
        <div className="rounded-xl border border-border/50 bg-card p-5 overflow-x-auto">
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Table className="h-4 w-4" />
            Sample Data (first 5 rows)
          </h3>
          <table className="w-full text-xs">
            <thead>
              <tr>
                {preview.detected_columns.map((col) => (
                  <th key={col} className="px-3 py-2 text-left text-muted-foreground font-medium border-b border-border/30">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.sample_rows.map((row, i) => (
                <tr key={i} className="hover:bg-secondary/20">
                  {preview.detected_columns.map((col) => (
                    <td key={col} className="px-3 py-1.5 text-foreground/80 border-b border-border/10">
                      {String(row[col] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <button
        id="btn-validate-upload"
        onClick={onValidate}
        disabled={loading || mappings.length === 0}
        className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
        Validate Data
      </button>
    </div>
  )
}

// ── Validate Step ────────────────────────────────────────

function ValidateStep({
  validation,
  onConfirm,
  onBack,
  loading,
}: {
  validation: UploadValidationResult
  onConfirm: () => void
  onBack: () => void
  loading: boolean
}) {
  return (
    <div className="space-y-4">
      <div className={`rounded-xl border p-5 ${
        validation.is_valid
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-critical/30 bg-critical/5'
      }`}>
        <div className="flex items-center gap-3 mb-3">
          {validation.is_valid ? (
            <CheckCircle2 className="h-6 w-6 text-emerald-500" />
          ) : (
            <XCircle className="h-6 w-6 text-critical" />
          )}
          <h3 className="text-sm font-semibold text-foreground">
            {validation.is_valid ? 'Validation Passed' : 'Validation Failed'}
          </h3>
        </div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total Rows:</span>{' '}
            <span className="font-medium">{validation.total_rows.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Valid:</span>{' '}
            <span className="font-medium text-emerald-400">{validation.valid_rows.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Errors:</span>{' '}
            <span className="font-medium text-critical">{validation.error_count}</span>
          </div>
        </div>
      </div>

      {validation.errors.length > 0 && (
        <div className="rounded-lg bg-critical/5 p-4 space-y-1">
          <h4 className="text-xs font-semibold text-critical uppercase">Errors</h4>
          {validation.errors.map((e, i) => (
            <p key={i} className="text-xs text-critical/80 flex items-start gap-1.5">
              <XCircle className="h-3 w-3 mt-0.5 shrink-0" /> {e}
            </p>
          ))}
        </div>
      )}

      {validation.warnings.length > 0 && (
        <div className="rounded-lg bg-warning/5 p-4 space-y-1">
          <h4 className="text-xs font-semibold text-warning uppercase">Warnings</h4>
          {validation.warnings.map((w, i) => (
            <p key={i} className="text-xs text-warning/80 flex items-start gap-1.5">
              <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" /> {w}
            </p>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-lg bg-secondary px-4 py-2.5 text-sm font-medium text-foreground hover:bg-secondary/80 transition-colors"
        >
          ← Back to Mapping
        </button>
        {validation.is_valid && (
          <button
            id="btn-confirm-upload"
            onClick={onConfirm}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Confirm & Load Data
          </button>
        )}
      </div>
    </div>
  )
}

// ── Result Step ──────────────────────────────────────────

function ResultStep({ result, onReset }: { result: UploadResult; onReset: () => void }) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-8 text-center">
      {result.success ? (
        <CheckCircle2 className="mx-auto h-16 w-16 text-emerald-500" />
      ) : (
        <XCircle className="mx-auto h-16 w-16 text-critical" />
      )}
      <h3 className="mt-4 text-lg font-semibold text-foreground">
        {result.success ? 'Data Loaded Successfully' : 'Load Failed'}
      </h3>
      <p className="mt-2 text-sm text-muted-foreground">{result.message}</p>
      {result.success && (
        <div className="mt-4 flex justify-center gap-6 text-sm">
          <div>
            <span className="text-muted-foreground">Rows loaded: </span>
            <span className="font-semibold">{result.rows_loaded.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Products: </span>
            <span className="font-semibold">{result.products_created}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Orders: </span>
            <span className="font-semibold">{result.orders_created}</span>
          </div>
        </div>
      )}
      <button
        onClick={onReset}
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-secondary px-6 py-2.5 text-sm font-medium text-foreground hover:bg-secondary/80 transition-colors"
      >
        <RotateCcw className="h-4 w-4" />
        Upload Another File
      </button>
    </div>
  )
}
