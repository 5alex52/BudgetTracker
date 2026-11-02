import { useEffect, useRef, useState, type ReactNode } from 'react'
import {
  Bold,
  Check,
  ChevronDown,
  CreditCard,
  Info,
  Layers,
  Plus,
  Search,
  Smartphone,
  Trash2,
  Wallet,
} from 'lucide-react'
import { useI18n } from '@/i18n'
import { useTheme } from '@/hooks/useTheme'
import { supportsBackdropRefraction } from '@/__shared__/utils/feature-detect'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { GlassBackdrop } from '@/components/glass/GlassBackdrop'
import { Button } from '@/components/ui/button'
import { Field, Input, Label, Textarea } from '@/components/ui/field'
import { Checkbox, SegmentedControl, Slider, Switch } from '@/components/ui/toggles'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  FilterSelect,
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/overlays'
import {
  Dialog,
  DialogContent,
  DialogTrigger,
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { Amount, CurrencyTag, TrendBadge } from '@/components/data/Amount'
import { AccountCard } from '@/components/data/AccountCard'
import { accounts, expenseStructure } from '@/__shared__/mock/finance'
import { Card, CardHeader } from '@/components/ui/card'
import { BarChart, DonutChart, LineChart } from '@/components/charts/charts'
import { ThemeSwitcher } from '@/components/layout/Switchers'

/* ------------------------------- каркас ----------------------------------- */

function Section({
  id,
  title,
  note,
  children,
}: {
  id: string
  title: string
  note?: string
  children: ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-stroke-subtle pt-8 first:border-0 first:pt-0">
      <h2 className="text-title font-semibold tracking-snug text-fg-primary">{title}</h2>
      {note && <p className="mt-1 max-w-3xl text-label text-fg-secondary">{note}</p>}
      <div className="mt-5">{children}</div>
    </section>
  )
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="w-28 shrink-0 text-caption uppercase tracking-wide text-fg-tertiary">{label}</span>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  )
}

/** Пёстрая подложка: без неё blur нечего показывать. */
function BusyBackdrop() {
  return (
    <div
      className="absolute inset-0 overflow-hidden rounded-xl"
      style={{
        backgroundImage:
          'radial-gradient(circle at 20% 30%, #f472b6 0%, transparent 45%), radial-gradient(circle at 80% 20%, #22d3ee 0%, transparent 45%), radial-gradient(circle at 60% 80%, #a3e635 0%, transparent 45%), radial-gradient(circle at 15% 85%, #fbbf24 0%, transparent 45%), linear-gradient(140deg, #4f46e5, #0ea5e9)',
      }}
      aria-hidden="true"
    >
      <div className="absolute inset-0">
        <div className="absolute left-[6%] top-[18%] size-16 rounded-full bg-white/85" />
        <div className="absolute left-[42%] top-[8%] h-24 w-24 rotate-12 rounded-lg bg-black/55" />
        <div className="absolute right-[12%] top-[30%] size-20 rounded-full bg-white/70" />
        <div className="absolute bottom-[12%] left-[22%] h-16 w-32 rounded-md bg-black/45" />
        <div className="absolute bottom-[18%] right-[30%] size-14 rounded-full bg-white/75" />
      </div>
      <div className="flex h-full flex-col justify-between p-4 text-[10px] font-medium leading-tight text-white/85">
        <p>Читаемый текст под стеклом · readable text under glass · [PHONE]</p>
        <p>Быстрая коричневая лиса прыгает через ленивую собаку · The quick brown fox</p>
      </div>
    </div>
  )
}

/** Живой счётчик стеклянных поверхностей в вьюпорте (ориентир ТЗ: ≤ 6). */
function useGlassInView(ref: React.RefObject<HTMLElement>) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      const nodes = document.querySelectorAll<HTMLElement>('.glass, [data-glass]')
      let visible = 0
      nodes.forEach((node) => {
        const rect = node.getBoundingClientRect()
        if (rect.bottom > 0 && rect.top < window.innerHeight && rect.height > 0) visible += 1
      })
      setCount(visible)
    }
    const schedule = () => {
      if (frame) return
      frame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      if (frame) cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [ref])

  return count
}

