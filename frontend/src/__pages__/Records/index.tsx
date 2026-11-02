import { useMemo, useState } from 'react'
import { ArrowDownUp, Filter, MoreHorizontal, Plus, Search } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { RecordItem } from '@/__shared__/mock/finance'
import { useRecordsStore } from '@/store/records'
import { useRecordDialog } from '@/components/records/RecordDialogContext'
import { readableOnTint } from '@/__shared__/utils/contrast'
import { useTheme } from '@/hooks/useTheme'
import { AppShell } from '@/components/layout/AppShell'
import { FilterPanel } from '@/components/filters/FilterPanel'
import { Amount } from '@/components/data/Amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/field'
import { Checkbox } from '@/components/ui/toggles'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, FilterSelect } from '@/components/ui/overlays'
import { ExportMenu } from '@/components/data/ExportMenu'
import { useToast } from '@/components/ui/toast'


import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/dialogs'
import { CategoryIcon } from '@/__shared__/utils/category-icon'

/** Порядок сортировки: по времени (новые сверху) — как в референсе. */
type SortKey = 'timeDesc' | 'timeAsc' | 'amountDesc' | 'amountAsc'

const SORT_LABEL_KEYS: Record<SortKey, TranslationKey> = {
  timeDesc: 'records.sortByDateDesc',
  timeAsc: 'records.sortByDateAsc',
  amountDesc: 'records.sortByAmountDesc',
  amountAsc: 'records.sortByAmountAsc',
}

function formatDay(date: string, locale: 'ru' | 'en') {
  const parsed = new Date(`${date}T00:00:00`)
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(parsed)
}

/** «Записи»: фильтры слева, список, сгруппированный по дням, итог за период. */
export function RecordsPage() {
  const { openCreate: onAddRecord, openEdit: onEditRecord } = useRecordDialog()
  const { toast } = useToast()
  const records = useRecordsStore((state) => state.items)
  const removeRecord = useRecordsStore((state) => state.remove)
  const { t, locale } = useI18n()
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('timeDesc')
  const [selected, setSelected] = useState<string[]>([])
  const [filterOpen, setFilterOpen] = useState(false)

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const found = needle
      ? records.filter(
          (item) =>
            item.category.toLowerCase().includes(needle) ||
            item.account.toLowerCase().includes(needle) ||
            (item.note ?? '').toLowerCase().includes(needle),
        )
      : records

    return [...found].sort((a, b) => {
      switch (sort) {
        case 'amountDesc':
          return Math.abs(b.amount) - Math.abs(a.amount)
        case 'amountAsc':
          return Math.abs(a.amount) - Math.abs(b.amount)
        case 'timeAsc':
          return `${a.date}${a.time}`.localeCompare(`${b.date}${b.time}`)
        default:
          return `${b.date}${b.time}`.localeCompare(`${a.date}${a.time}`)
      }
    })
  }, [records, query, sort])

  const grouped = useMemo(() => {
    const map = new Map<string, RecordItem[]>()
    filtered.forEach((item) => {
      const list = map.get(item.date) ?? []
      list.push(item)
      map.set(item.date, list)
    })
    return [...map.entries()]
  }, [filtered])

  const total = filtered.reduce((sum, item) => sum + item.amount, 0)
  const allSelected = filtered.length > 0 && selected.length === filtered.length

  return (
    <AppShell
      onAddRecord={onAddRecord}
      sidebar={
        <FilterPanel
          onReset={() => {
            setSelected([])
            setQuery('')
            toast({ title: t('filters.reset'), description: t('filters.resetDone'), tone: 'info' })
          }}
        />
      }
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('records.title')}</h1>
          <div className="flex flex-wrap items-center gap-2">
            {/* На мобиле фильтры открываются в Sheet: сайдбар скрыт */}
            <Sheet open={filterOpen} onOpenChange={setFilterOpen}>
              <SheetTrigger asChild>
                <Button variant="glass" size="sm" className="gap-1.5 md:hidden">
                  <Filter className="size-4" aria-hidden="true" />
                  {t('filters.title')}
                </Button>
              </SheetTrigger>
              <SheetContent side="left" title={t('filters.title')}>
                <FilterPanel
                  onReset={() => setFilterOpen(false)}
                  className="border-0 bg-transparent p-0 shadow-none"
                />
              </SheetContent>
            </Sheet>

            <ExportMenu items={records} />
            <Button size="sm" className="gap-1.5" onClick={onAddRecord}>
              <Plus className="size-4" aria-hidden="true" />
              {t('nav.addRecord')}
            </Button>
          </div>
        </div>
      }
    >
      {/* Тулбар списка */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="min-w-48 flex-1">
          <Input
            inputSize="sm"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('common.search')}
            iconLeft={<Search className="size-4" />}
            aria-label={t('common.search')}
          />
        </div>
        <div className="w-full sm:w-48">
          <FilterSelect
            ariaLabel={t('records.sortBy')}
            value={sort}
            onValueChange={(value) => setSort(value as SortKey)}
            icon={<ArrowDownUp className="size-4" />}
            options={(Object.keys(SORT_LABEL_KEYS) as SortKey[]).map((key) => ({
              value: key,
              label: t(SORT_LABEL_KEYS[key]),
            }))}
          />
        </div>
      </div>

      <Card className="overflow-hidden p-0">
        <div className="flex flex-wrap items-center gap-3 border-b border-stroke-subtle px-4 py-2.5">
          <Checkbox
            checked={allSelected ? true : selected.length > 0 ? 'indeterminate' : false}
            onCheckedChange={(value) => setSelected(value === true ? filtered.map((item) => item.id) : [])}
            aria-label={t('records.selectAll')}
          />
          <span className="text-caption text-fg-tertiary">{t('records.found', { count: filtered.length })}</span>
          {selected.length > 0 && (
            <span className="text-caption text-accent">
              {t('records.selectedCount', { count: selected.length })}
            </span>
          )}
          <span className="ml-auto flex items-center gap-1 text-caption text-fg-tertiary">
            {t('records.total')}:
            <Amount value={total} size="sm" tone="neutral" />
          </span>
        </div>

        {grouped.length === 0 && (
          <p className="px-4 py-10 text-center text-label text-fg-tertiary">{t('common.none')}</p>
        )}

        {grouped.map(([date, items]) => {
          const dayTotal = items.reduce((sum, item) => sum + item.amount, 0)
          return (
            <section key={date} aria-label={formatDay(date, locale)}>
              <div className="flex items-center justify-between gap-2 bg-surface-2/60 px-4 py-1.5">
                <h2 className="text-caption font-medium text-fg-secondary">{formatDay(date, locale)}</h2>
                <Amount value={dayTotal} size="xs" tone="neutral" className="text-fg-tertiary" />
              </div>
              <ul>
                {items.map((item, index) => (
                  <li key={item.id}>
                    <RecordRow
                      item={item}
                      onEdit={() => onEditRecord?.(item)}
                      onDelete={() => removeRecord(item.id)}
                      checked={selected.includes(item.id)}
                      onToggle={() =>
                        setSelected((prev) =>
                          prev.includes(item.id) ? prev.filter((id) => id !== item.id) : [...prev, item.id],
                        )
                      }
                      isFirst={index === 0}
                    />
                  </li>
                ))}
              </ul>
            </section>
          )
        })}
      </Card>
    </AppShell>
  )
}

