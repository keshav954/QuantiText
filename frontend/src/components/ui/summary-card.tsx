/**
 * SummaryCard — metric card with icon, label, value, and optional subtitle.
 * Extracted from inventory, alerts, and forecast pages where this pattern repeats.
 */

interface SummaryCardProps {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  sub?: string
  color?: string
}

export function SummaryCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'text-foreground',
}: SummaryCardProps) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex items-center gap-4">
      <div className="p-3 bg-muted rounded-xl">
        <Icon className={`h-5 w-5 ${color}`} />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}
