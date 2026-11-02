import { forwardRef, useId, type InputHTMLAttributes, type LabelHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from 'react'
import { cn } from '@/__shared__/utils/cn'

const controlBase = [
  'w-full rounded-sm bg-surface-2 text-fg-primary placeholder:text-fg-tertiary',
  'border border-stroke-control transition-[border-color,box-shadow,background-color]',
  'duration-fast ease-out hover:bg-surface-3/60',
  'focus-visible:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)]',
  'disabled:cursor-not-allowed disabled:opacity-50',
  'aria-[invalid=true]:border-negative aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-[var(--negative-soft)]',
].join(' ')

export type InputSize = 'sm' | 'md' | 'lg'

const sizeMap: Record<InputSize, string> = {
  sm: 'h-[var(--control-h-sm)] px-3 text-label',
  md: 'h-[var(--control-h-md)] px-3 text-body',
  lg: 'h-[var(--control-h-lg)] px-4 text-body',
}

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  inputSize?: InputSize
  /** Иконка слева (по одной из lucide, 16–20 px) */
  iconLeft?: ReactNode
  /** Слот справа: единица валюты, кнопка очистки */
  slotRight?: ReactNode
  invalid?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, inputSize = 'md', iconLeft, slotRight, invalid, ...rest },
  ref,
) {
  if (!iconLeft && !slotRight) {
    return (
      <input
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(controlBase, sizeMap[inputSize], className)}
        {...rest}
      />
    )
  }

  return (
    <div className={cn('relative flex items-center', className)}>
      {iconLeft && (
        <span className="pointer-events-none absolute left-3 text-fg-tertiary" aria-hidden="true">
          {iconLeft}
        </span>
      )}
      <input
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(controlBase, sizeMap[inputSize], iconLeft && 'pl-9', slotRight && 'pr-12')}
        {...rest}
      />
      {slotRight && <span className="absolute right-2 flex items-center">{slotRight}</span>}
    </div>
  )
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, rows = 3, ...rest }, ref) {
    return (
      <textarea
        ref={ref}
        rows={rows}
        className={cn(controlBase, 'min-h-[80px] resize-y px-3 py-2 text-body', className)}
        {...rest}
      />
    )
  },
)

export const Label = forwardRef<HTMLLabelElement, LabelHTMLAttributes<HTMLLabelElement>>(
  function Label({ className, ...rest }, ref) {
    return <label ref={ref} className={cn('text-label font-medium text-fg-secondary', className)} {...rest} />
  },
)

export interface FieldProps {
  label: string
  htmlFor?: string
  hint?: string
  error?: string
  required?: boolean
  children: ReactNode
  className?: string
}

/** Обёртка поля: подпись + контрол + подсказка/ошибка с корректной связкой aria. */
export function Field({ label, htmlFor, hint, error, required, children, className }: FieldProps) {
  const autoId = useId()
  const id = htmlFor ?? autoId
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <Label htmlFor={id}>
        {label}
        {required && (
          <span className="ml-0.5 text-negative" aria-hidden="true">
            *
          </span>
        )}
      </Label>
      <div aria-describedby={describedBy}>{children}</div>
      {error ? (
        <p id={`${id}-error`} className="text-caption text-negative" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-caption text-fg-tertiary">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
