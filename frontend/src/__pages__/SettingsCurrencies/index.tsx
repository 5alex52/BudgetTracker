import { useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { currencies as initialCurrencies, type CurrencyRate } from '@/__shared__/mock/finance'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'

/**
 * «Настройки → Валюты».
 *
 * Как в референсе: сверху форма добавления новой валюты, ниже таблица ваших
 * валют с двусторонним курсом. Базовая валюта помечена и не удаляется.
 * Добавление работает локально — пишем в состояние демо-данных.
 */
export function SettingsCurrenciesPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const [list, setList] = useState<CurrencyRate[]>(initialCurrencies)
  const [name, setName] = useState('')
  const [rate, setRate] = useState('')
  const [invalid, setInvalid] = useState(false)
  const [editingCode, setEditingCode] = useState<string | null>(null)
  const [draft, setDraft] = useState<CurrencyRate | null>(null)

  const base = list.find((item) => item.base) ?? list[0]

  const add = () => {
    const code = name.trim().toUpperCase().slice(0, 3)
    if (!code) {
      setInvalid(true)
      return
    }
    const parsed = Number(rate.replace(',', '.')) || 1
    setList((prev) => [...prev, { code, name: name.trim(), rate: parsed }])
    setName('')
    setRate('')
    setInvalid(false)
    toast({ title: t('settings.currencies.added'), description: `${code} = ${parsed} ${base.code}`, tone: 'success' })
  }

  return (
    <SettingsLayout title={t('settings.currencies')} subtitle={t('settings.currencies.rate')}>
      <div className="space-y-4">
        <Card>
          <CardHeader title={t('settings.currencies.addNew')} />
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <Field label={t('settings.currencies.name')} error={invalid ? t('recordForm.required') : undefined} className="min-w-56 flex-1">
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t('settings.currencies.name')}
                invalid={invalid}
              />
            </Field>
            <Field label={t('settings.currencies.rate')} className="w-40">
              <Input value={rate} onChange={(event) => setRate(event.target.value)} placeholder="2,97" inputMode="decimal" />
            </Field>
            <Button onClick={add} className="gap-1.5">
              <Plus className="size-4" aria-hidden="true" />
              {t('common.add')}
            </Button>
          </div>
        </Card>

        <Card className="overflow-hidden p-0">
          <div className="border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('settings.currencies.yours')}</h2>
          </div>

          <div className="overflow-x-auto">
          <table className="w-full border-collapse text-label">
            <caption className="sr-only">{t('settings.currencies.yours')}</caption>
            <thead>
              <tr>
                <th scope="col" className="px-3 py-2 text-left text-caption uppercase tracking-wide text-fg-tertiary sm:px-4">
                  {t('settings.categories.name')}
                </th>
                <th scope="col" className="px-3 py-2 text-left text-caption uppercase tracking-wide text-fg-tertiary sm:px-4">
                  {t('settings.currencies.rate')}
                </th>
                <th scope="col" className="px-4 py-2 text-right text-caption uppercase tracking-wide text-fg-tertiary">
                  <span className="sr-only">{t('accounts.rowMenu')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.map((item, index) => (
                <tr key={item.code} className={index > 0 ? 'border-t border-stroke-subtle' : undefined}>
                  <th scope="row" className="px-3 py-2.5 text-left font-normal sm:px-4">
                    <span className="flex items-center gap-2">
                      <span className="grid size-7 place-items-center rounded-pill bg-surface-2 text-caption font-semibold text-fg-primary">
                        {item.code.slice(0, 2)}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-label font-medium text-fg-primary">
                          {item.code} · {item.name}
                        </span>
                        {item.base && (
                          <span className="block text-caption text-fg-tertiary">{t('settings.currencies.base')}</span>
                        )}
                      </span>
                    </span>
                  </th>
                  <td className="px-3 py-2.5 text-fg-secondary sm:px-4">
                    {item.base ? (
                      <span className="text-caption text-fg-tertiary">—</span>
                    ) : (
                      <span className="flex flex-wrap gap-x-3 gap-y-0.5 text-caption">
                        <span className="hidden sm:inline">
                          {base.code} 1 = {item.code} {(1 / item.rate).toFixed(4)}
                        </span>
                        <span>
                          {item.code} 1 = {base.code} {item.rate.toFixed(3)}
                        </span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 sm:px-4">
                    {!item.base && (
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t('common.edit')}
                          title={t('common.edit')}
                          onClick={() => {
                            setEditingCode(item.code)
                            setDraft({ ...item })
                          }}
                        >
                          <Pencil className="size-3.5 text-accent" aria-hidden="true" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t('common.delete')}
                          title={t('common.delete')}
                          onClick={() => setList((prev) => prev.filter((row) => row.code !== item.code))}
                        >
                          <Trash2 className="size-3.5 text-[var(--negative)]" aria-hidden="true" />
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </Card>
      </div>

      {/* Окно редактирования валюты */}
      <Dialog
        open={Boolean(draft)}
        onOpenChange={(next) => {
          if (!next) {
            setDraft(null)
            setEditingCode(null)
          }
        }}
      >
        <DialogContent
          title={t('common.edit')}
          description={editingCode ?? undefined}
          footer={
            <div className="flex flex-wrap justify-between gap-2">
              <Button
                variant="ghost"
                className="text-[var(--negative)]"
                onClick={() => {
                  if (!draft) return
                  setList((prev) => prev.filter((row) => row.code !== draft.code))
                  setDraft(null)
                  setEditingCode(null)
                }}
              >
                {t('common.delete')}
              </Button>
              <div className="flex gap-2">
                <Button variant="subtle" onClick={() => setDraft(null)}>
                  {t('common.cancel')}
                </Button>
                <Button
                  onClick={() => {
                    if (!draft) return
                    setList((prev) => prev.map((row) => (row.code === draft.code ? draft : row)))
                    toast({ title: t('common.save'), description: `${draft.code}`, tone: 'success' })
                    setDraft(null)
                    setEditingCode(null)
                  }}
                >
                  {t('common.save')}
                </Button>
              </div>
            </div>
          }
        >
          {draft && (
            <div className="space-y-3">
              <Field label={t('settings.currencies.name')}>
                <Input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} autoFocus />
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label={t('settings.categories.name')}>
                  <Input
                    value={draft.code}
                    onChange={(event) => setDraft({ ...draft, code: event.target.value.toUpperCase().slice(0, 3) })}
                  />
                </Field>
                <Field label={`${t('settings.currencies.rate')} (${base.code})`} hint={draft.base ? t('settings.currencies.base') : undefined}>
                  <Input
                    value={String(draft.rate).replace('.', ',')}
                    onChange={(event) => setDraft({ ...draft, rate: Number(event.target.value.replace(',', '.')) || 0 })}
                    inputMode="decimal"
                    disabled={draft.base}
                  />
                </Field>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
