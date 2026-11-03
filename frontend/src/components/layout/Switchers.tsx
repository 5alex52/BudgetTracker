import { useI18n } from '@/i18n'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'
import { SegmentedControl } from '@/components/ui/toggles'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/overlays'

const THEME_ITEMS: Array<{ value: ThemeMode }> = [
  { value: 'system' },
  { value: 'light' },
  { value: 'dark' },
]

/**
 * Тема: три состояния (светлая / тёмная / как в браузере).
 *
 * Макеты — `docs/design/mockups/login-{desktop,mobile}-*.png`: контроль
 * текстовый, без пиктограмм, и на узком экране подписи не должны обрезаться.
 * Поэтому ``stretch`` растягивает полосу на всю ширину, а сегменты делят её
 * поровну: так три подписи помещаются и на 390 px, как в мобильном макете.
 */
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
      // flex-1 вешаем на сегменты: прямой потомок Root — это сам ToggleGroup,
      // поэтому прежний [&>*] растягивал не то.
      className={[compact ? 'text-[11px]' : '', stretch ? 'w-full [&>button]:flex-1' : '', className ?? '']
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
