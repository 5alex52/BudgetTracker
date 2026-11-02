import { useMemo, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { accounts, categories } from '@/__shared__/mock/finance'
import { Checkbox } from '@/components/ui/toggles'
import { Slider } from '@/components/ui/toggles'
import { Switch } from '@/components/ui/toggles'
import { Button } from '@/components/ui/button'
import { FilterSelect } from '@/components/ui/overlays'
import { CategoryIcon } from '@/__shared__/utils/category-icon'

/**
 * Панель фильтров записей — 11 групп из референса.
 *
 * На десктопе живёт в стеклянном сайдбаре, на мобиле — в том же виде внутри
 * Sheet: разметка одна, меняется только контейнер. Это осознанное решение:
 * дублировать 11 групп ради «мобильной» версии — источник расхождений.
 */
export function FilterPanel({
  onReset,
  className,
}: {
  onReset?: () => void
  className?: string
}) {
  const { t } = useI18n()
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([])
  const [selectedCategories, setSelectedCategories] = useState<string[]>([])
  const [range, setRange] = useState<[number, number]>([0, 5000])
  const [includeTransfers, setIncludeTransfers] = useState(true)
  const [onlyAcknowledged, setOnlyAcknowledged] = useState(false)
  const [currency, setCurrency] = useState('all')
  const [recordType, setRecordType] = useState('all')
  const [status, setStatus] = useState('all')
  const [paymentType, setPaymentType] = useState('all')

  const toggleAccount = (id: string) =>
    setSelectedAccounts((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  const toggleCategory = (id: string) =>
    setSelectedCategories((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  const groups = useMemo(
    () => [
      {
        id: 'accounts',
        title: t('filters.accounts'),
        content: (
          <div className="space-y-2.5">
            {accounts.slice(0, 6).map((account) => (
              <Checkbox
                key={account.id}
                checked={selectedAccounts.includes(account.id)}
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
            {categories.slice(0, 10).map((category) => (
              <Checkbox
                key={category.id}
                checked={selectedCategories.includes(category.id)}
                onCheckedChange={() => toggleCategory(category.id)}
                label={
                  <span className="flex items-center gap-1.5">
                    <CategoryIcon name={category.icon} className="size-3.5" />
                    {category.name}
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
          <FilterSelect
            ariaLabel={t('filters.tags')}
            value="all"
            onValueChange={() => undefined}
            options={[{ value: 'all', label: t('common.all') }]}
          />
        ),
      },
      {
        id: 'currencies',
        title: t('filters.currencies'),
        content: (
          <FilterSelect
            ariaLabel={t('filters.currencies')}
            value={currency}
            onValueChange={setCurrency}
            options={[
              { value: 'all', label: t('filters.allCurrencies') },
              { value: 'BYN', label: 'BYN' },
              { value: 'RUB', label: 'RUB' },
              { value: 'USD', label: 'USD' },
              { value: 'EUR', label: 'EUR' },
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
            onValueChange={setRecordType}
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
              onValueChange={(next) => setRange([next[0] ?? 0, next[1] ?? 5000])}
              min={0}
              max={5000}
              step={50}
              showValues
              aria-label={t('filters.amountRange')}
            />
            <p className="mt-2 text-caption text-fg-tertiary">{t('filters.amountAbsolute')}</p>
          </div>
        ),
      },
      {
        id: 'transfers',
        title: t('filters.transfers'),
        content: (
          <Switch
            checked={includeTransfers}
            onCheckedChange={setIncludeTransfers}
            label={t('filters.includingTransfers')}
          />
        ),
      },
      {
        id: 'statuses',
        title: t('filters.recordStatuses'),
        content: (
          <FilterSelect
            ariaLabel={t('filters.recordStatuses')}
            value={status}
            onValueChange={setStatus}
            options={[
              { value: 'all', label: t('filters.allStatuses') },
              { value: 'ack', label: t('recordForm.acknowledged') },
              { value: 'pending', label: t('recordForm.paymentStatus') },
            ]}
          />
        ),
      },
      {
        id: 'payments',
        title: t('filters.paymentTypes'),
        content: (
          <FilterSelect
            ariaLabel={t('filters.paymentTypes')}
            value={paymentType}
            onValueChange={setPaymentType}
            options={[
              { value: 'all', label: t('filters.allPaymentTypes') },
              { value: 'cash', label: t('recordForm.cash') },
              { value: 'card', label: t('recordForm.paymentType') },
            ]}
          />
        ),
      },
      {
        id: 'ack',
        title: t('recordForm.acknowledged'),
        content: (
          <Switch
            checked={onlyAcknowledged}
            onCheckedChange={setOnlyAcknowledged}
            label={t('recordForm.acknowledged')}
          />
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedAccounts, selectedCategories, range, includeTransfers, onlyAcknowledged, currency, recordType, status, paymentType, t],
  )

  return (
    <div className={cn('content-card flex flex-col gap-4 p-4', className)}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-label font-semibold text-fg-primary">{t('filters.title')}</h2>
        <Button variant="ghost" size="sm" className="text-caption" onClick={onReset}>
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