/** Проверка tabular-nums настоящим измерением ширины цифр в DOM. */
function useTabularNumsCheck() {
  const [state, setState] = useState<'unknown' | 'ok' | 'fallback'>('unknown')

  useEffect(() => {
    let cancelled = false
    const measure = () => {
      const holder = document.createElement('span')
      holder.style.cssText =
        'position:absolute;visibility:hidden;white-space:pre;font:500 20px var(--font-sans);font-variant-numeric:tabular-nums'
      const a = document.createElement('span')
      a.textContent = '1111'
      const b = document.createElement('span')
      b.textContent = '8888'
      holder.append(a, b)
      document.body.appendChild(holder)
      const widthA = a.getBoundingClientRect().width
      const widthB = b.getBoundingClientRect().width
      holder.remove()
      if (!cancelled) setState(Math.abs(widthA - widthB) < 0.5 ? 'ok' : 'fallback')
    }
    if (document.fonts?.ready) {
      document.fonts.ready.then(measure)
    } else {
      measure()
    }
    return () => {
      cancelled = true
    }
  }, [])

  return state
}

/* ------------------------------ страница ---------------------------------- */

export function DesignPage() {
  const { t } = useI18n()
  const { resolved } = useTheme()
  const { toast } = useToast()
  const pageRef = useRef<HTMLDivElement>(null)

  const [refraction, setRefraction] = useState(false)
  const [fontsReady, setFontsReady] = useState(false)
  const [checked, setChecked] = useState(true)
  const [partial, setPartial] = useState<boolean | 'indeterminate'>('indeterminate')
  const [switchOn, setSwitchOn] = useState(true)
  const [range, setRange] = useState([120, 840])
  const [segment, setSegment] = useState('expense')
  const [currency, setCurrency] = useState('byn')

  const glassInView = useGlassInView(pageRef)
  const tabular = useTabularNumsCheck()

  useEffect(() => {
    setRefraction(supportsBackdropRefraction())
    document.fonts?.ready.then(() => setFontsReady(true))
  }, [])

  const checks = [
    { label: 'Тема', value: resolved, hint: 'переключатель + prefers-color-scheme' },
    {
      label: 'Рефракция: SVG в backdrop',
      value: refraction ? 'движок заявляет' : 'не заявлена',
      hint: 'Chromium рисует смещение; WebKit разбирает, но остаётся уровень 1',
    },
    {
      label: 'tabular-nums',
      value: tabular === 'ok' ? 'работает' : tabular === 'fallback' ? 'нет → Medeo Mono' : '…',
      hint: 'измерение ширины цифр',
    },
    { label: 'Стекло в вьюпорте', value: `${glassInView} / ≤ 6`, hint: 'ориентир производительности' },
  ]

  return (
    <div ref={pageRef} className="relative min-h-dvh">
      <GlassBackdrop />

      <div className="relative z-[1] mx-auto max-w-container px-4 py-8 md:px-6">
        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-display font-semibold tracking-tight text-fg-primary">{t('design.title')}</h1>
            <p className="mt-1 text-body text-fg-secondary">{t('design.subtitle')}</p>
          </div>
          <ThemeSwitcher />
        </header>

        <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {checks.map((item) => (
            <Card key={item.label} className="p-4">
              <p className="text-caption text-fg-tertiary">{item.label}</p>
              <p className="mt-1 text-label font-medium text-fg-primary">{item.value}</p>
              <p className="mt-0.5 text-caption text-fg-tertiary">{item.hint}</p>
            </Card>
          ))}
        </div>

        <div className="space-y-10">
          {/* ------------------------------ материал ------------------------------ */}
          <Section
            id="material"
            title="Материал GlassSurface"
            note="Три варианта прозрачности и три уровня размытия над пёстрой подложкой. Рефракция — только при feature-detect и ширине ≤ 800 px."
          >
            <div className="relative overflow-hidden rounded-xl p-6">
              <BusyBackdrop />
              <div className="relative grid gap-4 sm:grid-cols-3">
                {(['regular', 'clear', 'tinted'] as const).map((variant) => (
                  <GlassSurface key={variant} variant={variant} level="md" refraction glow className="p-4">
                    <p className="text-label font-medium text-fg-primary">{variant}</p>
                    <p className="mt-1 text-caption text-fg-secondary">
                      blur 20 · saturate 165% · {variant === 'tinted' ? 'accent tint' : variant}
                    </p>
                  </GlassSurface>
                ))}
              </div>
              <div className="relative mt-4 grid gap-4 sm:grid-cols-3">
                {(['sm', 'md', 'lg'] as const).map((level) => (
                  <GlassSurface key={level} level={level} className="p-4" style={{ minHeight: 76 }}>
                    <p className="text-label font-medium text-fg-primary">level=&quot;{level}&quot;</p>
                    <p className="mt-1 text-caption text-fg-secondary">
                      {level === 'sm'
                        ? 'blur 10 · radius 14'
                        : level === 'md'
                          ? 'blur 20 · radius 20'
                          : 'blur 34 · radius 28'}
                    </p>
                  </GlassSurface>
                ))}
              </div>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Card>
                <CardHeader
                  title="Стекло над контентом"
                  subtitle="Проверка «протекания» контента под стеклом"
                />
                <div className="relative mt-3 h-40 overflow-hidden rounded-md bg-surface-2 p-3">
                  <p className="text-caption leading-relaxed text-fg-primary">
                    Под этим стеклом лежит текст и линии: при работающем blur они размываются, а не
                    просвечивают резко. [PHONE] · квик браун фокс.
                  </p>
                  <GlassSurface level="sm" className="absolute bottom-3 left-3 right-3 p-3">
                    <p className="text-label font-medium text-fg-primary">GlassSurface level=&quot;sm&quot;</p>
                  </GlassSurface>
                </div>
              </Card>

              <Card>
                <CardHeader title="Отказы и спец-режимы" subtitle="Проверяются системными настройками ОС" />
                <ul className="mt-3 space-y-2 text-caption text-fg-secondary">
                  <li>
                    <code className="text-fg-primary">prefers-reduced-transparency</code> → плотный фон, blur
                    отключён
                  </li>
                  <li>
                    <code className="text-fg-primary">prefers-contrast: more</code> → непрозрачный фон, границы
                    currentColor
                  </li>
                  <li>
                    <code className="text-fg-primary">prefers-reduced-motion</code> → без пружин и scale
                  </li>
                  <li>
                    <code className="text-fg-primary">@supports not (backdrop-filter)</code> → surface-1 без
                    блика
                  </li>
                  <li>Ширина стекла &gt; 800 px → рефракция не применяется, остаётся blur</li>
                </ul>
              </Card>
            </div>
          </Section>

          {/* ------------------------------- кнопки ------------------------------- */}
          <Section
            id="buttons"
            title="Button"
            note="Варианты, размеры и статические состояния (disabled, loading). Hover, focus-visible и pressed живые."
          >
            <div className="space-y-4">
              <Row label="primary">
                <Button>Купить</Button>
                <Button size="sm">Small</Button>
                <Button size="lg">Large</Button>
                <Button pill>Пилюля</Button>
                <Button disabled>Disabled</Button>
                <Button loading>Loading</Button>
              </Row>
              <Row label="glass">
                <Button variant="glass">Стекло</Button>
                <Button variant="glass" size="sm">
                  Small
                </Button>
                <Button variant="glass" pill>
                  Пилюля
                </Button>
                <Button variant="glass" disabled>
                  Disabled
                </Button>
              </Row>
              <Row label="subtle / ghost">
                <Button variant="subtle">Subtle</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="subtle" disabled>
                  Disabled
                </Button>
              </Row>
              <Row label="icon">
                <Button variant="ghost" size="icon" aria-label="Добавить">
                  <Plus className="size-4" aria-hidden="true" />
                </Button>
                <Button variant="glass" size="icon" aria-label="Смартфон">
                  <Smartphone className="size-4" aria-hidden="true" />
                </Button>
                <Button variant="subtle" size="icon" aria-label="Слои">
                  <Layers className="size-4" aria-hidden="true" />
                </Button>
              </Row>
              <Row label="danger / link">
                <Button variant="danger" className="gap-1.5">
                  <Trash2 className="size-4" aria-hidden="true" />
                  Удалить
                </Button>
                <Button variant="link">Ссылка</Button>
              </Row>
            </div>
          </Section>

          {/* -------------------------------- поля -------------------------------- */}
          <Section id="fields" title="Input / Field" note="Размеры, иконка, валютный слот, ошибка, disabled.">
            <div className="grid gap-4 md:grid-cols-3">
              <Field label="E-mail" hint="Подсказка под полем">
                <Input placeholder="name@example.com" type="email" />
              </Field>
              <Field label="Поиск" hint="С иконкой слева">
                <Input placeholder={t('common.search')} iconLeft={<Search className="size-4" />} />
              </Field>
              <Field label="Сумма" hint="Слот справа — валюта">
                <Input defaultValue="1 200,00" slotRight={<CurrencyTag currency="BYN" />} />
              </Field>
              <Field label="Ошибка" error="Обязательное поле">
                <Input invalid placeholder="Пусто" />
              </Field>
              <Field label="Disabled">
                <Input disabled defaultValue="Недоступно" />
              </Field>
              <Field label="Малый размер">
                <Input inputSize="sm" placeholder="sm · 32 px" />
              </Field>
              <Field label="Многострочное" className="md:col-span-3">
                <Textarea placeholder={t('recordForm.notePlaceholder')} />
              </Field>
            </div>
          </Section>

          {/* ------------------------------ контролы ----------------------------- */}
          <Section
            id="controls"
            title="Switch / Checkbox / Slider / Segmented"
            note="Все состояния, включая indeterminate и disabled."
          >
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <div className="space-y-4">
                  <Row label="switch">
                    <Switch checked={switchOn} onCheckedChange={setSwitchOn} aria-label="Демо" />
                    <Switch aria-label="Выключен" />
                    <Switch disabled checked aria-label="Disabled" />
                  </Row>
                  <Row label="checkbox">
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) => setChecked(value === true)}
                      aria-label="Демо"
                    />
                    <Checkbox aria-label="Выключен" />
                    <Checkbox
                      checked={partial}
                      onCheckedChange={setPartial}
                      aria-label="Частично"
                    />
                    <Checkbox disabled aria-label="Disabled" />
                  </Row>
                  <Row label="slider">
                    <div className="w-64">
                      <Slider
                        value={range}
                        onValueChange={setRange}
                        showValues
                        min={0}
                        max={1000}
                        step={10}
                        aria-label={t('filters.amountRange')}
                      />
                    </div>
                  </Row>
                  <Row label="segmented">
                    <SegmentedControl
                      aria-label="Тип записи"
                      value={segment}
                      onValueChange={setSegment}
                      items={[
                        { value: 'expense', label: t('recordForm.expense') },
                        { value: 'income', label: t('recordForm.income') },
                        { value: 'transfer', label: t('recordForm.transfer') },
                      ]}
                    />
                  </Row>
                </div>
              </Card>

              <Card>
                <CardHeader title="Select и плавающие слои" subtitle="Radix: select, popover, dropdown, toast" />
                <div className="mt-4 space-y-3">
                  <Row label="select">
                    <div className="w-56">
                      <FilterSelect
                        ariaLabel="Валюта"
                        value={currency}
                        onValueChange={setCurrency}
                        icon={<Wallet className="size-4" />}
                        options={[
                          { value: 'byn', label: 'BYN' },
                          { value: 'rub', label: 'RUB' },
                          { value: 'usd', label: 'USD' },
                          { value: 'eur', label: 'EUR' },
                        ]}
                      />
                    </div>
                  </Row>
                  <Row label="popover">
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button variant="glass" size="sm" className="gap-1.5">
                          <Info className="size-4" aria-hidden="true" />
                          Открыть
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent>
                        <p className="text-label font-medium text-fg-primary">Popover на стекле</p>
                        <p className="mt-1 text-caption text-fg-secondary">
                          Внутри стекла — только surface-2/3, без вложенного blur.
                        </p>
                      </PopoverContent>
                    </Popover>
                  </Row>
                  <Row label="dropdown">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="glass" size="sm" className="gap-1.5">
                          Меню
                          <ChevronDown className="size-3.5" aria-hidden="true" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        <DropdownMenuLabel>Действия</DropdownMenuLabel>
                        <DropdownMenuItem>
                          <Check className="size-4" aria-hidden="true" />
                          Выбрать
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <CreditCard className="size-4" aria-hidden="true" />
                          Изменить
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                          <Trash2 className="size-4" aria-hidden="true" />
                          Удалить
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </Row>
                  <Row label="toast">
                    <Button
                      variant="subtle"
                      size="sm"
                      onClick={() =>
                        toast({
                          title: 'Запись добавлена',
                          description: '−120,00 BYN · Продукты',
                          tone: 'success',
                        })
                      }
                    >
                      Показать тост
                    </Button>
                  </Row>
                </div>
              </Card>
            </div>
          </Section>

          {/* -------------------------------- слои -------------------------------- */}
          <Section
            id="layers"
            title="Dialog / Sheet"
            note="Стеклянные модальные слои: подложка с затемнением и статичным blur(2px)."
          >
            <div className="flex flex-wrap gap-3">
              <Dialog>
                <DialogTrigger asChild>
                  <Button>Открыть Dialog</Button>
                </DialogTrigger>
                <DialogContent title="Удалить запись?" description="Действие нельзя отменить.">
                  <p className="text-body text-fg-secondary">
                    Запись «Продукты −120,00 BYN» будет удалена из списка.
                  </p>
                  <div className="mt-6 flex justify-end gap-2">
                    <Button variant="subtle">Отмена</Button>
                    <Button variant="danger">Удалить</Button>
                  </div>
                </DialogContent>
              </Dialog>

              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="glass">Sheet слева</Button>
                </SheetTrigger>
                <SheetContent side="left" title="Фильтры">
                  <p className="text-label text-fg-secondary">
                    На мобиле здесь живёт панель фильтров из 11 групп.
                  </p>
                </SheetContent>
              </Sheet>

              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="glass">Sheet снизу</Button>
                </SheetTrigger>
                <SheetContent side="bottom" title="Ещё">
                  <p className="text-label text-fg-secondary">
                    Мобильное меню «Ещё» и переключатели темы и языка.
                  </p>
                </SheetContent>
              </Sheet>
            </div>
          </Section>

          {/* ------------------------------- данные ------------------------------- */}
          <Section
            id="data"
            title="Данные"
            note="Суммы, тренды, валюты, плитки счетов — во всех состояниях."
          >
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader title="Amount" subtitle="tabular-nums; знак и цвет несут смысл" />
                <div className="mt-4 space-y-3">
                  <Row label="размеры">
                    <Amount value={16059.73} size="lg" tone="neutral" />
                    <Amount value={-2329.15} size="md" />
                    <Amount value={12267.07} size="sm" />
                    <Amount value={0} size="xs" />
                  </Row>
                  <Row label="тон">
                    <Amount value={1200} tone="positive" />
                    <Amount value={-1200} tone="negative" />
                    <Amount value={1200} tone="neutral" />
                  </Row>
                  <Row label="tone=auto">
                    <Amount value={9937.92} size="sm" />
                    <Amount value={-3329.15} size="sm" />
                    <Amount value={0} size="sm" />
                  </Row>
                  <Row label="валюта">
                    <Amount value={109401.99} currency="RUB" size="sm" />
                    <Amount value={5345} currency="USD" size="sm" />
                    <Amount value={0} currency="EUR" size="sm" />
                  </Row>
                  <Row label="trend / tag">
                    <TrendBadge value={174} />
                    <TrendBadge value={-69} />
                    <TrendBadge value={0} />
                    <CurrencyTag currency="BYN" />
                    <CurrencyTag currency="RUB" />
                  </Row>
                </div>
              </Card>

              <Card>
                <CardHeader title="AccountCard" subtitle="обычный / только чтение / вне статистики / архив" />
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {accounts
                    .filter((account) => ['alfa', 'alfa-rub', 'alfa-usd', 'tinkoff-usd'].includes(account.id))
                    .map((account) => (
                      <AccountCard key={account.id} account={account} />
                    ))}
                </div>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader title="Графики" subtitle="SVG на токенах: линия, бары, донат" />
                <div className="mt-4 grid gap-6 md:grid-cols-3">
                  <LineChart
                    points={[
                      { label: '1 окт.', value: 12600 },
                      { label: '10 окт.', value: 13550 },
                      { label: '20 окт.', value: 14500 },
                      { label: '31 окт.', value: 16059.73 },
                    ]}
                    ariaLabel="Динамика баланса"
                  />
                  <BarChart
                    points={[
                      { label: '1 окт.', income: 1200, expense: -400 },
                      { label: '10 окт.', income: 2100, expense: -1100 },
                      { label: '20 окт.', income: 3000, expense: -500 },
                      { label: '31 окт.', income: 2200, expense: -900 },
                    ]}
                    ariaLabel="Денежный поток"
                  />
                  <DonutChart segments={expenseStructure} ariaLabel="Структура расходов" size={150} />
                </div>
              </Card>
            </div>
          </Section>

          {/* ----------------------------- типографика ---------------------------- */}
          <Section id="type" title="Типографика" note="Medeo Sans / Medeo Mono, шкала, кириллица, tabular-nums.">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <div className="space-y-2">
                  <p className="text-display font-semibold tracking-tight text-fg-primary">
                    Display 32 · Ваши финансы
                  </p>
                  <p className="text-title font-semibold text-fg-primary">Title 24 · Аналитика</p>
                  <p className="text-headline font-semibold text-fg-primary">Headline 17 · Структура расходов</p>
                  <p className="text-body text-fg-primary">
                    Body 15 · Погрузитесь в отчёты, составляйте бюджеты, синхронизируйте банки.
                  </p>
                  <p className="text-label text-fg-secondary">Label 13 · Категория, метки, дата и время</p>
                  <p className="text-caption text-fg-tertiary">Caption 12 · В сравнении с предыдущим периодом</p>
                  <p className="text-overline uppercase text-fg-tertiary">Overline 11 · WALLET / ОБЩИЕ</p>
                </div>
              </Card>
              <Card>
                <CardHeader title="Цифры и кириллица" subtitle="Проверка набора и глифов" />
                <div className="mt-3 space-y-2">
                  <p className="num text-metric-xl text-fg-primary">1 234 567,89</p>
                  <p className="tnum text-metric text-fg-primary">1111 · 8888 · 0000</p>
                  <p className="text-body text-fg-primary">Ж Щ Д Ю ё й Ә Ғ Қ Ң Ө Ү Һ — Ъ Ы Ь Э Ю Я</p>
                  <p className="text-body text-fg-primary">€ ₽ $ BYN — − + = %</p>
                  <dl className="mt-3 space-y-1 text-caption text-fg-secondary">
                    <div className="flex gap-2">
                      <dt className="text-fg-tertiary">tabular-nums:</dt>
                      <dd className="text-fg-primary">
                        {tabular === 'ok'
                          ? 'работает в Medeo Sans'
                          : tabular === 'fallback'
                            ? 'не работает → .num (Medeo Mono)'
                            : 'измеряется…'}
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="text-fg-tertiary">webfont:</dt>
                      <dd className="text-fg-primary">{fontsReady ? 'загружен (self-host)' : 'загружается…'}</dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="text-fg-tertiary">optical sizing:</dt>
                      <dd className="text-fg-primary">auto (opsz 14–32)</dd>
                    </div>
                  </dl>
                </div>
              </Card>
            </div>
          </Section>

          {/* --------------------------- доступность ----------------------------- */}
          <Section id="a11y" title="Доступность" note="Фокус, клавиатура, контраст, ограничения движения.">
            <Card>
              <ul className="space-y-2 text-label text-fg-secondary">
                <li>
                  Видимый <code className="text-fg-primary">:focus-visible</code> — 2 px accent, offset 2 px.
                </li>
                <li>
                  Все слои закрываются по <kbd className="text-fg-primary">Esc</kbd>, фокус возвращается на
                  триггер (Radix).
                </li>
                <li>
                  Иконки-кнопки имеют <code className="text-fg-primary">aria-label</code>; суммы —{' '}
                  <code className="text-fg-primary">aria-label</code> в развёрнутом виде.
                </li>
                <li>Скип-линк «К основному содержимому» — первый таб в оболочке приложения.</li>
                <li>Доход и расход различаются знаком и стрелкой, не только цветом.</li>
                <li>Одновременно видимых стеклянных поверхностей: {glassInView} (ориентир ≤ 6).</li>
              </ul>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Button variant="glass" size="sm">
                  <Bold className="size-4" aria-hidden="true" />
                  Фокус по Tab
                </Button>
                <Input className="w-40" defaultValue="Tab сюда" aria-label="Поле для проверки фокуса" />
                <Label>Подпись поля</Label>
              </div>
            </Card>
          </Section>
        </div>
      </div>
    </div>
  )
}
