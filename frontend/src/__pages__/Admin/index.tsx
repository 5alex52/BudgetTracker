import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Pencil, RefreshCw, Users } from 'lucide-react'
import { ApiError, adminApi } from '@/api'
import type { AdminUserDto } from '@/api/types'
import { useApiQuery, useDebounced } from '@/hooks/useApi'
import { useI18n } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Field, Input } from '@/components/ui/field'
import { Switch } from '@/components/ui/toggles'
import { useToast } from '@/components/ui/toast'

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
 * Админ-панель: сводка по пользователям и управление ими.
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

  const users = useApiQuery(
    () => adminApi.listAdminUsers({ search: debouncedSearch, offset, limit }),
    [debouncedSearch, offset],
  )

  const [editFor, setEditFor] = useState<AdminUserDto | null>(null)
  const [editForm, setEditForm] = useState({ firstname: '', lastname: '', email: '' })
  const [busy, setBusy] = useState<string | null>(null)

  const total = users.data?.total ?? 0
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + limit, total)

  const refresh = () => {
    users.reload()
  }

  const fail = (caught: unknown) => {
    toast({
      title: t('admin.actionFailed'),
      description: caught instanceof ApiError ? caught.detail : String(caught),
      tone: 'error',
    })
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
          <Button variant="subtle" size="sm" className="gap-1.5" onClick={refresh}>
            <RefreshCw className="size-4" aria-hidden="true" />
            {t('state.retry')}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Пользователи */}
        <Card className="p-0">
          <div className="flex flex-col gap-2 border-b border-stroke-subtle p-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="flex items-center gap-1.5 text-label font-semibold text-fg-primary">
              <Users className="size-4" aria-hidden="true" />
              {t('admin.users')}
              {users.data && (
                <span className="text-caption font-normal text-fg-tertiary">
                  ({number(users.data.total)})
                </span>
              )}
           </h2>
            <Input
              inputSize="sm"
              className="sm:w-72"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t('admin.search')}
              aria-label={t('admin.search')}

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

                  <div className="flex shrink-0 items-center gap-1">
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
