/**
 * PageHeader — reusable page title bar with icon, description, and optional action slot.
 * Used across all feature pages for consistent heading structure.
 */

import type { LucideIcon } from 'lucide-react'

interface PageHeaderProps {
  icon?: LucideIcon
  title: string
  description?: string
  children?: React.ReactNode
}

export function PageHeader({ icon: Icon, title, description, children }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
          {Icon && <Icon className="h-6 w-6 text-primary" />}
          {title}
        </h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  )
}