/** Строка записи: иконка категории, название, счёт, время, сумма, меню. */
function RecordRow({
  item,
  checked,
  onToggle,
  onEdit,
  onDelete,
  isFirst,
}: {
  item: RecordItem
  checked: boolean
  onToggle: () => void
  onEdit?: () => void
  onDelete?: () => void
  isFirst: boolean
}) {
  const { t } = useI18n()
  const { isDark } = useTheme()

  return (
    <div
      className={cn(
        'group flex items-center gap-2.5 px-3 py-2.5 transition-colors duration-fast hover:bg-surface-2/70 sm:gap-3 sm:px-4',
        !isFirst && 'border-t border-stroke-subtle',
      )}
    >
      <span className="hidden sm:block">
        <Checkbox checked={checked} onCheckedChange={onToggle} aria-label={item.category} />
      </span>

      <span
        className="grid size-7 shrink-0 place-items-center rounded-pill sm:size-8"
        style={{
          backgroundColor: `${item.categoryColor}22`,
          color: readableOnTint(item.categoryColor, { dark: isDark, threshold: 3 }),
        }}
      >
        <CategoryIcon name={item.categoryIcon} className="size-4" />
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-label font-medium text-fg-primary">{item.category}</p>
        <p className="flex items-center gap-1.5 truncate text-caption text-fg-tertiary">
          <span
            className="size-1.5 shrink-0 rounded-full"
            style={{ backgroundColor: item.accountTint }}
            aria-hidden="true"
          />
          {item.account}
          <span aria-hidden="true">·</span>
          {item.time}
          {item.note && (
            <>
              <span aria-hidden="true">·</span>
              <span className="truncate">{item.note}</span>
            </>
          )}
        </p>
      </div>

      <Amount value={item.amount} currency={item.currency} size="sm" className="shrink-0" />

      <span className="hidden sm:block">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={t('records.rowMenu')}>
              <MoreHorizontal className="size-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onEdit}>{t('common.edit')}</DropdownMenuItem>
            <DropdownMenuItem className="text-[var(--negative)]" onSelect={onDelete}>
              {t('common.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </span>
    </div>
  )
}
