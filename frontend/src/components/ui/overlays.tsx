import type { ComponentPropsWithoutRef, ElementRef, ReactNode } from 'react'
import { forwardRef } from 'react'
import * as SelectPrimitive from '@radix-ui/react-select'
import * as PopoverPrimitive from '@radix-ui/react-popover'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import * as DropdownPrimitive from '@radix-ui/react-dropdown-menu'
import { Check, ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { glassClass } from '@/components/glass/GlassSurface'

/**
 * Стеклянные оверлеи. Правило: внутри стекла не размещаем ещё одно стекло,
 * поэтому элементы меню используют surface-2/3, а не backdrop-filter.
 */

const glassContent = cn(
  glassClass({ level: 'sm' }),
  'z-[var(--z-popover)] max-w-[calc(100vw-1.5rem)] overflow-hidden p-1 text-fg-primary ',
  'data-[state=open]:animate-in data-[state=closed]:animate-out ',
  'data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0',
)

const itemBase =
  'relative flex cursor-default select-none items-center gap-2 rounded-xs px-2 py-1.5 text-label outline-none ' +
  'data-[highlighted]:bg-surface-2 data-[highlighted]:text-fg-primary ' +
  'data-[disabled]:pointer-events-none data-[disabled]:opacity-45'

/* -------------------------------- Select --------------------------------- */

export const Select = SelectPrimitive.Root
export const SelectGroup = SelectPrimitive.Group
export const SelectValue = SelectPrimitive.Value

export const SelectTrigger = forwardRef<
  ElementRef<typeof SelectPrimitive.Trigger>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(function SelectTrigger({ className, children, ...rest }, ref) {
  return (
    <SelectPrimitive.Trigger
      ref={ref}
      className={cn(
        'flex h-[var(--control-h-md)] w-full items-center justify-between gap-2 rounded-sm',
        'border border-stroke-control bg-surface-2 px-3 text-body text-fg-primary',
        'transition-colors duration-fast ease-out hover:bg-surface-3/60',
        'data-[placeholder]:text-fg-tertiary',
        'focus-visible:outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)]',
        'disabled:cursor-not-allowed disabled:opacity-45',
        className,
      )}
      {...rest}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="size-4 shrink-0 text-fg-tertiary" aria-hidden="true" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
})

export const SelectContent = forwardRef<
  ElementRef<typeof SelectPrimitive.Content>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(function SelectContent({ className, children, position = 'popper', ...rest }, ref) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        ref={ref}
        position={position}
        sideOffset={6}
        className={cn(glassContent, 'min-w-[var(--radix-select-trigger-width)]', className)}
        {...rest}
      >
        <SelectPrimitive.Viewport className="max-h-72 overflow-y-auto">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
})

export const SelectItem = forwardRef<
  ElementRef<typeof SelectPrimitive.Item>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(function SelectItem({ className, children, ...rest }, ref) {
  return (
    <SelectPrimitive.Item ref={ref} className={cn(itemBase, 'pr-7', className)} {...rest}>
      <SelectPrimitive.ItemIndicator className="absolute right-2">
        <Check className="size-3.5" aria-hidden="true" />
      </SelectPrimitive.ItemIndicator>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
})

export const SelectLabel = forwardRef<
  ElementRef<typeof SelectPrimitive.Label>,
  ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(function SelectLabel({ className, ...rest }, ref) {
  return (
    <SelectPrimitive.Label
      ref={ref}
      className={cn('px-2 py-1.5 text-overline uppercase text-fg-tertiary', className)}
      {...rest}
    />
  )
})

/** Готовый «компактный» селект для панели фильтров: иконка + значение + шеврон. */
export interface FilterSelectOption {
  value: string
  label: string
  /** Вложенный уровень: подкатегории показываются с отступом и точкой цвета */
  indent?: boolean
  dotColor?: string
}

export interface FilterSelectProps {
  icon?: ReactNode
  value: string
  options: FilterSelectOption[]
  /** Сгруппированный список: заголовок группы — родительская категория */
  groups?: Array<{ label: string; options: FilterSelectOption[] }>
  /** Не вызывается, пока селект заблокирован (``disabled``) */
  onValueChange?: (value: string) => void
  ariaLabel: string
  className?: string
  /** Заблокированный селект: значение видно, но изменить его нельзя */
  disabled?: boolean
  /**
   * Что показывать в закрытом триггере. По умолчанию Radix подставляет текст
   * выбранной опции; если подпись опции длиннее кода, стоит задать своё значение
   * (например, только код валюты), чтобы оно не обрезалось в узком триггере.
   */
  renderValue?: ReactNode
}

export function FilterSelect({
  icon,
  value,
  options,
  groups,
  onValueChange,
  ariaLabel,
  className,
  renderValue,
  disabled = false,
}: FilterSelectProps) {
  const renderOption = (option: FilterSelectOption) => (
    <SelectItem key={option.value} value={option.value}>
      <span className={cn('flex items-center gap-1.5', option.indent && 'pl-3')}>
        {option.dotColor && (
          <span className="size-1.5 rounded-pill" style={{ backgroundColor: option.dotColor }} aria-hidden="true" />
        )}
        {option.label}
      </span>
    </SelectItem>
  )

  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger
        aria-label={ariaLabel}
        className={cn('h-[34px] text-label', disabled && 'cursor-not-allowed opacity-60', className)}
      >
        <span className="flex min-w-0 items-center gap-2">
          {icon && <span className="text-fg-tertiary">{icon}</span>}
          <SelectValue>{renderValue}</SelectValue>
        </span>
      </SelectTrigger>
      <SelectContent>
        {groups
          ? groups.map((group) => (
              <SelectGroup key={group.label}>
                <SelectLabel>{group.label}</SelectLabel>
                {group.options.map(renderOption)}
              </SelectGroup>
            ))
          : options.map(renderOption)}
      </SelectContent>
    </Select>
  )
}

/* ------------------------------- Popover --------------------------------- */

export const Popover = PopoverPrimitive.Root
export const PopoverTrigger = PopoverPrimitive.Trigger
export const PopoverAnchor = PopoverPrimitive.Anchor

export const PopoverContent = forwardRef<
  ElementRef<typeof PopoverPrimitive.Content>,
  ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>
>(function PopoverContent({ className, align = 'center', sideOffset = 8, ...rest }, ref) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        ref={ref}
        align={align}
        sideOffset={sideOffset}
        collisionPadding={12}
        className={cn(glassContent, 'w-72 p-3', className)}
        {...rest}
      />
    </PopoverPrimitive.Portal>
  )
})

