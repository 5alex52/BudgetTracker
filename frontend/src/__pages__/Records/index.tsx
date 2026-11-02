import { useEffect, useMemo, useState } from 'react'
import { ArrowDownUp, Filter, MoreHorizontal, Plus, Search, Trash2 } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { RecordItem } from '@/__shared__/types/models'
import { useRecordsStore } from '@/store/records'
import { ApiError } from '@/api'
import { useRecordDialog } from '@/components/records/RecordDialogContext'
import { readableOnTint } from '@/__shared__/utils/contrast'
import { useTheme } from '@/hooks/useTheme'
import { useDebounced } from '@/hooks/useApi'
import { AppShell } from '@/components/layout/AppShell'
import { EMPTY_FILTERS, FilterPanel, type RecordFilters } from '@/components/filters/FilterPanel'
import { Amount } from '@/components/data/Amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/field'
import { Checkbox } from '@/components/ui/toggles'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  FilterSelect,
} from '@/components/ui/overlays'
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

/** Порядок в интерфейсе → параметр `sort` сервера. */
const SORT_PARAM = {
  timeDesc: 'date_desc',
  timeAsc: 'date_asc',
  amountDesc: 'amount_desc',
  amountAsc: 'amount_asc',
} as const

function formatDay(date: string, locale: 'ru' | 'en') {
  const parsed = new Date(`${date}T00:00:00`)
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(parsed)
}

/**
 * «Записи»: фильтры в сайдбаре, список по дням, итог за период.
 *
 * Фильтрация, поиск и сортировка выполняются на сервере: клиент держит только
 * текущую страницу. Поэтому счётчик «найдено» — это `X-Total-Count`, а не длина
 * загруженного куска.
 */
export function RecordsPage() {
  const { openCreate: onAddRecord, openEdit: onEditRecord } = useRecordDialog()
  const { toast } = useToast()
  const { t, locale } = useI18n()

  const records = useRecordsStore((state) => state.items)
  const total = useRecordsStore((state) => state.total)
  const loading = useRecordsStore((state) => state.loading)
  const error = useRecordsStore((state) => state.error)
  const load = useRecordsStore((state) => state.load)
  const bulkRemove = useRecordsStore((state) => state.bulkRemove)
  const removeRecord = useRecordsStore((state) => state.remove)

  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounced(query)
  const [sort, setSort] = useState<SortKey>('timeDesc')
  const [filters, setFilters] = useState<RecordFilters>(EMPTY_FILTERS)
  const [selected, setSelected] = useState<string[]>([])
  const [filterOpen, setFilterOpen] = useState(false)

  /* Текущие фильтры в терминах API: их же получает серверная выгрузка */
  const apiFilters = useMemo(
    () => ({
      q: debouncedQuery.trim() || undefined,
      sort: SORT_PARAM[sort],
      account_ids: filters.accountIds.map(Number),
      category_ids: filters.categoryIds,
      tag_ids: filters.tagIds,
      currency_ids: filters.currencies,
      types: filters.types,
      amount_min: filters.amountMin,
      amount_max: filters.amountMax,
    }),
    [debouncedQuery, sort, filters],
  )

  /* Первая загрузка и любое изменение фильтров/поиска/сортировки — один запрос */
  useEffect(() => {
    void load(apiFilters)
    setSelected([])
  }, [apiFilters, load])

  /* Группировка по дням: сервер отдаёт плоский список с сортировкой */
  const grouped = useMemo(() => {
    const map = new Map<string, RecordItem[]>()
    records.forEach((item) => {
      const list = map.get(item.date) ?? []
      list.push(item)
      map.set(item.date, list)
    })
    return [...map.entries()]
  }, [records])

  /** Итог разбит по валютам: складывать рубли с долларами нельзя */
  const totalsByCurrency = useMemo(() => {
    const map = new Map<string, number>()
    records.forEach((item) => {
      map.set(item.currency, (map.get(item.currency) ?? 0) + item.amount)
    })
    return [...map.entries()].sort((left, right) => Math.abs(right[1]) - Math.abs(left[1]))
  }, [records])
  const allSelected = records.length > 0 && selected.length === records.length

  /** Массовое удаление: сервер принимает список id одним запросом */
  const removeSelected = async () => {
    if (selected.length === 0) return
    try {
      const deleted = await bulkRemove(selected)
      setSelected([])
      toast({ title: t('records.deleteSelectedDone', { count: deleted }), tone: 'info' })
    } catch (caught) {
      toast({
        title: t('records.deleteFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  const removeOne = async (id: string) => {
    try {
      await removeRecord(id)
      toast({ title: t('state.deleted'), tone: 'info' })
    } catch {
      toast({ title: t('records.deleteFailed'), tone: 'error' })
    }
  }

  return (
    <AppShell
      onAddRecord={onAddRecord}
      sidebar={
        <FilterPanel
          value={filters}
          onChange={setFilters}
          onReset={() => toast({ title: t('filters.reset'), description: t('filters.resetDone'), tone: 'info' })}
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
                  value={filters}
                  onChange={setFilters}
                  className="border-0 bg-transparent p-0 shadow-none"
                />
              </SheetContent>
            </Sheet>

            <ExportMenu items={records} serverFilters={apiFilters} />
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
            onCheckedChange={(value) => setSelected(value === true ? records.map((item) => item.id) : [])}
            aria-label={t('records.selectAll')}
          />
          <span className="text-caption text-fg-tertiary">{t('records.found', { count: total })}</span>
          {selected.length > 0 && (
            <>
              <span className="text-caption text-accent">
                {t('records.selectedCount', { count: selected.length })}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5 text-caption text-[var(--negative)]"
                onClick={() => void removeSelected()}
              >
                <Trash2 className="size-3.5" aria-hidden="true" />
                {t('records.deleteSelected')}
              </Button>
            </>
          )}
          <span className="ml-auto flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-fg-tertiary">
            {t('records.total')}:
            {totalsByCurrency.length === 0 ? (
              <Amount value={0} size="sm" tone="neutral" />
            ) : (
              totalsByCurrency.map(([currency, value]) => (
                <Amount key={currency} value={value} currency={currency} size="sm" tone="neutral" />
              ))
            )}
          </span>
        </div>

        {loading && records.length === 0 && (
          <p className="px-4 py-10 text-center text-label text-fg-tertiary" role="status">
            {t('state.loading')}
          </p>
        )}

        {error && (
          <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
            <p className="text-label text-fg-secondary">
              {t('records.loadFailed')}: {error}
            </p>
            <Button variant="subtle" size="sm" onClick={() => void load()}>
              {t('state.retry')}
            </Button>
          </div>
        )}

        {!loading && !error && grouped.length === 0 && (
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
                      onDelete={() => void removeOne(item.id)}
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

        {/* Догрузка: сервер отдаёт страницы по 100 записей */}
        {records.length < total && (
          <div className="border-t border-stroke-subtle px-4 py-3 text-center">
            <Button
              variant="subtle"
              size="sm"
              disabled={loading}
              onClick={() => void load(undefined, { append: true })}
            >
              {loading ? t('state.loading') : t('records.showMore')}
            </Button>
          </div>
        )}
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
          {item.isExcluded && (
            <span className="rounded-xs bg-surface-2 px-1.5 py-0.5 text-fg-tertiary">
              {t('records.excluded')}
            </span>
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
