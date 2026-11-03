import {
  forwardRef,
  useId,
  type ComponentPropsWithoutRef,
  type ComponentType,
  type ElementRef,
  type ReactNode,
} from 'react'
import * as SwitchPrimitive from '@radix-ui/react-switch'
import * as CheckboxPrimitive from '@radix-ui/react-checkbox'
import * as SliderPrimitive from '@radix-ui/react-slider'
import * as ToggleGroupPrimitive from '@radix-ui/react-toggle-group'
import { Check, Minus } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { glassClass } from '@/components/glass/GlassSurface'

/* ------------------------------- Switch ---------------------------------- */

export interface SwitchProps extends ComponentPropsWithoutRef<typeof SwitchPrimitive.Root> {
  /** Подпись справа; клик по тексту переключает (label → button) */
  label?: ReactNode
}

export const Switch = forwardRef<ElementRef<typeof SwitchPrimitive.Root>, SwitchProps>(function Switch(
  { className, label, id, ...rest },
  ref,
) {
  const generatedId = useId()
  const switchId = id ?? generatedId

  const control = (
    <SwitchPrimitive.Root
      ref={ref}
      id={switchId}
      className={cn(
        'relative inline-flex h-5 w-8 shrink-0 items-center rounded-pill border border-transparent',
        'bg-surface-3 transition-colors duration-fast ease-out',
        'data-[state=checked]:bg-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-1)]',
        'disabled:cursor-not-allowed disabled:opacity-45',
        className,
      )}
      {...rest}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          'pointer-events-none block size-4 rounded-pill bg-white shadow-sm',
          'transition-transform duration-fast ease-out',
          'translate-x-[2px] data-[state=checked]:translate-x-[14px]',
          'motion-reduce:transition-none',
        )}
      />
    </SwitchPrimitive.Root>
  )

  if (!label) return control

  return (
    <div className={cn('flex items-start gap-2', className)}>
      {control}
      <label htmlFor={switchId} className="cursor-pointer text-label leading-5 text-fg-secondary">
        {label}
      </label>
    </div>
  )
})

/* ------------------------------ Checkbox --------------------------------- */

export interface CheckboxProps extends ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root> {
  /** Подпись справа; клик по тексту переключает (label → button) */
  label?: ReactNode
}

export const Checkbox = forwardRef<ElementRef<typeof CheckboxPrimitive.Root>, CheckboxProps>(
  function Checkbox({ className, label, id, ...rest }, ref) {
    const generatedId = useId()
    const checkboxId = id ?? generatedId

    const control = (
      <CheckboxPrimitive.Root
      ref={ref}
      id={checkboxId}
      className={cn(
        'grid size-[18px] shrink-0 place-items-center rounded-xs border border-stroke-strong bg-surface-2',
        'transition-colors duration-fast ease-out hover:border-accent',
        'data-[state=checked]:border-accent data-[state=checked]:bg-accent data-[state=checked]:text-accent-fg',
        'data-[state=indeterminate]:border-accent data-[state=indeterminate]:bg-accent data-[state=indeterminate]:text-accent-fg',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-1)]',
        'disabled:cursor-not-allowed disabled:opacity-45',
        className,
      )}
      {...rest}
    >
      <CheckboxPrimitive.Indicator className="grid place-items-center">
        {rest.checked === 'indeterminate' ? (
          <Minus className="size-3" aria-hidden="true" />
        ) : (
          <Check className="size-3" aria-hidden="true" strokeWidth={3} />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
    )

    if (!label) return control

    return (
      <div className={cn('flex items-start gap-2', className)}>
        {control}
        <label htmlFor={checkboxId} className="cursor-pointer text-label leading-[18px] text-fg-secondary">
          {label}
        </label>
      </div>
    )
  },
)

/* -------------------------------- Slider --------------------------------- */

export interface SliderProps
  extends Omit<ComponentPropsWithoutRef<typeof SliderPrimitive.Root>, 'value' | 'onValueChange'> {
  value: number[]
  onValueChange?: (value: number[]) => void
  /** Показывать значения над бегунками */
  showValues?: boolean
}

