import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { glassClass } from '@/components/glass/GlassSurface'

const buttonVariants = cva(
  [
    'inline-flex select-none items-center justify-center gap-2 whitespace-nowrap',
    'font-medium transition-[background-color,box-shadow,transform,color] duration-fast ease-out',
    'active:scale-[.975] disabled:pointer-events-none disabled:opacity-45',
    'motion-reduce:active:scale-100',
  ],
  {
    variants: {
      variant: {
        primary: 'bg-accent-fill text-accent-fg btn-primary-gloss hover:bg-accent-fill-hover',
        glass: `${glassClass({ level: 'sm' })} text-fg-primary hover:brightness-[1.04]`,
        subtle: 'bg-surface-2 text-fg-primary hover:bg-surface-3',
        ghost: 'text-fg-secondary hover:bg-surface-2 hover:text-fg-primary',
        danger: 'bg-negative-soft text-negative hover:brightness-[0.97]',
        link: 'text-accent underline-offset-4 hover:underline px-0',
      },
      size: {
        sm: 'h-[var(--control-h-sm)] px-3 text-label rounded-md',
        md: 'h-[var(--control-h-md)] px-4 text-body rounded-md',
        lg: 'h-[var(--control-h-lg)] px-5 text-body rounded-md',
        icon: 'h-[var(--control-h-md)] w-[var(--control-h-md)] rounded-md',
        'icon-sm': 'h-[var(--control-h-sm)] w-[var(--control-h-sm)] rounded-sm',
      },
      pill: { true: 'rounded-pill', false: '' },
      block: { true: 'w-full', false: '' },
    },
    defaultVariants: { variant: 'primary', size: 'md', pill: false, block: false },
  },
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Shows a spinner and blocks repeated presses */
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, pill, block, loading = false, disabled, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={rest.type ?? 'button'}
      className={cn(buttonVariants({ variant, size, pill, block }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  )
})

export { buttonVariants }
