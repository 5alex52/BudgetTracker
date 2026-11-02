import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { ChevronDown, LogOut, Monitor, Moon, Settings, Sun } from 'lucide-react'
import { useI18n, type Locale } from '@/i18n'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'
import { cn } from '@/__shared__/utils/cn'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/overlays'

const THEME_OPTIONS: Array<{ mode: ThemeMode; labelKey: 'settings.appearance.system' | 'settings.appearance.light' | 'settings.appearance.dark'; icon: typeof Sun }> = [
  { mode: 'system', labelKey: 'settings.appearance.system', icon: Monitor },
  { mode: 'light', labelKey: 'settings.appearance.light', icon: Sun },
  { mode: 'dark', labelKey: 'settings.appearance.dark', icon: Moon },
]

const LOCALES: Array<{ locale: Locale; label: string }> = [
  { locale: 'ru', label: 'Русский' },
  { locale: 'en', label: 'English' },
]

/** Меню пользователя: тема, язык, настройки. Плавающий слой — на стекле. */
export function UserMenu() {
  const { t, locale, setLocale } = useI18n()
  const { mode, setMode } = useTheme()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const signOut = useAuthStore((state) => state.signOut)

  // Инициалы вместо аватара: сервер отдаёт только ссылку на фото, а её может не быть
  const fullName = user?.fullname || user?.firstname || user?.email || '—'
  const initials =
    (user?.firstname?.[0] ?? '') + (user?.lastname?.[0] ?? '') || fullName.slice(0, 2).toUpperCase()

  const logout = async () => {
    await signOut()
    navigate('/login', { replace: true })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" pill className="gap-2 pl-1 pr-2">
          <span className="grid size-6 place-items-center rounded-pill bg-accent-soft text-caption font-semibold text-accent-on-soft uppercase">
            {initials}
          </span>
          <span className="hidden max-w-40 truncate text-label text-fg-primary lg:inline">{fullName}</span>
          <ChevronDown className="size-3.5 text-fg-tertiary" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuLabel>{t('settings.appearance')}</DropdownMenuLabel>
        {THEME_OPTIONS.map(({ mode: option, labelKey, icon: Icon }) => (
          <DropdownMenuItem
            key={option}
            onSelect={() => setMode(option)}
            className={cn(mode === option && 'text-accent')}
          >
            <Icon className="size-4" aria-hidden="true" />
            {t(labelKey)}
            {mode === option && <span className="ml-auto text-caption">●</span>}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuLabel>{t('login.language')}</DropdownMenuLabel>
        {LOCALES.map((item) => (
          <DropdownMenuItem
            key={item.locale}
            onSelect={() => setLocale(item.locale)}
            className={cn(locale === item.locale && 'text-accent')}
          >
            {item.label}
            {locale === item.locale && <span className="ml-auto text-caption">●</span>}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate('/settings')}>
          <Settings className="size-4" aria-hidden="true" />
          {t('nav.settings')}
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void logout()}>
          <LogOut className="size-4" aria-hidden="true" />
          {t('login.signOut')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
