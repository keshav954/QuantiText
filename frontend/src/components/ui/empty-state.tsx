/**
 * EmptyState — friendly placeholder when no data is available.
 * Used across tables, lists, and detail panes.
 */

import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title?: string
  description?: string
  children?: React.ReactNode
}

export function EmptyState({
  icon: Icon = Inbox,
  title = 'No data yet',
  description,
  children,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="p-4 bg-muted rounded-2xl mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <p className="font-medium text-foreground">{title}</p>
      {description && (
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  )
}
