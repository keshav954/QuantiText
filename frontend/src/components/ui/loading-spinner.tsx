/**
 * LoadingSpinner — consistent loading indicator used across the app.
 */

import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  /** Display size in Tailwind units (e.g. '5', '8', '12'). Default '6'. */
  size?: string
  /** Optional label displayed below the spinner. */
  label?: string
  /** Fill the parent container and center. */
  fullPage?: boolean
  className?: string
}

export function LoadingSpinner({
  size = '6',
  label,
  fullPage = false,
  className,
}: LoadingSpinnerProps) {
  const spinner = (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      <Loader2 className={`h-${size} w-${size} animate-spin text-primary`} />
      {label && <p className="text-sm text-muted-foreground">{label}</p>}
    </div>
  )

  if (fullPage) {
    return (
      <div className="flex items-center justify-center min-h-[200px] w-full">
        {spinner}
      </div>
    )
  }

  return spinner
}
