import { useState } from 'react'
import { Archive, Eye, MoreHorizontal, Plus } from 'lucide-react'
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
 * «Счета»: группы по типу счёта, как в референсе, плюс итог группы.
 *
 * Итог считается только по базовой валюте: складывать рубли с долларами нельзя,
 * а сервер отдаёт балансы в валюте счёта. Для общего итога есть `/accounts/balance`.
 */
export function AccountsPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const accounts = useFinanceStore((state) => state.accounts)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const loading = useFinanceStore((state) => state.loading)
  const [showArchived, setShowArchived] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Account | null>(null)

  const openCreate = () => {
    setEditing(null)
    setDialogOpen(true)
  }
  const openEdit = (account: Account) => {
    setEditing(account)
    setDialogOpen(true)
  }

  const visible = accounts.filter((account) => showArchived || !account.archived)
  const groups = KIND_ORDER.map((kind) => ({
    kind,
    items: visible.filter((account) => account.kind === kind),
  })).filter((group) => group.items.length > 0)

  return (
    <AppShell
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('accounts.title')}</h1>
          <Button size="sm" className="gap-1.5" onClick={openCreate}>
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

      {!loading && groups.length === 0 && (
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
          const total = group.items.reduce(
            (sum, account) => sum + (account.currency === baseCurrency ? account.balance : 0),
            0,
          )
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
                {group.items.map((account, index) => (
                  <li key={account.id}>
                    <div
                      className={cn(
                        'flex items-center gap-3 rounded-md px-2 py-2.5 transition-colors duration-fast hover:bg-surface-2/70',
                        index > 0 && 'border-t border-stroke-subtle',
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
                        </p>
                        <p className="flex flex-wrap items-center gap-1.5 text-caption text-fg-tertiary">
                          {t(KIND_LABEL[account.kind])}
                          {account.excluded && (
                            <span className="inline-flex items-center gap-1 rounded-xs bg-surface-2 px-1.5 py-0.5">
                              <Eye className="size-3" aria-hidden="true" />
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
                ))}
              </ul>
            </Card>
          )
        })}
      </div>

      <AccountDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        account={editing}
        onDeleted={() => navigate('/accounts')}
      />
    </AppShell>
  )
}
