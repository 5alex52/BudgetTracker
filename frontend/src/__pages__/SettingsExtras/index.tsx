import { useMemo, useState } from 'react'
import { Plus, Play, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { ApiError, templatesApi, usersApi } from '@/api'
import { useFinanceStore } from '@/store/finance'
import { useAuthStore } from '@/store/auth'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { FilterSelect } from '@/components/ui/overlays'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'

/** Цвета меток: сервер хранит hex, палитра фиксирована. */
const TAG_COLORS = [
  '#5b8fd6',
  '#3aa76d',
  '#e0913c',
  '#e06fa0',
  '#8b6fd6',
  '#d94b4b',
  // Дополнительные оттенки — те же, что в палитре категорий
  '#c9a227',
  '#7cb342',
  '#009688',
  '#607d8b',
]

/**
 * «Настройки → Метки».
 *
 * Метка живёт на сервере и связана с записями через `transaction_tags`,
 * поэтому счётчик использования считает сервис, а не клиент.
 */
export function SettingsTagsPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const tags = useFinanceStore((state) => state.tags)
  const createTag = useFinanceStore((state) => state.createTag)
  const deleteTag = useFinanceStore((state) => state.deleteTag)

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [color, setColor] = useState(TAG_COLORS[0])
  const [pending, setPending] = useState(false)

  const add = async () => {
    if (!name.trim()) return
    setPending(true)
    try {
      await createTag({ name: name.trim(), color })
      toast({ title: t('settings.tags.add'), description: name.trim(), tone: 'success' })
      setName('')
      setColor(TAG_COLORS[0])
      setOpen(false)
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const remove = async (id: number, label: string) => {
    try {
      await deleteTag(id)
      toast({ title: t('state.deleted'), description: label, tone: 'info' })
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  return (
    <SettingsLayout
      title={t('settings.tags')}
      actions={
        <Button className="gap-1.5" onClick={() => setOpen(true)}>
          <Plus className="size-4" aria-hidden="true" />
          {t('settings.tags.add')}
        </Button>
      }
    >
      <Card className="overflow-hidden p-0">
        {tags.length === 0 && (
          <p className="px-4 py-8 text-center text-label text-fg-tertiary">{t('state.empty')}</p>
        )}
        <ul>
          {tags.map((tag, index) => (
            <li
              key={tag.id}
              className={cn(
                'flex items-center gap-3 px-4 py-2.5',
                index > 0 && 'border-t border-stroke-subtle',
              )}
            >
              <span
                className="size-2.5 rounded-pill"
                style={{ backgroundColor: tag.color }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate text-label font-medium text-fg-primary">
                {tag.name}
              </span>
              <span className="text-caption text-fg-tertiary">
                {t('settings.tags.usage')}: {tag.transactions_count}
              </span>
              <Button
                variant="ghost"
                size="sm"
                aria-label={t('common.delete')}
                onClick={() => void remove(tag.id, tag.name)}
              >
                <Trash2 className="size-4 text-fg-tertiary" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title={t('settings.tags.add')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={() => void add()} disabled={!name.trim() || pending}>
                {pending ? t('state.saving') : t('common.save')}
              </Button>
            </div>
          }
        >
          <div className="space-y-3">
            <Field label={t('settings.categories.name')}>
              <Input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
            </Field>
            <div>
              <p className="mb-2 text-label font-medium text-fg-primary">
                {t('settings.categories.color')}
              </p>
              <div className="flex flex-wrap gap-2">
                {TAG_COLORS.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setColor(item)}
                    aria-label={item}
                    aria-pressed={color === item}
                    className={cn(
                      'size-6 rounded-pill border-2 transition-transform',
                      color === item ? 'scale-110 border-fg-primary' : 'border-transparent',
                    )}
                    style={{ backgroundColor: item }}
                  />
                ))}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}

/**
 * «Настройки → Шаблоны».
 *
 * Шаблон хранит сумму, счёт, категорию и метки. Кнопка «Создать запись»
 * вызывает `POST /templates/{id}/apply` — сервис сам создаёт запись и
 * увеличивает счётчик использования.
 */
export function SettingsTemplatesPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const templates = useFinanceStore((state) => state.templates)
  const accounts = useFinanceStore((state) => state.accounts)
  const categories = useFinanceStore((state) => state.categories)
  const deleteTemplate = useFinanceStore((state) => state.deleteTemplate)
  const createTemplate = useFinanceStore((state) => state.createTemplate)
  const reloadTemplates = useFinanceStore((state) => state.reloadTemplates)

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [accountId, setAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [pending, setPending] = useState(false)

  const accountById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account])),
    [accounts],
  )
  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  )

  const openCreate = () => {
    setName('')
    setAmount('')
    setAccountId(accounts.find((item) => !item.crypto)?.id ?? '')
    setCategoryId(categories[0] ? String(categories[0].id) : '')
    setOpen(true)
  }

  const save = async () => {
    const parsed = Number(amount.replace(',', '.'))
    const category = categoryById.get(Number(categoryId))
    if (!name.trim() || !Number.isFinite(parsed) || parsed <= 0 || !category || !accountId) return
    setPending(true)
    try {
      await createTemplate({
        name: name.trim(),
        type: category.type,
        amount: parsed,
        currency_id: accountById.get(accountId)?.currency ?? 'BYN',
        account_id: Number(accountId),
        category_id: category.id,
        note: null,
      })
      toast({ title: t('settings.templates.add'), description: name.trim(), tone: 'success' })
      setOpen(false)
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const apply = async (id: number) => {
    try {
      await templatesApi.applyTemplate(id)
      toast({ title: t('templates.applied'), tone: 'success' })
      await reloadTemplates()
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  const remove = async (id: number, label: string) => {
    try {
      await deleteTemplate(id)
      toast({ title: t('state.deleted'), description: label, tone: 'info' })
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  return (
    <SettingsLayout
      title={t('settings.templates')}
      actions={
        <Button className="gap-1.5" onClick={openCreate} disabled={accounts.length === 0}>
          <Plus className="size-4" aria-hidden="true" />
          {t('settings.templates.add')}
        </Button>
      }
    >
      <Card className="overflow-hidden p-0">
        {templates.length === 0 && (
          <p className="px-4 py-8 text-center text-label text-fg-tertiary">{t('state.empty')}</p>
        )}
        <ul>
          {templates.map((item, index) => {
            const account = accountById.get(String(item.account_id))
            const category = categoryById.get(item.category_id)
            return (
              <li
                key={item.id}
                className={cn(
                  'flex flex-wrap items-center gap-3 px-4 py-2.5',
                  index > 0 && 'border-t border-stroke-subtle',
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-label font-medium text-fg-primary">{item.name}</p>
                  <p className="truncate text-caption text-fg-tertiary">
                    {item.type === 'income' ? t('recordForm.income') : t('recordForm.expense')} ·{' '}
                    {category?.name ?? '—'} · {account?.name ?? '—'} · {item.amount} {item.currency_id}
                  </p>
                </div>
                <span className="text-caption text-fg-tertiary">
                  {t('templates.usage', { count: item.usage_count })}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 text-caption text-accent"
                  onClick={() => void apply(item.id)}
                >
                  <Play className="size-3.5" aria-hidden="true" />
                  {t('templates.apply')}
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t('common.delete')}
                  className="text-fg-tertiary hover:text-[var(--negative)]"
                  onClick={() => void remove(item.id, item.name)}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </Button>
              </li>
            )
          })}
        </ul>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title={t('settings.templates.add')}
          description={t('settings.templates.addHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={() => void save()} disabled={!name.trim() || pending}>
                {pending ? t('state.saving') : t('common.save')}
              </Button>
            </div>
          }
        >
          <div className="space-y-3">
            <Field label={t('settings.templates.name')}>
              <Input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
            </Field>
            <Field label={t('recordForm.amount')}>
              <Input
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                inputMode="decimal"
                placeholder="0,00"
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t('recordForm.account')}>
                <FilterSelect
                  ariaLabel={t('recordForm.account')}
                  value={accountId}
                  onValueChange={setAccountId}
                  options={accounts.filter((item) => !item.crypto).map((item) => ({ value: item.id, label: item.name }))}
                />
              </Field>
              <Field label={t('recordForm.category')}>
                <FilterSelect
                  ariaLabel={t('recordForm.category')}
                  value={categoryId}
                  onValueChange={setCategoryId}
                  options={categories.map((item) => ({ value: String(item.id), label: item.name }))}
                />
              </Field>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}

/**
 * «Настройки → Личные данные и конфиденциальность».
 *
 * Выгрузка данных — серверная (`GET /users/me/export`), поэтому в архив попадает
 * всё, включая записи и подписку. Удаление аккаунта требует пароль: без него
 * сервис отвечает 400, и это защита от случайного нажатия.
 */
export function SettingsPrivacyPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const signOut = useAuthStore((state) => state.signOut)

  const [exporting, setExporting] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)

  const exportData = async () => {
    setExporting(true)
    try {
      const payload = await usersApi.exportAccountData()
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'budgettracker-export.json'
      link.click()
      URL.revokeObjectURL(url)
      toast({ title: t('privacy.exported'), description: 'budgettracker-export.json', tone: 'success' })
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setExporting(false)
    }
  }

  const destroyAccount = async () => {
    if (!password) return
    setPending(true)
    try {
      await usersApi.deleteAccount(password)
      await signOut()
      toast({ title: t('privacy.deleted'), tone: 'info' })
    } catch (caught) {
      toast({
        title: t('privacy.deleteFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <SettingsLayout title={t('privacy.title')}>
      <div className="space-y-4">
        <Card>
          <h2 className="text-label font-semibold text-fg-primary">{t('privacy.portability')}</h2>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.exportHint')}</p>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.portabilityText')}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="subtle" onClick={() => void exportData()} disabled={exporting}>
              {exporting ? t('state.loading') : t('privacy.export')}
            </Button>
            <Button
              variant="ghost"
              className="gap-1.5 text-[var(--negative)]"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="size-4" aria-hidden="true" />
              {t('privacy.deleteTitle')}
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-label font-semibold text-fg-primary">{t('privacy.contact')}</h2>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.contactHint')}</p>
        </Card>
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent
          title={t('privacy.deleteTitle')}
          description={t('privacy.deleteHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setDeleteOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                className="bg-[var(--negative)] hover:bg-[var(--negative)]/90"
                disabled={!password || pending}
                onClick={() => void destroyAccount()}
              >
                {pending ? t('state.saving') : t('privacy.deleteTitle')}
              </Button>
            </div>
          }
        >
          <Field label={t('privacy.passwordPrompt')}>
            <Input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoFocus
            />
          </Field>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
