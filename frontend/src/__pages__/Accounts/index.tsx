import { useMemo, useState } from 'react'
import { Archive, Bitcoin, EyeOff, MoreHorizontal, Plus } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { useNavigate } from 'react-router-dom'
import type { Account, AccountKind } from '@/__shared__/types/models'
import { useFinanceStore } from '@/store/finance'
import { chipColors } from '@/__shared__/utils/contrast'
import { AccountDialog } from '@/components/accounts/AccountDialog'
import { AppShell } from '@/components/layout/AppShell'
import { Amount } from '@/components/data/Amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Switch } from '@/components/ui/toggles'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/overlays'

const KIND_ORDER: AccountKind[] = ['checking', 'savings', 'cash', 'credit_card', 'investment']

const KIND_LABEL: Record<AccountKind, TranslationKey> = {
  checking: 'accounts.type.checking',
  savings: 'accounts.type.savings',
  cash: 'accounts.type.cash',
  credit_card: 'accounts.type.credit_card',
  investment: 'accounts.type.investment',
}

/**
 * "Accounts": groups by account type, as in the reference, plus a group total.
 *
 * The group total is converted to the base currency at current rates:
 * balances in different currencies can't be added directly.
 */
export function AccountsPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const accounts = useFinanceStore((state) => state.accounts)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const rates = useFinanceStore((state) => state.rates)
  const loading = useFinanceStore((state) => state.loading)
  const [showArchived, setShowArchived] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)

  // The catalog rate is "how many currency units per 1 base unit", so
  // an account balance is converted to base by dividing by the rate.
  const ratesByCode = useMemo(
    () => new Map(rates.map((rate) => [rate.code, rate.base ? 1 : rate.rate])),
    [rates],
  )
  const toBase = (account: Account) => {
    const rate = ratesByCode.get(account.currency)
    return rate && rate > 0 ? account.balance / rate : 0
  }

  const openCreate = () => {
    setEditing(null)
    setDialogOpen(true)
  }
  const openEdit = (account: Account) => {
    setEditing(account)
    setDialogOpen(true)
  }

  const active = accounts.filter((account) => !account.archived)
  const groups = KIND_ORDER.map((kind) => ({
    kind,
    items: active.filter((account) => account.kind === kind),
  })).filter((group) => group.items.length > 0)
  // The archive is shown only in the main list (the "Archived" toggle), as a separate dimmed section
  const archivedList = showArchived ? accounts.filter((account) => account.archived) : []

  /** Account row: dimmed — a muted row in the archive section. */
  const renderRow = (account: Account, dimmed: boolean, first: boolean) => (
    <li key={account.id}>
      <div
        className={cn(
          'flex items-center gap-3 rounded-md px-2 py-2.5 transition-colors duration-fast hover:bg-surface-2/70',
          !first && 'border-t border-stroke-subtle',
          dimmed && 'opacity-55',
        )}
      >
        <span
          className="grid size-8 shrink-0 place-items-center rounded-pill text-caption font-semibold"
          style={(() => {
            const chip = chipColors(account.tint)
            return { backgroundColor: chip.backgroundColor, color: chip.color }
          })()}
          aria-hidden="true"
        >
          {account.name.slice(0, 1)}
        </span>

        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 truncate text-label font-medium text-fg-primary">
            {account.name}
            {account.crypto && (
              <Bitcoin className="size-3.5 shrink-0 text-fg-tertiary" aria-label={t('accounts.cryptoBadge')} />
            )}
          </p>
          <p className="flex flex-wrap items-center gap-1.5 text-caption text-fg-tertiary">
            {t(KIND_LABEL[account.kind])}
            {account.excluded && (
              <span className="inline-flex items-center gap-1 rounded-xs bg-surface-2 px-1.5 py-0.5">
                <EyeOff className="size-3" aria-hidden="true" />
                {t('accounts.excluded')}
              </span>
            )}
            {account.archived && (
              <span className="inline-flex items-center gap-1 rounded-xs bg-surface-2 px-1.5 py-0.5">
                <Archive className="size-3" aria-hidden="true" />
                {t('accounts.archived')}
              </span>
            )}
          </p>
        </div>

        <Amount value={account.balance} currency={account.currency} size="sm" tone="neutral" />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label={t('accounts.rowMenu')}>
              <MoreHorizontal className="size-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => navigate(`/accounts/${account.id}`)}>
              {t('accounts.openDetails')}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => openEdit(account)}>
              {t('common.edit')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  )

  return (
    <AppShell
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('accounts.title')}</h1>
          <Button
            size="sm"
            className="gap-1.5"
            onClick={openCreate}
          >
            <Plus className="size-4" aria-hidden="true" />
            {t('accounts.add')}
          </Button>
        </div>
      }
    >
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Switch checked={showArchived} onCheckedChange={setShowArchived} label={t('accounts.showArchived')} />
      </div>


      {loading && accounts.length === 0 && (
        <p className="text-label text-fg-tertiary" role="status">
          {t('state.loading')}
        </p>
      )}

      {!loading && groups.length === 0 && archivedList.length === 0 && (
        <Card>
          <p className="text-label text-fg-secondary">{t('state.empty')}</p>
          <Button size="sm" className="mt-3 gap-1.5" onClick={openCreate}>
            <Plus className="size-4" aria-hidden="true" />
            {t('accounts.add')}
          </Button>
        </Card>
      )}

      <div className="space-y-4">
        {groups.map((group) => {
          // Group total in the base currency: balances in different currencies
          // can't be added directly, so each is converted at its rate.
          // Excluded-from-statistics accounts don't contribute to the total.
          const total = group.items.reduce((sum, account) => (account.excluded ? sum : sum + toBase(account)), 0)
          return (
            <Card key={group.kind}>
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-overline uppercase tracking-wide text-fg-tertiary">
                  {t(KIND_LABEL[group.kind])}
                  <span className="ml-1.5 text-fg-tertiary/70">{group.items.length}</span>
                </h2>
                <Amount value={total} currency={baseCurrency} size="sm" tone="neutral" className="text-fg-secondary" />
              </div>

              <ul className="-mx-2">
                {group.items.map((account, index) => renderRow(account, false, index === 0))}
              </ul>
            </Card>
          )
        })}
      </div>

      {archivedList.length > 0 && (
        <Card className="mt-4">
          <h2 className="mb-3 text-overline uppercase tracking-wide text-fg-tertiary">
            {t('accounts.archived')}
            <span className="ml-1.5 text-fg-tertiary/70">{archivedList.length}</span>
          </h2>
          <ul className="-mx-2">
            {archivedList.map((account, index) => renderRow(account, true, index === 0))}
          </ul>
        </Card>
      )}

      <AccountDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        account={editing}
        onDeleted={() => navigate('/accounts')}
      />
    </AppShell>
  )
}
