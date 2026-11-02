import { useState } from 'react'
import { Archive, Eye, Lock, MoreHorizontal, Plus } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { useNavigate } from 'react-router-dom'
import type { AccountKind } from '@/__shared__/mock/finance'
import { useAccountsStore } from '@/store/accounts'
import { chipColors } from '@/__shared__/utils/contrast'
import { AccountDialog } from '@/components/accounts/AccountDialog'
import type { Account } from '@/__shared__/mock/finance'
import { AppShell } from '@/components/layout/AppShell'
import { Amount } from '@/components/data/Amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Switch } from '@/components/ui/toggles'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/overlays'

const KIND_ORDER: AccountKind[] = ['checking', 'savings', 'cash', 'general']

const KIND_LABEL: Record<AccountKind, string> = {
  checking: 'accounts.type.checking',
  savings: 'accounts.type.savings',
  cash: 'accounts.type.cash',
  general: 'accounts.type.general',
}

/**
 * «Счета»: три группы по типу счёта, как в референсе, плюс общий итог.
 * Исключённые из статистики и архивированные помечены текстом, а не только цветом.
 */
export function AccountsPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const accounts = useAccountsStore((state) => state.items)
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
        <Switch
          checked={showArchived}
          onCheckedChange={setShowArchived}
          label={t('accounts.showArchived')}
        />
      </div>

      <div className="space-y-4">
        {groups.map((group) => {
          const total = group.items.reduce(
            (sum, account) => sum + (account.currency === 'BYN' ? account.balance : 0),
            0,
          )
          return (
            <Card key={group.kind}>
              <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-overline uppercase tracking-wide text-fg-tertiary">
                  {t(KIND_LABEL[group.kind] as Parameters<typeof t>[0])}
                  <span className="ml-1.5 text-fg-tertiary/70">{group.items.length}</span>
                </h2>
                <Amount value={total} size="sm" tone="neutral" className="text-fg-secondary" />
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
                          {account.locked && <Lock className="size-3 shrink-0 text-fg-tertiary" aria-hidden="true" />}
                        </p>
                        <p className="flex flex-wrap items-center gap-1.5 text-caption text-fg-tertiary">
                          {t(KIND_LABEL[account.kind] as Parameters<typeof t>[0])}
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
                          <DropdownMenuItem onSelect={() => openEdit(account)}>{t('common.edit')}</DropdownMenuItem>
                          <DropdownMenuItem className="text-[var(--negative)]" onSelect={() => openEdit(account)}>
                            {t('common.delete')}
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
