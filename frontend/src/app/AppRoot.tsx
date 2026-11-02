import type { ReactNode } from 'react'
import { GlassFilters } from '@/components/glass/GlassBackdrop'
import { LayoutProbe } from '@/__shared__/utils/LayoutProbe'
import { ToastProvider } from '@/components/ui/toast'
import { TooltipProvider } from '@/components/ui/overlays'

/**
 * Корень приложения: провайдеры оверлеев и SVG-фильтры для рефракции.
 * Рендерится один раз, вне роутов — чтобы стеклянные поповеры/тосты
 * имели доступ к порталам и фильтрам.
 */
export function AppRoot({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider delayDuration={300} skipDelayDuration={120}>
      <ToastProvider>
        <GlassFilters />
        {children}
      {typeof window !== 'undefined' &&
        new URLSearchParams(window.location.search).get('debug') === 'layout' && <LayoutProbe />}
      </ToastProvider>
    </TooltipProvider>
  )
}
