/**
 * Alerts page — anomaly feed with severity badges, dismiss action, and detection trigger.
 * Phase 6.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  X,
  CheckCheck,
  Zap,
  Eye,
  EyeOff,
} from 'lucide-react'
import {
  fetchAlerts,
  fetchAnomalies,
  dismissAnomaly,
  markAlertsRead,
  triggerDetection,
  type AlertItem,
  type AnomalyItem,
} from '@/api/anomaly'

const SEVERITY_CONFIG = {
  critical: {
    icon: AlertCircle,
    class: 'text-red-400 bg-red-400/10 border-red-400/20',
    dot: 'bg-red-400',
    label: 'Critical',
  },
  warning: {
    icon: AlertTriangle,
    class: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    dot: 'bg-amber-400',
    label: 'Warning',
  },
  info: {
    icon: Info,
    class: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    dot: 'bg-blue-400',
    label: 'Info',
  },
}

const DETECTOR_LABELS: Record<string, string> = {
  zscore: 'Z-Score',
  iforest: 'Isolation Forest',
  data_quality: 'Data Quality',
}

const ANOMALY_TYPE_LABELS: Record<string, string> = {
  revenue_spike: 'Revenue Spike',
  revenue_drop: 'Revenue Drop',
  zero_sales: 'Zero Sales Streak',
  inventory_critical: 'Critical Stock',
}

function AlertCard({
  alert,
  onMarkRead,
}: {
  alert: AlertItem
  onMarkRead: (id: string) => void
}) {
  const cfg = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.info
  const Icon = cfg.icon

  return (
    <div
      className={`rounded-2xl border p-4 transition-all ${
        alert.is_read ? 'opacity-60' : ''
      } ${cfg.class}`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground leading-snug">{alert.title}</h3>
            <div className="flex items-center gap-1 shrink-0">
              {!alert.is_read && (
                <span className={`w-2 h-2 rounded-full ${cfg.dot} animate-pulse`} />
              )}
              <button
                id={`mark-read-${alert.id}`}
                onClick={() => onMarkRead(alert.id)}
                className="p-1 rounded hover:bg-white/10 transition-colors"
                title="Mark as read"
              >
                <CheckCheck className="h-3.5 w-3.5 opacity-60 hover:opacity-100" />
              </button>
            </div>
          </div>
          {alert.description && (
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              {alert.description}
            </p>
          )}
          <p className="text-xs text-muted-foreground/60 mt-2">
            {new Date(alert.created_at).toLocaleString('en-GB', {
              dateStyle: 'medium',
              timeStyle: 'short',
            })}
          </p>
        </div>
      </div>
    </div>
  )
}

function AnomalyRow({
  anomaly,
  onDismiss,
}: {
  anomaly: AnomalyItem
  onDismiss: (id: string) => void
}) {
  const severityColor =
    anomaly.severity_score >= 0.75
      ? 'text-red-400'
      : anomaly.severity_score >= 0.5
      ? 'text-amber-400'
      : 'text-blue-400'

  return (
    <tr className="border-b border-border/50 hover:bg-muted/20 transition-colors group">
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {new Date(anomaly.detected_date).toLocaleDateString('en-GB', {
          day: 'numeric', month: 'short',
        })}
      </td>
      <td className="px-4 py-3 text-foreground font-medium text-sm">
        {anomaly.product_name ?? '–'}
        {anomaly.sku && (
          <span className="text-xs text-muted-foreground ml-1 font-mono">({anomaly.sku})</span>
        )}
      </td>
      <td className="px-4 py-3">
        <span className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground">
          {ANOMALY_TYPE_LABELS[anomaly.anomaly_type] ?? anomaly.anomaly_type}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {DETECTOR_LABELS[anomaly.detector] ?? anomaly.detector}
      </td>
      <td className={`px-4 py-3 font-bold text-sm ${severityColor}`}>
        {(anomaly.severity_score * 100).toFixed(0)}%
      </td>
      <td className="px-4 py-3 text-muted-foreground text-sm">
        {anomaly.estimated_impact !== null
          ? `£${anomaly.estimated_impact.toFixed(0)}`
          : '–'}
      </td>
      <td className="px-4 py-3">
        <button
          id={`dismiss-${anomaly.id}`}
          onClick={() => onDismiss(anomaly.id)}
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground"
          title="Dismiss anomaly"
        >
          <X className="h-4 w-4" />
        </button>
      </td>
    </tr>
  )
}

export function AlertsPage() {
  const [activeTab, setActiveTab] = useState<'alerts' | 'anomalies'>('alerts')
  const [onlyUnread, setOnlyUnread] = useState(false)
  const queryClient = useQueryClient()

  const alertsQuery = useQuery({
    queryKey: ['alerts', onlyUnread],
    queryFn: () => fetchAlerts({ only_unread: onlyUnread, limit: 50 }),
    refetchInterval: 30_000, // refresh every 30s
  })

  const anomaliesQuery = useQuery({
    queryKey: ['anomalies'],
    queryFn: () => fetchAnomalies({ only_active: true, limit: 100 }),
    enabled: activeTab === 'anomalies',
  })

  const dismissMutation = useMutation({
    mutationFn: dismissAnomaly,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const markReadMutation = useMutation({
    mutationFn: (ids: string[]) => markAlertsRead(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  })

  const detectMutation = useMutation({
    mutationFn: () => triggerDetection(30),
    onSuccess: (_data) => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const alerts = alertsQuery.data?.items ?? []
  const anomalies = anomaliesQuery.data?.items ?? []
  const unreadCount = alertsQuery.data?.unread_count ?? 0

  const handleMarkAllRead = () => {
    const unread = alerts.filter((a) => !a.is_read).map((a) => a.id)
    if (unread.length) markReadMutation.mutate(unread)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <Bell className="h-6 w-6 text-primary" />
            Alerts & Anomalies
            {unreadCount > 0 && (
              <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Z-Score · Isolation Forest · Data Quality detectors
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            id="trigger-detection-btn"
            onClick={() => detectMutation.mutate()}
            disabled={detectMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Zap className={`h-4 w-4 ${detectMutation.isPending ? 'animate-spin' : ''}`} />
            {detectMutation.isPending ? 'Running…' : 'Run Detection'}
          </button>
        </div>
      </div>

      {/* Detection result banner */}
      {detectMutation.isSuccess && (
        <div className="bg-emerald-400/10 border border-emerald-400/20 rounded-xl p-3 text-sm text-emerald-400 flex items-center gap-2">
          <CheckCheck className="h-4 w-4" />
          Detection complete: {detectMutation.data.new_anomalies} new anomalies,{' '}
          {detectMutation.data.new_alerts} new alerts · {detectMutation.data.period_checked}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-muted p-1 rounded-xl w-fit">
        <button
          id="tab-alerts"
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'alerts'
              ? 'bg-card text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Alerts
          {unreadCount > 0 && (
            <span className="ml-1.5 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </button>
        <button
          id="tab-anomalies"
          onClick={() => setActiveTab('anomalies')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'anomalies'
              ? 'bg-card text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Anomalies
          {anomaliesQuery.data?.total !== undefined && (
            <span className="ml-1.5 text-xs text-muted-foreground">
              ({anomaliesQuery.data.total})
            </span>
          )}
        </button>
      </div>

      {/* Alerts tab */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button
              id="toggle-unread-btn"
              onClick={() => setOnlyUnread((v) => !v)}
              className={`flex items-center gap-2 text-sm transition-colors ${
                onlyUnread ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {onlyUnread ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {onlyUnread ? 'Show all' : 'Unread only'}
            </button>
            {unreadCount > 0 && (
              <button
                id="mark-all-read-btn"
                onClick={handleMarkAllRead}
                disabled={markReadMutation.isPending}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {alertsQuery.isLoading ? (
            <div className="grid gap-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 bg-muted animate-pulse rounded-2xl" />
              ))}
            </div>
          ) : alerts.length === 0 ? (
            <div className="bg-card border border-border rounded-2xl p-12 text-center">
              <Bell className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-foreground font-medium">No alerts</p>
              <p className="text-muted-foreground text-sm mt-1">
                {onlyUnread ? 'All caught up!' : 'Run anomaly detection to generate alerts.'}
              </p>
            </div>
          ) : (
            <div className="grid gap-3">
              {alerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onMarkRead={(id) => markReadMutation.mutate([id])}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Anomalies tab */}
      {activeTab === 'anomalies' && (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          {anomaliesQuery.isLoading ? (
            <div className="p-6 space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-muted animate-pulse rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-muted/30">
                  <tr>
                    {['Date', 'Product', 'Type', 'Detector', 'Severity', 'Impact', ''].map(
                      (h) => (
                        <th
                          key={h}
                          className="text-left text-xs text-muted-foreground px-4 py-3 font-medium"
                        >
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {anomalies.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-muted-foreground text-sm">
                        No active anomalies. Run detection to find issues.
                      </td>
                    </tr>
                  ) : (
                    anomalies.map((a) => (
                      <AnomalyRow
                        key={a.id}
                        anomaly={a}
                        onDismiss={(id) => dismissMutation.mutate(id)}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
