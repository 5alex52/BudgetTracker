import { Monitor, Moon, Sun } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'
import { SegmentedControl } from '@/components/ui/toggles'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/overlays'

const THEME_ITEMS: Array<{ value: ThemeMode; label: string; icon: typeof Sun }> = [
  { value: 'system', label: 'system', icon: Monitor },
  { value: 'light', label: 'light', icon: Sun },
  { value: 'dark', label: 'dark', icon: Moon },
]

/** Тема: три состояния (светлая / тёмная / как в браузере). */
export function ThemeSwitcher({
  compact = false,
  className,
  stretch = false,
}: {
  compact?: boolean
  className?: string
  /** Растянуть на всю ширину, сегменты делят её поровну (для узких экранов) */
  stretch?: boolean
}) {
  const { mode, setMode } = useTheme()
  const { t } = useI18n()

  const items = THEME_ITEMS.map((item) => ({
    value: item.value,
    label:
      item.value === 'system'
        ? t('settings.appearance.system')
        : item.value === 'light'
          ? t('settings.appearance.light')
          : t('settings.appearance.dark'),
  }))

  return (
    <SegmentedControl
      aria-label={t('settings.appearance')}
      items={items}
      value={mode}
      onValueChange={(next: string) => next && setMode(next as ThemeMode)}
      className={[
        compact ? 'text-[11px]' : '',
        stretch ? 'w-full [&>*]:flex-1 [&>*]:justify-center' : '',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
    />
  )
}

/** Язык интерфейса RU / EN. */
export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n()

  return (
    <Select value={locale} onValueChange={(next) => setLocale(next as 'ru' | 'en')}>
      <SelectTrigger aria-label={t('settings.language')} className="h-[var(--control-h-sm)] w-32 text-label">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="ru">Русский</SelectItem>
        <SelectItem value="en">English</SelectItem>
      </SelectContent>
    </Select>
  )
}
