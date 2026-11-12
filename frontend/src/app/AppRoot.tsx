import type { ReactNode } from 'react'
import { GlassFilters } from '@/components/glass/GlassBackdrop'
import { LayoutProbe } from '@/__shared__/utils/LayoutProbe'
import { ToastProvider } from '@/components/ui/toast'
import { TooltipProvider } from '@/components/ui/overlays'

/**
 * App root: overlay providers and SVG filters for refraction.
 * Rendered once, outside the routes, so glass popovers/toasts
 * have access to portals and filters.
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
