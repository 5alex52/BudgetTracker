import type { ReactNode } from 'react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Settings, ShieldCheck } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { Sheet, SheetContent } from '@/components/ui/dialogs'
import { LanguageSwitcher } from './Switchers'

/** Bottom glass Sheet for "More" on mobile. */
export function MoreSheet({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const { t } = useI18n()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)

  const go = (to: string) => {
    setOpen(false)
    navigate(to)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex flex-1 min-w-[4rem] flex-col items-center justify-center gap-1 rounded-md text-[11px] leading-4 text-fg-secondary"
      >
        {children}
      </button>
      <SheetContent side="bottom" title={t('common.more')}>
        <div className="flex flex-col gap-1">
          {user?.is_superuser && (
            <button
              type="button"
              onClick={() => go('/admin')}
              className="flex h-12 items-center gap-3 rounded-md px-3 text-body text-fg-primary"
            >
              <ShieldCheck className="size-5 text-fg-tertiary" aria-hidden="true" />
              {t('nav.admin')}
            </button>
          )}
          <button
            type="button"
            onClick={() => go('/settings')}
            className="flex h-12 items-center gap-3 rounded-md px-3 text-body text-fg-primary"
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
