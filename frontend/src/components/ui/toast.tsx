import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import * as ToastPrimitive from '@radix-ui/react-toast'
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { glassClass } from '@/components/glass/GlassSurface'

type ToastTone = 'info' | 'success' | 'error'

interface ToastItem {
  id: number
  title: string
  description?: string
  tone: ToastTone
}

interface ToastApi {
  toast: (input: { title: string; description?: string; tone?: ToastTone }) => void
}

const ToastContext = createContext<ToastApi | null>(null)

const toneIcon: Record<ToastTone, ReactNode> = {
  info: <Info className="size-4 text-accent" aria-hidden="true" />,
  success: <CheckCircle2 className="size-4 text-positive" aria-hidden="true" />,
  error: <AlertTriangle className="size-4 text-negative" aria-hidden="true" />,
}

/** Glass toasts at the bottom right; at most 3 at a time. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const toast = useCallback<ToastApi['toast']>(({ title, description, tone = 'info' }) => {
    setItems((prev) => [...prev.slice(-2), { id: Date.now() + Math.random(), title, description, tone }])
  }, [])

  const value = useMemo<ToastApi>(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider swipeDirection="right" duration={4200}>
        {children}
        {items.map((item) => (
          <ToastPrimitive.Root
            key={item.id}
            data-toast="true"
            onOpenChange={(open) => {
              if (!open) setItems((prev) => prev.filter((entry) => entry.id !== item.id))
            }}
            className={cn(
              glassClass({ level: 'sm', glow: true }),
              'fixed bottom-4 right-4 z-[var(--z-toast)] flex w-[min(92vw,360px)] items-start gap-3 p-3',
              'data-[state=open]:animate-in data-[state=open]:slide-in-from-bottom-2 data-[state=open]:fade-in-0',
              'data-[state=closed]:animate-out data-[state=closed]:fade-out-0',
              'data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)]',
            )}
            style={{ bottom: `calc(1rem + ${items.indexOf(item) * 76}px)` }}
            onPointerMove={(event) => {
              // Same cursor glint as the header: the position is passed via CSS variables
              const rect = event.currentTarget.getBoundingClientRect()
              event.currentTarget.style.setProperty('--glass-mx', `${event.clientX - rect.left}px`)
              event.currentTarget.style.setProperty('--glass-my', `${event.clientY - rect.top}px`)
            }}
          >
            <span className="mt-0.5">{toneIcon[item.tone]}</span>
            <div className="min-w-0 flex-1">
              <ToastPrimitive.Title className="text-label font-medium text-fg-primary">
                {item.title}
              </ToastPrimitive.Title>
              {item.description && (
                <ToastPrimitive.Description className="mt-0.5 text-caption text-fg-secondary">
                  {item.description}
                </ToastPrimitive.Description>
              )}
            </div>
            <ToastPrimitive.Close className="rounded-xs p-1 text-fg-tertiary hover:text-fg-primary" aria-label="Закрыть">
              <X className="size-3.5" aria-hidden="true" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-[var(--z-toast)] m-0 flex list-none flex-col gap-2 p-0" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast должен вызываться внутри ToastProvider')
  return context
}
