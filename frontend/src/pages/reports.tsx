/**
 * Reports page — generated BI reports with narrative and recommendations.
 *
 * Features:
 * - Generate new report button
 * - Report list with expandable detail
 * - Recommendation approval/reject flow
 * - Export as text
 */

import { useState } from 'react'
import { format } from 'date-fns'
import {
  FileText,
  Plus,
  Download,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertTriangle,
  TrendingUp,
  Package,
  BarChart3,
} from 'lucide-react'
import {
  useReports,
  useReport,
  useGenerateReport,
  useRecommendations,
  useDecideRecommendation,
  type ReportOut,
  type RecommendationOut,
} from '@/api/reports'

export function ReportsPage() {
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'reports' | 'approvals'>('reports')

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Reports</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Auto-generated business intelligence reports with AI narrative
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-secondary/50 p-1 w-fit">
        <button
          id="tab-reports"
          onClick={() => setActiveTab('reports')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'reports'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className="inline h-4 w-4 mr-1.5 -mt-0.5" />
          Reports
        </button>
        <button
          id="tab-approvals"
          onClick={() => setActiveTab('approvals')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'approvals'
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <CheckCircle2 className="inline h-4 w-4 mr-1.5 -mt-0.5" />
          Approvals
        </button>
      </div>

      {activeTab === 'reports' && (
        <ReportsTab
          selectedId={selectedReportId}
          onSelect={setSelectedReportId}
        />
      )}
      {activeTab === 'approvals' && <ApprovalsTab />}
    </div>
  )
}

// ── Reports Tab ──────────────────────────────────────────

function ReportsTab({
  selectedId,
  onSelect,
}: {
  selectedId: string | null
  onSelect: (id: string | null) => void
}) {
  const { data, isLoading, isError } = useReports()
  const generateMutation = useGenerateReport()

  const handleGenerate = () => {
    generateMutation.mutate({
      title: `Weekly Report — ${format(new Date(), 'MMM dd, yyyy')}`,
      report_type: 'on_demand',
    })
  }

  return (
    <div className="space-y-4">
      {/* Actions */}
      <div className="flex gap-3">
        <button
          id="btn-generate-report"
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {generateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          Generate Report
        </button>
      </div>

      {/* Success message */}
      {generateMutation.isSuccess && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
          <p className="text-sm text-emerald-400">
            ✓ Report generated successfully
          </p>
        </div>
      )}

      {/* Error */}
      {(isError || generateMutation.isError) && (
        <div className="rounded-lg border border-critical/30 bg-critical/10 px-4 py-3">
          <p className="text-sm text-critical">
            Failed to {generateMutation.isError ? 'generate report' : 'load reports'}
          </p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary/60" />
        </div>
      )}

      {/* Report list */}
      {data && (
        <div className="space-y-3">
          {data.items.length === 0 ? (
            <div className="rounded-xl border border-border/50 bg-card p-8 text-center">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground/40" />
              <p className="mt-3 text-sm text-muted-foreground">
                No reports yet. Generate your first report above.
              </p>
            </div>
          ) : (
            data.items.map((report) => (
              <ReportCard
                key={report.id}
                report={report}
                isExpanded={selectedId === report.id}
                onToggle={() => onSelect(selectedId === report.id ? null : report.id)}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}

function ReportCard({
  report,
  isExpanded,
  onToggle,
}: {
  report: ReportOut
  isExpanded: boolean
  onToggle: () => void
}) {
  const { data: detail, isLoading } = useReport(isExpanded ? report.id : null)

  const handleExport = (e: React.MouseEvent) => {
    e.stopPropagation()
    const _token = localStorage.getItem('quantitext-token')
    window.open(
      `/api/v1/reports/${report.id}/export`,
      '_blank'
    )
  }

  return (
    <div className="rounded-xl border border-border/50 bg-card overflow-hidden transition-all hover:border-border">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-5 py-4 text-left"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-foreground truncate">{report.title}</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {report.report_type === 'weekly' ? '📅 Weekly' : '📊 On-demand'} ·{' '}
            {format(new Date(report.created_at), 'MMM dd, yyyy HH:mm')}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {report.has_data && (
            <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
              Data attached
            </span>
          )}
          <button
            onClick={handleExport}
            className="p-1.5 rounded-md hover:bg-secondary transition-colors"
            title="Export as text"
          >
            <Download className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-border/50 px-5 py-4 space-y-4 animate-fade-in">
          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-6 w-6 animate-spin text-primary/60" />
            </div>
          ) : detail ? (
            <>
              {/* Narrative */}
              {detail.narrative && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Executive Summary
                  </h4>
                  <div className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed bg-secondary/30 rounded-lg p-4">
                    {detail.narrative}
                  </div>
                </div>
              )}

              {/* KPI Summary from aggregated data */}
              {detail.aggregated_data?.kpi_summary && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Key Metrics
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <MetricCard
                      label="Revenue"
                      value={`£${Number((detail.aggregated_data.kpi_summary as any).total_revenue).toLocaleString()}`}
                      icon={TrendingUp}
                    />
                    <MetricCard
                      label="Orders"
                      value={Number((detail.aggregated_data.kpi_summary as any).total_orders).toLocaleString()}
                      icon={BarChart3}
                    />
                    <MetricCard
                      label="AOV"
                      value={`£${Number((detail.aggregated_data.kpi_summary as any).avg_order_value).toFixed(2)}`}
                      icon={FileText}
                    />
                    <MetricCard
                      label="Customers"
                      value={Number((detail.aggregated_data.kpi_summary as any).unique_customers).toLocaleString()}
                      icon={Package}
                    />
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Failed to load report details.</p>
          )}
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, icon: Icon }: { label: string; value: string; icon: any }) {
  return (
    <div className="rounded-lg bg-secondary/50 p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-3.5 w-3.5 text-primary/60" />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <span className="text-sm font-semibold text-foreground">{value}</span>
    </div>
  )
}

// ── Approvals Tab ────────────────────────────────────────

function ApprovalsTab() {
  const { data, isLoading, isError } = useRecommendations()
  const decideMutation = useDecideRecommendation()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary/60" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-critical/30 bg-critical/10 px-4 py-3">
        <p className="text-sm text-critical">Failed to load recommendations</p>
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="rounded-xl border border-border/50 bg-card p-8 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-muted-foreground/40" />
        <p className="mt-3 text-sm text-muted-foreground">
          No recommendations to review.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {data.pending_count > 0 && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
          <p className="text-sm text-warning">
            <Clock className="inline h-4 w-4 mr-1.5 -mt-0.5" />
            {data.pending_count} recommendation{data.pending_count > 1 ? 's' : ''} pending approval
          </p>
        </div>
      )}

      <div className="space-y-3">
        {data.items.map((rec) => (
          <RecommendationCard
            key={rec.id}
            rec={rec}
            onDecide={(action) => decideMutation.mutate({ id: rec.id, action })}
            isDeciding={decideMutation.isPending}
          />
        ))}
      </div>
    </div>
  )
}

function RecommendationCard({
  rec,
  onDecide,
  isDeciding,
}: {
  rec: RecommendationOut
  onDecide: (action: 'approve' | 'reject') => void
  isDeciding: boolean
}) {
  const typeIcons: Record<string, typeof Package> = {
    reorder: Package,
    markdown: TrendingUp,
    investigate: AlertTriangle,
  }
  const Icon = typeIcons[rec.action_type] ?? FileText

  const statusColors: Record<string, string> = {
    pending: 'bg-warning/20 text-warning',
    approved: 'bg-emerald-500/20 text-emerald-400',
    rejected: 'bg-critical/20 text-critical',
  }

  return (
    <div className="rounded-xl border border-border/50 bg-card px-5 py-4">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-secondary/80 p-2 mt-0.5">
          <Icon className="h-4 w-4 text-primary/70" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-foreground capitalize">
              {rec.action_type}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[rec.status] ?? ''}`}>
              {rec.status}
            </span>
          </div>
          {rec.product_name && (
            <p className="text-xs text-muted-foreground mb-1">
              {rec.sku} · {rec.product_name}
            </p>
          )}
          <p className="text-sm text-foreground/80">{rec.reason}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {format(new Date(rec.created_at), 'MMM dd, yyyy HH:mm')}
          </p>
        </div>
        {rec.status === 'pending' && (
          <div className="flex gap-2 shrink-0">
            <button
              id={`btn-approve-${rec.id}`}
              onClick={() => onDecide('approve')}
              disabled={isDeciding}
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/30 disabled:opacity-50 transition-colors"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Approve
            </button>
            <button
              id={`btn-reject-${rec.id}`}
              onClick={() => onDecide('reject')}
              disabled={isDeciding}
              className="inline-flex items-center gap-1 rounded-lg bg-critical/20 px-3 py-1.5 text-xs font-medium text-critical hover:bg-critical/30 disabled:opacity-50 transition-colors"
            >
              <XCircle className="h-3.5 w-3.5" />
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