/* ------------------------------- Tooltip --------------------------------- */

export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export const TooltipContent = forwardRef<
  ElementRef<typeof TooltipPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(function TooltipContent({ className, sideOffset = 6, ...rest }, ref) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        ref={ref}
        sideOffset={sideOffset}
        className={cn(
          glassClass({ level: 'sm' }),
          'z-[var(--z-popover)] max-w-64 rounded-xs px-2 py-1 text-caption text-fg-primary',
          'data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0',
          className,
        )}
        {...rest}
      />
    </TooltipPrimitive.Portal>
  )
})

/* ----------------------------- DropdownMenu ------------------------------ */

export const DropdownMenu = DropdownPrimitive.Root
export const DropdownMenuTrigger = DropdownPrimitive.Trigger
export const DropdownMenuGroup = DropdownPrimitive.Group

export const DropdownMenuContent = forwardRef<
  ElementRef<typeof DropdownPrimitive.Content>,
  ComponentPropsWithoutRef<typeof DropdownPrimitive.Content>
>(function DropdownMenuContent({ className, align = 'end', sideOffset = 8, ...rest }, ref) {
  return (
    <DropdownPrimitive.Portal>
      <DropdownPrimitive.Content
        ref={ref}
        align={align}
        sideOffset={sideOffset}
        collisionPadding={12}
        className={cn(glassContent, 'min-w-52', className)}
        {...rest}
      />
    </DropdownPrimitive.Portal>
  )
})

export const DropdownMenuItem = forwardRef<
  ElementRef<typeof DropdownPrimitive.Item>,
  ComponentPropsWithoutRef<typeof DropdownPrimitive.Item>
>(function DropdownMenuItem({ className, ...rest }, ref) {
  return <DropdownPrimitive.Item ref={ref} className={cn(itemBase, className)} {...rest} />
})

export const DropdownMenuCheckboxItem = DropdownPrimitive.CheckboxItem
export const DropdownMenuRadioItem = DropdownPrimitive.RadioItem

export const DropdownMenuSeparator = forwardRef<
  ElementRef<typeof DropdownPrimitive.Separator>,
  ComponentPropsWithoutRef<typeof DropdownPrimitive.Separator>
>(function DropdownMenuSeparator({ className, ...rest }, ref) {
  return (
    <DropdownPrimitive.Separator ref={ref} className={cn('my-1 h-px bg-stroke-subtle', className)} {...rest} />
  )
})

export const DropdownMenuLabel = forwardRef<
  ElementRef<typeof DropdownPrimitive.Label>,
  ComponentPropsWithoutRef<typeof DropdownPrimitive.Label>
>(function DropdownMenuLabel({ className, ...rest }, ref) {
  return (
    <DropdownPrimitive.Label
      ref={ref}
      className={cn('px-2 py-1.5 text-overline uppercase text-fg-tertiary', className)}
      {...rest}
    />
  )
})

export function DropdownChevron() {
  return <ChevronRight className="ml-auto size-3.5 text-fg-tertiary" aria-hidden="true" />
}
