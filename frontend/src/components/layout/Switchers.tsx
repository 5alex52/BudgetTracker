import { Monitor, Sun, Moon } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'
import { SegmentedControl } from '@/components/ui/toggles'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/overlays'

const THEME_ITEMS: Array<{ value: ThemeMode; icon: typeof Sun; labelKey: 'settings.appearance.system' | 'settings.appearance.light' | 'settings.appearance.dark' }> = [
  { value: 'system', icon: Monitor, labelKey: 'settings.appearance.system' },
  { value: 'light', icon: Sun, labelKey: 'settings.appearance.light' },
  { value: 'dark', icon: Moon, labelKey: 'settings.appearance.dark' },
]

/**
 * Theme: three states (light / dark / as in the browser).
 *
 * The switcher is shown as icons with tooltips: more compact than text
 * and doesn't get clipped on a narrow screen.
 */
export function ThemeSwitcher({
  compact = false,
  className,
  stretch = false,
}: {
  compact?: boolean
  className?: string
  /** Stretch to full width, segments split it evenly (for narrow screens) */
  stretch?: boolean
}) {
  const { mode, setMode } = useTheme()
  const { t } = useI18n()

  const items = THEME_ITEMS.map((item) => ({
    value: item.value,
    icon: item.icon,
    label: t(item.labelKey),
  }))

  return (
    <SegmentedControl
      aria-label={t('settings.appearance')}
      items={items}
      value={mode}
      onValueChange={(next: string) => next && setMode(next as ThemeMode)}
      iconOnly
      // flex-1 goes on the segments: Root's direct child is the ToggleGroup itself,
      // so the old [&>*] stretched the wrong thing.
      className={[compact ? 'text-[11px]' : '', stretch ? 'w-full [&>button]:flex-1' : '', className ?? '']
        .filter(Boolean)
        .join(' ')}
    />
  )
}

/** UI language RU / EN. */
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
