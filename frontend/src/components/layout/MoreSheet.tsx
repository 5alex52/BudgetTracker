import type { ReactNode } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, Settings, TrendingUp } from 'lucide-react'
import { useI18n } from '@/i18n'
import { Sheet, SheetContent } from '@/components/ui/dialogs'
import { LanguageSwitcher } from './Switchers'

/** Нижний стеклянный Sheet для «Ещё» на мобиле. */
export function MoreSheet({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const { t } = useI18n()
  const navigate = useNavigate()

  const go = (to: string) => {
    setOpen(false)
    navigate(to)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex flex-1 min-w-[4rem] flex-col items-center justify-center gap-1 rounded-md text-[11px] leading-4 text-fg-secondary transition-colors hover:text-fg-primary"
      >
        {children}
      </button>
      <SheetContent side="bottom" title={t('common.more')}>
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={() => go('/investments')}
            className="flex h-12 items-center gap-3 rounded-md px-3 text-body text-fg-primary hover:bg-surface-2"
          >
            <TrendingUp className="size-5 text-fg-tertiary" aria-hidden="true" />
            {t('nav.investments')}
          </button>
          <button
            type="button"
            onClick={() => go('/imports')}
            className="flex h-12 items-center gap-3 rounded-md px-3 text-body text-fg-primary hover:bg-surface-2"
          >
            <Download className="size-5 text-fg-tertiary" aria-hidden="true" />
            {t('nav.imports')}
          </button>
          <button
            type="button"
            onClick={() => go('/settings')}
            className="flex h-12 items-center gap-3 rounded-md px-3 text-body text-fg-primary hover:bg-surface-2"
          >
            <Settings className="size-5 text-fg-tertiary" aria-hidden="true" />
            {t('nav.settings')}
          </button>
        </div>
        <div className="mt-4 flex flex-col gap-3 border-t border-stroke-subtle pt-4">
          <LanguageSwitcher />
        </div>
      </SheetContent>
    </Sheet>
  )
}
