import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  Pencil,
  RefreshCw,
  Search,
  ShieldCheck,
  Users,
  Wallet,
} from 'lucide-react'
import { ApiError, adminApi, billingApi } from '@/api'
import type { AdminUserDto, SubscriptionStatusValue } from '@/api/types'
import { cn } from '@/__shared__/utils/cn'
import { useApiQuery, useDebounced } from '@/hooks/useApi'
import { useI18n, type TranslationKey } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { AppShell } from '@/components/layout/AppShell'
import { Amount } from '@/components/data/Amount'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Field, Input } from '@/components/ui/field'
import { FilterSelect } from '@/components/ui/overlays'
import { Switch } from '@/components/ui/toggles'
import { useToast } from '@/components/ui/toast'

const STATUS_KEY: Record<SubscriptionStatusValue, TranslationKey> = {
  active: 'admin.status.active',
  canceled: 'admin.status.canceled',
  expired: 'admin.status.canceled',
  pending: 'admin.status.past_due',
}

function formatDate(iso: string | null, locale: 'ru' | 'en') {
  if (!iso) return '—'
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

function initials(user: AdminUserDto) {
  const source = user.fullname || user.email
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()
}

/**
 * Админ-панель: сводка по подпискам и управление пользователями.
 * Все запросы защищены на сервере — сюда попадают только суперпользователи.
 */
export function AdminPage() {
  const { t, locale, number } = useI18n()
  const { toast } = useToast()
  const currentUser = useAuthStore((state) => state.user)

  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounced(search)
  const [offset, setOffset] = useState(0)
  const limit = 20

  useEffect(() => {
    setOffset(0)
  }, [debouncedSearch])

  const stats = useApiQuery(() => adminApi.getAdminStats(), [])
  const users = useApiQuery(
    () => adminApi.listAdminUsers({ search: debouncedSearch, offset, limit }),
    [debouncedSearch, offset],
  )
  const plans = useApiQuery(() => billingApi.listPlans(), [])
  const timeline = useApiQuery(() => adminApi.getSubscriptionTimeline(30), [])

  const [grantFor, setGrantFor] = useState<AdminUserDto | null>(null)
  const [grantPlan, setGrantPlan] = useState('')
  const [revokeFor, setRevokeFor] = useState<AdminUserDto | null>(null)
  const [editFor, setEditFor] = useState<AdminUserDto | null>(null)
  const [editForm, setEditForm] = useState({ firstname: '', lastname: '', email: '' })
  const [busy, setBusy] = useState<string | null>(null)

  const paidPlans = (plans.data ?? []).filter((plan) => plan.period !== 'none')
  const total = users.data?.total ?? 0
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + limit, total)

  const refresh = () => {
    stats.reload()
    users.reload()
  }

  const fail = (caught: unknown) => {
    toast({
      title: t('admin.actionFailed'),
      description: caught instanceof ApiError ? caught.detail : String(caught),
      tone: 'error',
    })
  }

  const openGrant = (user: AdminUserDto) => {
    setGrantFor(user)
    setGrantPlan(paidPlans[0]?.code ?? '')
  }

  const toggleActive = async (user: AdminUserDto, active: boolean) => {
    setBusy(`active-${user.id}`)
    try {
      await adminApi.updateAdminUser(user.id, { is_active: active })
      toast({ title: t('admin.statusChanged'), tone: 'success' })
      refresh()
    } catch (caught) {
      fail(caught)
    } finally {
      setBusy(null)
    }
  }

  const grant = async () => {
    if (!grantFor || !grantPlan) return
    setBusy('grant')
    try {
      await adminApi.grantAdminSubscription(grantFor.id, grantPlan)
      toast({ title: t('admin.granted'), tone: 'success' })
      setGrantFor(null)
      refresh()
    } catch (caught) {
      fail(caught)
    } finally {
      setBusy(null)
    }
  }

  const revoke = async () => {
    if (!revokeFor) return
    setBusy('revoke')
    try {
      await adminApi.revokeAdminSubscription(revokeFor.id)
      toast({ title: t('admin.revoked'), tone: 'success' })
      setRevokeFor(null)
      refresh()
    } catch (caught) {
      fail(caught)
    } finally {
      setBusy(null)
    }
  }

  const openEdit = (user: AdminUserDto) => {
    const parts = user.fullname.split(/\s+/)
    setEditFor(user)
    setEditForm({
      firstname: parts[0] ?? '',
      lastname: parts.slice(1).join(' ') ?? '',
      email: user.email,
    })
  }

  const saveEdit = async () => {
    if (!editFor) return
    setBusy('edit')
    try {
      await adminApi.updateAdminUser(editFor.id, {
        firstname: editForm.firstname.trim() || undefined,
        lastname: editForm.lastname.trim() || undefined,
        email: editForm.email.trim() || undefined,
      })
      toast({ title: t('admin.saved'), tone: 'success' })
      setEditFor(null)
      refresh()
    } catch (caught) {
      if (caught instanceof ApiError && caught.detail?.toLowerCase().includes('email')) {
        toast({ title: t('admin.emailInUse'), tone: 'error' })
      } else {
        fail(caught)
      }
    } finally {
      setBusy(null)
    }
  }

  return (
    <AppShell
      context={t('admin.title')}
      header={
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('admin.title')}</h1>
            <p className="mt-1 text-label text-fg-secondary">{t('admin.subtitle')}</p>
          </div>
          <Button variant="subtle" size="sm" className="gap-1.5" onClick={refresh} loading={stats.loading}>
            <RefreshCw className="size-4" aria-hidden="true" />
            {t('state.retry')}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Сводка */}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Card className="p-4">
            <p className="text-caption text-fg-tertiary">{t('admin.stats.users')}</p>
            <p className="mt-1 text-title font-semibold text-fg-primary">
              {stats.data ? number(stats.data.users_total) : '—'}
            </p>
            <p className="mt-1 text-caption text-fg-tertiary">
              {t('admin.stats.usersHint', { count: stats.data?.users_new_30d ?? 0 })}
            </p>
          </Card>
          <Card className="p-4">
            <p className="flex items-center gap-1.5 text-caption text-fg-tertiary">
              <ShieldCheck className="size-3.5" aria-hidden="true" />
              {t('admin.stats.premium')}
            </p>
            <p className="mt-1 text-title font-semibold text-fg-primary">
              {stats.data ? number(stats.data.premium_total) : '—'}
            </p>
            <p className="mt-1 text-caption text-fg-tertiary">
              {t('admin.free')}: {stats.data ? number(stats.data.free_total) : '—'}
            </p>
          </Card>
          <Card className="p-4">
            <p className="flex items-center gap-1.5 text-caption text-fg-tertiary">
              <Clock3 className="size-3.5" aria-hidden="true" />
              {t('admin.stats.expiring')}
            </p>
            <p className="mt-1 text-title font-semibold text-fg-primary">
              {stats.data ? number(stats.data.expiring_soon) : '—'}
            </p>
          </Card>
          <Card className="p-4">
            <p className="flex items-center gap-1.5 text-caption text-fg-tertiary">
              <Wallet className="size-3.5" aria-hidden="true" />
              {t('admin.stats.revenue')}
            </p>
            <p className="mt-1">
              <Amount value={stats.data?.revenue_30d ?? 0} currency="USD" size="md" tone="neutral" />
            </p>
          </Card>
        </div>

        {/* График подписок */}
        <Card className="p-4">
          <div className="mb-3">
            <h2 className="text-label font-semibold text-fg-primary">{t('admin.chart.subscriptions')}</h2>
            <p className="mt-0.5 text-caption text-fg-tertiary">{t('admin.chartHint')}</p>
          </div>
          {timeline.data && timeline.data.points.length > 0 ? (
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeline.data.points} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="premiumGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="freeGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--text-tertiary)" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="var(--text-tertiary)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 6" vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke="var(--text-tertiary)"
                    tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    minTickGap={20}
                    tickFormatter={(value: string) => {
                      const date = new Date(value)
                      return `${date.getDate()}.${String(date.getMonth() + 1).padStart(2, '0')}`
                    }}
                  />
                  <YAxis
                    stroke="var(--text-tertiary)"
                    tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={40}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload?.length) return null
                      const date = new Date(label as string)
                      const formatted = date.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US', {
                        day: 'numeric',
                        month: 'long',
                      })
                      return (
                        <div className="glass glass--sm rounded-sm px-2.5 py-1.5 text-caption text-fg-primary shadow-md">
                          <p className="mb-0.5 font-medium">{formatted}</p>
                          <p className="flex items-center gap-1.5 tabular-nums">
                            <span className="size-1.5 rounded-pill" style={{ backgroundColor: 'var(--accent)' }} />
                            <span className="text-fg-secondary">{t('admin.chart.premium')}:</span>
                            <span className="font-medium">{payload[0]?.value ?? 0}</span>
                          </p>
                          <p className="flex items-center gap-1.5 tabular-nums">
                            <span
                              className="size-1.5 rounded-pill"
                              style={{ backgroundColor: 'var(--text-tertiary)' }}
                            />
                            <span className="text-fg-secondary">{t('admin.chart.free')}:</span>
                            <span className="font-medium">{payload[1]?.value ?? 0}</span>
                          </p>
                        </div>
                      )
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="premium"
                    stroke="var(--accent)"
                    strokeWidth={2}
                    fill="url(#premiumGradient)"
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="free"
                    stroke="var(--text-tertiary)"
                    strokeWidth={2}
                    fill="url(#freeGradient)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-caption text-fg-tertiary">{t('state.empty')}</p>
          )}
        </Card>

        {/* Тарифы */}
        <Card className="p-0">
          <div className="border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('admin.stats.plans')}</h2>
          </div>
          <ul className="flex flex-wrap gap-2 p-4">
            {(stats.data?.plans ?? []).map((plan) => (
              <li
                key={plan.code}
                className="flex items-center gap-2 rounded-md bg-surface-2 px-3 py-2 text-label text-fg-secondary"
              >
                <span className="font-medium text-fg-primary">{plan.name}</span>
                <span className="text-caption text-fg-tertiary">{number(plan.count)}</span>
              </li>
            ))}
            {stats.data?.plans.length === 0 && (
              <li className="text-caption text-fg-tertiary">{t('state.empty')}</li>
            )}
          </ul>
        </Card>

        {/* Пользователи */}
        <Card className="p-0">
          <div className="flex flex-col gap-2 border-b border-stroke-subtle p-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="flex items-center gap-1.5 text-label font-semibold text-fg-primary">
              <Users className="size-4" aria-hidden="true" />
              {t('admin.users')}
            </h2>
            <Input
              inputSize="sm"
              className="sm:w-72"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t('admin.search')}
              aria-label={t('admin.search')}
              iconLeft={<Search className="size-4" aria-hidden="true" />}
            />
          </div>

          {users.error ? (
            <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
              <p className="text-label text-fg-secondary">{t('state.error')}</p>
              <Button variant="subtle" size="sm" onClick={users.reload}>
                {t('state.retry')}
              </Button>
            </div>
          ) : users.loading && !users.data ? (
            <p className="px-4 py-8 text-center text-caption text-fg-tertiary">{t('state.loading')}</p>
          ) : (users.data?.items.length ?? 0) === 0 ? (
            <p className="px-4 py-8 text-center text-caption text-fg-tertiary">{t('admin.empty')}</p>
          ) : (
            <ul>
              {users.data?.items.map((user) => (
                <li
                  key={user.id}
                  className="flex flex-col gap-3 border-t border-stroke-subtle px-4 py-3 first:border-t-0 sm:flex-row sm:items-center"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="grid size-8 shrink-0 place-items-center rounded-pill bg-accent-soft text-caption font-semibold uppercase text-accent-on-soft">
                        {initials(user)}
                      </span>
                      <p className="truncate text-label font-medium text-fg-primary">{user.fullname}</p>
                      {user.is_superuser && (
                        <span className="rounded-pill bg-surface-2 px-1.5 py-0.5 text-caption text-fg-tertiary">
                          admin
                        </span>
                      )}
                      {!user.is_active && (
                        <span className="rounded-pill bg-negative-soft px-1.5 py-0.5 text-caption text-negative">
                          {t('admin.blocked')}
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 truncate text-caption text-fg-tertiary">{user.email}</p>
                    <p className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-caption text-fg-tertiary">
                      <span>
                        {t('admin.registered')}: {formatDate(user.created_at, locale)}
                      </span>
                      <span>
                        {t('admin.lastLogin')}:{' '}
                        {user.last_login_at ? formatDate(user.last_login_at, locale) : t('admin.never')}
                      </span>
                      {!user.is_verified && <span className="text-[var(--warning)]">{t('admin.unverified')}</span>}
                    </p>
                  </div>

                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        'rounded-pill px-2 py-0.5 text-caption',
                        user.is_premium ? 'bg-accent/12 font-medium text-accent' : 'bg-surface-2 text-fg-secondary',
                      )}
                    >
                      {user.is_premium ? user.plan_name : t('admin.free')}
                    </span>
                    {user.is_premium && user.current_period_end && (
                      <span className="text-caption text-fg-tertiary">
                        {t('admin.until')} {formatDate(user.current_period_end, locale)}
                      </span>
                    )}
                    {!user.is_premium && user.plan_code !== 'free' && (
                      <span className="rounded-pill bg-warning-soft px-2 py-0.5 text-caption text-[var(--warning)]">
                        {t(STATUS_KEY[user.subscription_status])}
                      </span>
                    )}
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    {user.is_premium ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-caption text-[var(--negative)]"
                        onClick={() => setRevokeFor(user)}
                      >
                        {t('admin.revoke')}
                      </Button>
                    ) : (
                      <Button variant="subtle" size="sm" onClick={() => openGrant(user)} disabled={paidPlans.length === 0}>
                        {t('admin.grant')}
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => openEdit(user)} aria-label={t('admin.edit')}>
                      <Pencil className="size-4" aria-hidden="true" />
                    </Button>
                    <Switch
                      checked={user.is_active}
                      onCheckedChange={(active) => void toggleActive(user, active)}
                      disabled={user.is_superuser || busy === `active-${user.id}` || user.id === currentUser?.id}
                      aria-label={user.is_active ? t('admin.block') : t('admin.unblock')}
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-stroke-subtle px-4 py-3">
            <p className="text-caption text-fg-tertiary">{t('admin.page', { from, to, total })}</p>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="gap-1"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                <ChevronLeft className="size-4" aria-hidden="true" />
                {t('admin.prev')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1"
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
              >
                {t('admin.next')}
                <ChevronRight className="size-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Выдача подписки */}
      <Dialog open={grantFor !== null} onOpenChange={(open) => !open && setGrantFor(null)}>
        <DialogContent
          title={t('admin.grantTitle')}
          description={grantFor?.fullname}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setGrantFor(null)}>
                {t('common.cancel')}
              </Button>
              <Button size="sm" onClick={() => void grant()} loading={busy === 'grant'} disabled={!grantPlan}>
                {t('admin.grant')}
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <Field label={t('admin.plan')}>
              <FilterSelect
                value={grantPlan}
                onValueChange={setGrantPlan}
                ariaLabel={t('admin.plan')}
                options={paidPlans.map((plan) => ({ value: plan.code, label: plan.name }))}
              />
            </Field>
            <p className="text-caption text-fg-tertiary">{t('admin.grantHint')}</p>
          </div>
        </DialogContent>
      </Dialog>

      {/* Отзыв подписки */}
      <Dialog open={revokeFor !== null} onOpenChange={(open) => !open && setRevokeFor(null)}>
        <DialogContent
          title={t('admin.revokeTitle')}
          description={revokeFor?.fullname}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setRevokeFor(null)}>
                {t('common.cancel')}
              </Button>
              <Button variant="danger" size="sm" onClick={() => void revoke()} loading={busy === 'revoke'}>
                {t('admin.revoke')}
              </Button>
            </>
          }
        >
          <p className="text-label text-fg-secondary">{t('admin.revokeHint')}</p>
        </DialogContent>
      </Dialog>

      {/* Редактирование пользователя */}
      <Dialog open={editFor !== null} onOpenChange={(open) => !open && setEditFor(null)}>
        <DialogContent
          title={t('admin.editTitle')}
          description={editFor?.email}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setEditFor(null)}>
                {t('common.cancel')}
              </Button>
              <Button size="sm" onClick={() => void saveEdit()} loading={busy === 'edit'}>
                {t('common.save')}
              </Button>
            </>
          }
        >
          <div className="space-y-3">
            <Field label={t('admin.firstname')}>
              <Input
                value={editForm.firstname}
                onChange={(e) => setEditForm({ ...editForm, firstname: e.target.value })}
              />
            </Field>
            <Field label={t('admin.lastname')}>
              <Input
                value={editForm.lastname}
                onChange={(e) => setEditForm({ ...editForm, lastname: e.target.value })}
              />
            </Field>
            <Field label={t('admin.email')}>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
