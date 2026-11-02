import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { useFinanceStore } from '@/store/finance'
import type { TransactionTypeValue } from '@/api/types'
import { Checkbox } from '@/components/ui/toggles'
import { Slider } from '@/components/ui/toggles'
import { Button } from '@/components/ui/button'
import { FilterSelect } from '@/components/ui/overlays'
import { CategoryIcon } from '@/__shared__/utils/category-icon'

/** Фильтры в терминах интерфейса: в параметры API их переводит страница записей. */
export interface RecordFilters {
  accountIds: string[]
  categoryIds: number[]
  tagIds: number[]
  currencies: string[]
  types: TransactionTypeValue[]
  amountMin?: number
  amountMax?: number
}

export const EMPTY_FILTERS: RecordFilters = {
  accountIds: [],
  categoryIds: [],
  tagIds: [],
  currencies: [],
  types: [],
}

/**
 * Панель фильтров записей.
 *
 * Набор групп сокращён до того, что реально фильтруется на сервере: счета,
 * категории, метки, валюты, тип записи и диапазон суммы. Группы вроде «статус
 * подтверждения» из макета остались бы декоративными, поэтому их нет.
 */
export function FilterPanel({
  value,
  onChange,
  onReset,
  className,
}: {
  value: RecordFilters
  onChange: (next: RecordFilters) => void
  onReset?: () => void
  className?: string
}) {
  const { t } = useI18n()
  const accounts = useFinanceStore((state) => state.accounts)
  const categories = useFinanceStore((state) => state.categories)
  const tags = useFinanceStore((state) => state.tags)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const currencyCodes = useFinanceStore((state) => state.currencyCodes)
  const [currency, setCurrency] = useState('all')
  const [recordType, setRecordType] = useState('all')
  const [range, setRange] = useState<[number, number]>([0, 5000])

  const toggleAccount = (id: string) =>
    onChange({
      ...value,
      accountIds: value.accountIds.includes(id)
        ? value.accountIds.filter((item) => item !== id)
        : [...value.accountIds, id],
    })

  const toggleCategory = (id: number) =>
    onChange({
      ...value,
      categoryIds: value.categoryIds.includes(id)
        ? value.categoryIds.filter((item) => item !== id)
        : [...value.categoryIds, id],
    })

  const toggleTag = (id: number) =>
    onChange({
      ...value,
      tagIds: value.tagIds.includes(id)
        ? value.tagIds.filter((item) => item !== id)
        : [...value.tagIds, id],
    })

  const reset = () => {
    setCurrency('all')
    setRecordType('all')
    setRange([0, 5000])
    onChange(EMPTY_FILTERS)
    onReset?.()
  }

  const groups = [
    {
      id: 'accounts',
      title: t('filters.accounts'),
      content: (
        <div className="max-h-44 space-y-2.5 overflow-y-auto pr-1">
          {accounts.length === 0 && <p className="text-caption text-fg-tertiary">{t('state.empty')}</p>}
          {accounts.map((account) => (
            <Checkbox
              key={account.id}
              checked={value.accountIds.includes(account.id)}
              onCheckedChange={() => toggleAccount(account.id)}
              label={
                <span className="flex items-center gap-1.5">
                  <span
                    className="size-1.5 rounded-full"
                    style={{ backgroundColor: account.tint }}
                    aria-hidden="true"
                  />
                  {account.name}
                </span>
              }
            />
          ))}
        </div>
      ),
    },
    {
      id: 'categories',
      title: t('filters.categories'),
      content: (
        <div className="max-h-44 space-y-2.5 overflow-y-auto pr-1">
          {categories.length === 0 && <p className="text-caption text-fg-tertiary">{t('state.empty')}</p>}
          {categories.map((category) => (
            <Checkbox
              key={category.id}
              checked={value.categoryIds.includes(category.id)}
              onCheckedChange={() => toggleCategory(category.id)}
              label={
                <span className="flex items-center gap-1.5">
                  <CategoryIcon name={category.icon} className="size-3.5" />
                  <span className={cn(category.parentId !== null && 'pl-2 text-fg-secondary')}>
                    {category.name}
                  </span>
                </span>
              }
            />
          ))}
        </div>
      ),
    },
    {
      id: 'tags',
      title: t('filters.tags'),
      content: (
        <div className="max-h-40 space-y-2.5 overflow-y-auto pr-1">
          {tags.length === 0 && <p className="text-caption text-fg-tertiary">{t('state.empty')}</p>}
          {tags.map((tag) => (
            <Checkbox
              key={tag.id}
              checked={value.tagIds.includes(tag.id)}
              onCheckedChange={() => toggleTag(tag.id)}
              label={
                <span className="flex items-center gap-1.5">
                  <span
                    className="size-2 rounded-full"
                    style={{ backgroundColor: tag.color }}
                    aria-hidden="true"
                  />
                  {tag.name}
                  <span className="text-fg-tertiary">{tag.transactions_count}</span>
                </span>
              }
            />
          ))}
        </div>
      ),
    },
    {
      id: 'currencies',
      title: t('filters.currencies'),
      content: (
        <FilterSelect
          ariaLabel={t('filters.currencies')}
          value={currency}
          onValueChange={(next) => {
            setCurrency(next)
            onChange({ ...value, currencies: next === 'all' ? [] : [next] })
          }}
          options={[
            { value: 'all', label: t('filters.allCurrencies') },
            ...currencyCodes().map((code) => ({ value: code, label: code })),
          ]}
        />
      ),
    },
    {
      id: 'types',
      title: t('filters.recordTypes'),
      content: (
        <FilterSelect
          ariaLabel={t('filters.recordTypes')}
          value={recordType}
          onValueChange={(next) => {
            setRecordType(next)
            onChange({
              ...value,
              types: next === 'all' ? [] : [next as TransactionTypeValue],
            })
          }}
          options={[
            { value: 'all', label: t('filters.allRecordTypes') },
            { value: 'income', label: t('recordForm.income') },
            { value: 'expense', label: t('recordForm.expense') },
            { value: 'transfer', label: t('recordForm.transfer') },
          ]}
        />
      ),
    },
    {
      id: 'amount',
      title: t('filters.amountRange'),
      content: (
        <div className="px-2 pt-1">
          <Slider
            value={[range[0], range[1]]}
            onValueChange={(next) => {
              const start = next[0] ?? 0
              const end = next[1] ?? 5000
              setRange([start, end])
              onChange({
                ...value,
                amountMin: start > 0 ? start : undefined,
                amountMax: end < 5000 ? end : undefined,
              })
            }}
            min={0}
            max={5000}
            step={50}
            showValues
            aria-label={t('filters.amountRange')}
          />
          <p className="mt-2 text-caption text-fg-tertiary">
            {t('filters.amountAbsolute')} · {baseCurrency}
          </p>
        </div>
      ),
    },
  ]

  return (
    <div className={cn('content-card flex flex-col gap-4 p-4', className)}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-label font-semibold text-fg-primary">{t('filters.title')}</h2>
        <Button variant="ghost" size="sm" className="text-caption" onClick={reset}>
          {t('filters.reset')}
        </Button>
      </div>

      {groups.map((group) => (
        <FilterGroup key={group.id} title={group.title}>
          {group.content}
        </FilterGroup>
      ))}
    </div>
  )
}

/** Группа фильтра: раскрыта по умолчанию, сворачивается для компактности на мобиле. */
function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="border-t border-stroke-subtle pt-3 first-of-type:border-0 first-of-type:pt-0">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="text-caption font-medium uppercase tracking-wide text-fg-tertiary">{title}</span>
        <ChevronDown
          className={cn(
            'size-3.5 shrink-0 text-fg-tertiary transition-transform duration-fast',
            open && 'rotate-180',
          )}
          aria-hidden="true"
        />
      </button>
      {open && <div className="mt-2.5">{children}</div>}
    </div>
  )
}
