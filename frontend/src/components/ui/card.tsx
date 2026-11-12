import type { ReactNode } from 'react'
import { cn } from '@/__shared__/utils/cn'

/**
 * Content card. IMPORTANT: no glass — content doesn't get backdrop-filter.
 * Outer radius 18, inner blocks use --radius-nest-3.
 */
export function Card({
  children,
  className,
  as: Tag = 'section',
  ...rest
}: {
  children: ReactNode
  className?: string
  as?: 'section' | 'div' | 'article'
} & Omit<React.ComponentPropsWithoutRef<'section'>, 'children' | 'className'>) {
  return (
    <Tag
      {...rest}
      className={cn(
        'content-card p-5',
        className,
      )}
    >
      {children}
    </Tag>
  )
}

export function CardHeader({
  title,
  subtitle,
  actions,
  className,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-wrap items-start justify-between gap-3', className)}>
      <div className="min-w-0">
        <h2 className="text-headline font-semibold tracking-snug text-fg-primary">{title}</h2>
        {subtitle && <p className="mt-0.5 text-caption text-fg-tertiary">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-1">{actions}</div>}
    </div>
  )
}

export function CardMetric({
  label,
  children,
  className,
}: {
  label?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {label && <span className="text-caption text-fg-tertiary">{label}</span>}
      {children}
    </div>
  )
}
