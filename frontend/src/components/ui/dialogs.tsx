import type { ComponentPropsWithoutRef, ElementRef, ReactNode } from 'react'
import { forwardRef } from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { glassClass } from '@/components/glass/GlassSurface'
import { Button } from './button'

/* --------------------------------- Dialog -------------------------------- */

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

const overlayClass = [
  'fixed inset-0 z-[var(--z-dialog)] bg-[rgba(6,10,9,.42)]',
  'backdrop-blur-[2px]',
  'data-[state=open]:animate-in data-[state=open]:fade-in-0',
  'data-[state=closed]:animate-out data-[state=closed]:fade-out-0',
].join(' ')

export const DialogOverlay = forwardRef<
  ElementRef<typeof DialogPrimitive.Overlay>,
  ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(function DialogOverlay({ className, ...rest }, ref) {
  return <DialogPrimitive.Overlay ref={ref} className={cn(overlayClass, className)} {...rest} />
})

export interface DialogContentProps extends ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  title: string
  description?: string
  /** Скрыть кнопку закрытия (например, в двухколоночной форме со своими действиями) */
  hideClose?: boolean
  footer?: ReactNode
}

/**
 * Стеклянная панель диалога. Радиус внешний = --glass-radius-lg,
 * у внутренних блоков считается по правилу «внешний − padding».
 */
export const DialogContent = forwardRef<ElementRef<typeof DialogPrimitive.Content>, DialogContentProps>(
  function DialogContent(
    { className, children, title, description, hideClose = false, footer, ...rest },
    ref,
  ) {
    return (
      <DialogPrimitive.Portal>
        <DialogOverlay />
        <DialogPrimitive.Content
          ref={ref}
          className={cn(
            glassClass({ level: 'lg' }),
            'fixed left-1/2 top-1/2 z-[var(--z-dialog)] w-[min(92vw,var(--dialog-w,560px))]',
            '-translate-x-1/2 -translate-y-1/2 overflow-hidden p-6 text-fg-primary',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[.97]',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-[.97]',
            'motion-reduce:data-[state=open]:zoom-in-100 motion-reduce:data-[state=closed]:zoom-out-100',
            className,
          )}
          {...rest}
        >
          <DialogPrimitive.Title className="text-title font-semibold tracking-snug">
            {title}
          </DialogPrimitive.Title>
          {description ? (
            <DialogPrimitive.Description className="mt-1 text-label text-fg-secondary">
              {description}
            </DialogPrimitive.Description>
          ) : (
            <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
          )}
          <div className="mt-5">{children}</div>
          {footer && <div className="mt-6 flex items-center justify-end gap-2">{footer}</div>}
          {!hideClose && (
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon-sm" className="absolute right-4 top-4" aria-label="Закрыть">
                <X className="size-4" aria-hidden="true" />
              </Button>
            </DialogPrimitive.Close>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    )
  },
)

/* ---------------------------------- Sheet -------------------------------- */

export const Sheet = DialogPrimitive.Root
export const SheetTrigger = DialogPrimitive.Trigger
export const SheetClose = DialogPrimitive.Close

export interface SheetContentProps extends ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  title: string
  side?: 'left' | 'right' | 'bottom'
}

/**
 * Sheet — стеклянная панель, выезжающая с края. На мобиле используется для
 * фильтров (side="left") и меню «Ещё» (side="bottom").
 */
export const SheetContent = forwardRef<ElementRef<typeof DialogPrimitive.Content>, SheetContentProps>(
  function SheetContent({ className, children, title, side = 'left', ...rest }, ref) {
    const sideClass =
      side === 'left'
        ? 'left-0 top-0 h-dvh w-[min(86vw,320px)] border-r data-[state=open]:slide-in-from-left data-[state=closed]:slide-out-to-left'
        : side === 'right'
          ? 'right-0 top-0 h-dvh w-[min(86vw,360px)] border-l data-[state=open]:slide-in-from-right data-[state=closed]:slide-out-to-right'
          : 'inset-x-0 bottom-0 max-h-[82dvh] rounded-b-none border-t pb-[env(safe-area-inset-bottom)] data-[state=open]:slide-in-from-bottom data-[state=closed]:slide-out-to-bottom'

    return (
      <DialogPrimitive.Portal>
        <DialogOverlay />
        <DialogPrimitive.Content
          ref={ref}
          className={cn(
            glassClass(),
            'fixed z-[var(--z-sheet)] overflow-y-auto p-4 text-fg-primary',
            sideClass,
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:duration-slow',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:duration-base',
            className,
          )}
          {...rest}
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <DialogPrimitive.Title className="text-headline font-semibold">{title}</DialogPrimitive.Title>
            <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Закрыть">
                <X className="size-4" aria-hidden="true" />
              </Button>
            </DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    )
  },
)