export const Slider = forwardRef<ElementRef<typeof SliderPrimitive.Root>, SliderProps>(
  function Slider({ className, value, onValueChange, showValues = false, ...rest }, ref) {
    return (
      <SliderPrimitive.Root
        ref={ref}
        value={value}
        onValueChange={onValueChange}
        className={cn('relative flex w-full touch-none select-none items-center py-2', className)}
        {...rest}
      >
        <SliderPrimitive.Track className="relative h-1 w-full grow overflow-hidden rounded-pill bg-surface-3">
          <SliderPrimitive.Range className="absolute h-full bg-accent" />
        </SliderPrimitive.Track>
        {value.map((_, index) => (
          <SliderPrimitive.Thumb
            key={index}
            aria-label={rest['aria-label'] ?? `Значение ${index + 1}`}
            className={cn(
              'group relative block size-5 rounded-pill border-2 border-accent bg-white shadow-sm',
              'transition-transform duration-fast ease-out hover:scale-105 active:scale-95',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)] focus-visible:ring-offset-2',
              'motion-reduce:transition-none motion-reduce:hover:scale-100',
            )}
          >
            {showValues && (
              <span className="pointer-events-none absolute -top-7 left-1/2 -translate-x-1/2 rounded-xs bg-fg-primary px-1.5 py-0.5 text-caption text-bg-base opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                {value[index]}
              </span>
            )}
          </SliderPrimitive.Thumb>
        ))}
      </SliderPrimitive.Root>
    )
  },
)

/* --------------------------- Segmented control --------------------------- */

export interface SegmentedControlItem {
  value: string
  /** Текстовая подпись; служит доступным именем и в режиме «только иконка» */
  label: string
  /** Необязательная иконка слева от подписи (в iconOnly — вместо неё) */
  icon?: ComponentType<{ className?: string }>
  disabled?: boolean
}

export interface SegmentedControlProps {
  items: SegmentedControlItem[]
  value?: string
  onValueChange?: (value: string) => void
  'aria-label'?: string
  className?: string
  /**
   * Показывать только иконки. Текстовая подпись остаётся доступной через
   * aria-label сегмента — так контрол помещается в узкую строку и не
   * обрезается до безымянных пиктограмм.
   */
  iconOnly?: boolean
}

/**
 * Сегментированный контрол на стекле: индикатор — пилюля, переезжающая
 * CSS-переходом (не layout-анимация, чтобы не дёргать reflow в списках).
 */
export function SegmentedControl({ items, className, iconOnly = false, ...rest }: SegmentedControlProps) {
  return (
    <ToggleGroupPrimitive.Root
      type="single"
      className={cn(
        glassClass({ level: 'sm' }),
        'relative inline-flex items-center gap-1 rounded-pill p-1',
        className,
      )}
      {...rest}
    >
      {items.map((item) => {
        const Icon = item.icon
        return (
          <ToggleGroupPrimitive.Item
            key={item.value}
            value={item.value}
            disabled={item.disabled}
            // В iconOnly текст скрыт, поэтому доступное имя задаётся явно.
            aria-label={iconOnly ? item.label : undefined}
            title={iconOnly ? item.label : undefined}
            className={cn(
              'relative z-10 inline-flex items-center justify-center gap-1.5 rounded-pill text-label font-medium text-fg-secondary',
              iconOnly ? 'size-8 p-0' : 'px-3 py-1',
              'transition-colors duration-base ease-out',
              'hover:text-fg-primary',
              'data-[state=on]:bg-surface-1 data-[state=on]:text-fg-primary data-[state=on]:shadow-sm',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)]',
              'disabled:cursor-not-allowed disabled:opacity-45',
            )}
          >
            {Icon && <Icon className="size-4 shrink-0" />}
            {!iconOnly && item.label}
          </ToggleGroupPrimitive.Item>
        )
      })}
    </ToggleGroupPrimitive.Root>
  )
}
