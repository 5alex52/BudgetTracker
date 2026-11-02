import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { rules as initialRules, tags as initialTags, type RuleItem, type TagItem } from '@/__shared__/mock/finance'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { Switch } from '@/components/ui/toggles'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { useAccountsStore } from '@/store/accounts'
import { useRecordsStore } from '@/store/records'

/**
 * «Настройки → Метки», «Шаблоны», «Автоматические правила», «Личные данные».
 * Содержимое взято из референсов; то, чего там нет, помечено как заготовка.
 */

export function SettingsTagsPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const [list, setList] = useState<TagItem[]>(initialTags)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')

  const add = () => {
    if (!name.trim()) return
    const tag: TagItem = { id: `t-${Date.now()}`, name: name.trim(), color: '#5b8fd6', usage: 0 }
    setList((prev) => [...prev, tag])
    setName('')
    setOpen(false)
    toast({ title: t('settings.tags.add'), description: tag.name, tone: 'success' })
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
        <ul>
          {list.map((tag, index) => (
            <li
              key={tag.id}
              className={`flex items-center gap-3 px-4 py-2.5 ${index > 0 ? 'border-t border-stroke-subtle' : ''}`}
            >
              <span className="size-2.5 rounded-pill" style={{ backgroundColor: tag.color }} aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate text-label font-medium text-fg-primary">{tag.name}</span>
              <span className="text-caption text-fg-tertiary">
                {t('settings.tags.usage')}: {tag.usage}
              </span>
              <Button
                variant="ghost"
                size="sm"
                aria-label={t('common.delete')}
                onClick={() => setList((prev) => prev.filter((row) => row.id !== tag.id))}
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
              <Button onClick={add} disabled={!name.trim()}>
                {t('common.save')}
              </Button>
            </div>
          }
        >
          <Field label={t('settings.categories.name')}>
            <Input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
          </Field>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}

const TEMPLATES = [
  { id: 'tpl-1', name: 'Продукты', detail: 'Расход · Продукты · Alfa' },
  { id: 'tpl-2', name: 'Такси', detail: 'Расход · Такси · наличные' },
  { id: 'tpl-3', name: 'Зарплата', detail: 'Доход · Зарплата · Alfa' },
]

export function SettingsTemplatesPage() {
  const { t } = useI18n()
  const [list, setList] = useState(TEMPLATES)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [detail, setDetail] = useState('')
  /** Шаблон, который правим: null — создаём новый */
  const [editing, setEditing] = useState<{ id: string; name: string; detail: string } | null>(null)

  const openCreate = () => {
    setEditing(null)
    setName('')
    setDetail('')
    setOpen(true)
  }
  const openEdit = (item: { id: string; name: string; detail: string }) => {
    setEditing(item)
    setName(item.name)
    setDetail(item.detail)
    setOpen(true)
  }
  const save = () => {
    const value = { name: name.trim(), detail: detail.trim() || '—' }
    setList((prev) =>
      editing
        ? prev.map((row) => (row.id === editing.id ? { ...row, ...value } : row))
        : [...prev, { id: `tpl-${Date.now()}`, ...value }],
    )
    setOpen(false)
  }

  return (
    <SettingsLayout
      title={t('settings.templates')}
      actions={
        <Button className="gap-1.5" onClick={openCreate}>
          <Plus className="size-4" aria-hidden="true" />
          {t('settings.templates.add')}
        </Button>
      }
    >
      <Card className="overflow-hidden p-0">
        <ul>
          {list.map((item, index) => (
            <li
              key={item.id}
              className={`flex items-center gap-3 px-4 py-2.5 ${index > 0 ? 'border-t border-stroke-subtle' : ''}`}
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-label font-medium text-fg-primary">{item.name}</p>
                <p className="truncate text-caption text-fg-tertiary">{item.detail}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-caption text-accent"
                onClick={() => openEdit(item)}
              >
                {t('common.edit')}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={t('common.delete')}
                className="text-fg-tertiary hover:text-[var(--negative)]"
                onClick={() => setList((prev) => prev.filter((row) => row.id !== item.id))}
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title={editing ? t('settings.templates.edit') : t('settings.templates.add')}
          description={editing ? editing.name : t('settings.templates.addHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button disabled={!name.trim()} onClick={save}>
                {t('common.save')}
              </Button>
            </div>
          }
        >
          <div className="space-y-3">
            <Field label={t('settings.templates.name')}>
              <Input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
            </Field>
            <Field label={t('settings.templates.detail')} hint={t('settings.templates.detailHint')}>
              <Input
                value={detail}
                onChange={(event) => setDetail(event.target.value)}
                placeholder={t('settings.templates.detailPlaceholder')}
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}

export function SettingsRulesPage() {
  const { t } = useI18n()
  const [ruleOpen, setRuleOpen] = useState(false)
  const [ruleMatch, setRuleMatch] = useState('')
  const [ruleCategory, setRuleCategory] = useState('')
  const [list, setList] = useState<RuleItem[]>(initialRules)

  return (
    <SettingsLayout title={t('settings.rules')} subtitle={t('settings.rules.hint')}>
      <div className="space-y-3">
        {list.map((rule) => (
          <Card key={rule.id} className="flex flex-wrap items-center gap-3 p-4">
            <div className="min-w-0 flex-1">
              <p className="text-label font-medium text-fg-primary">{rule.field}</p>
              <p className="text-caption text-fg-tertiary">{rule.match}</p>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-caption text-fg-tertiary">{t('settings.rules.then')}</p>
              <p className="text-label text-fg-primary">
                {rule.action}: {rule.value}
              </p>
            </div>
            <Switch
              checked={rule.enabled}
              onCheckedChange={(next) =>
                setList((prev) => prev.map((row) => (row.id === rule.id ? { ...row, enabled: next } : row)))
              }
              label={rule.enabled ? t('settings.on') : t('settings.off')}
            />
          </Card>
        ))}
        <Card className="flex flex-wrap items-center justify-between gap-3 border-dashed">
          <p className="text-label text-fg-secondary">{t('settings.rules.hint')}</p>
          <Button variant="subtle" className="gap-1.5" onClick={() => setRuleOpen(true)}>
            <Plus className="size-4" aria-hidden="true" />
            {t('settings.rules.add')}
          </Button>
        </Card>

        <Dialog open={ruleOpen} onOpenChange={setRuleOpen}>
          <DialogContent
            title={t('settings.rules.add')}
            description={t('settings.rules.formHint')}
            footer={
              <div className="flex justify-end gap-2">
                <Button variant="subtle" onClick={() => setRuleOpen(false)}>
                  {t('common.cancel')}
                </Button>
                <Button
                  disabled={!ruleMatch.trim() || !ruleCategory.trim()}
                  onClick={() => {
                    setList((prev) => [
                      ...prev,
                      {
                        id: `rule-${Date.now()}`,
                        field: 'description',
                        match: ruleMatch.trim(),
                        action: 'category',
                        value: ruleCategory.trim(),
                        enabled: true,
                      },
                    ])
                    setRuleMatch('')
                    setRuleCategory('')
                    setRuleOpen(false)
                  }}
                >
                  {t('common.add')}
                </Button>
              </div>
            }
          >
            <div className="space-y-3">
              <Field label={t('settings.rules.match')} hint={t('settings.rules.matchHint')}>
                <Input
                  value={ruleMatch}
                  onChange={(event) => setRuleMatch(event.target.value)}
                  placeholder="PYATEROCHKA"
                  autoFocus
                />
              </Field>
              <Field label={t('settings.rules.assign')}>
                <Input
                  value={ruleCategory}
                  onChange={(event) => setRuleCategory(event.target.value)}
                  placeholder={t('settings.rules.assignPlaceholder')}
                />
              </Field>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </SettingsLayout>
  )
}

export function SettingsPrivacyPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const [messages, setMessages] = useState(true)
  const [dpoOpen, setDpoOpen] = useState(false)

  /** Выгрузка данных: тот же клиентский экспорт, что и в «Записях». */
  const exportDataArchive = () => {
    const payload = {
      exportedAt: new Date().toISOString(),
      records: useRecordsStore.getState().items,
      accounts: useAccountsStore.getState().items,
      tags: initialTags,
      rules: initialRules,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'budgettracker-data.json'
    link.click()
    URL.revokeObjectURL(url)
    toast({ title: t('privacy.exportData'), description: 'budgettracker-data.json', tone: 'success' })
  }

  return (
    <SettingsLayout title={t('privacy.title')}>
      <div className="space-y-4">
        <Card>
          <h2 className="text-label font-semibold text-fg-primary">{t('privacy.documents')}</h2>
          <ul className="mt-2 space-y-2">
            <li>
              <a href="#privacy" className="text-label text-accent hover:underline">
                {t('settings.privacy')}
              </a>
            </li>
            <li>
              <a href="#terms" className="text-label text-accent hover:underline">
                {t('privacy.terms')}
              </a>
            </li>
          </ul>
        </Card>

        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-label font-semibold text-fg-primary">{t('privacy.messages')}</h2>
            <Switch checked={messages} onCheckedChange={setMessages} label={messages ? t('settings.on') : t('settings.off')} />
          </div>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.messagesHint')}</p>
        </Card>

        <Card>
          <h2 className="text-label font-semibold text-fg-primary">{t('privacy.portability')}</h2>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.portabilityText')}</p>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.forgotten')}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="subtle" onClick={() => exportDataArchive()}>
              {t('privacy.exportData')}
            </Button>
            <Button variant="ghost" className="text-accent" onClick={() => setDpoOpen(true)}>
              {t('privacy.dpo')}
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-label font-semibold text-fg-primary">{t('privacy.contact')}</h2>
          <p className="mt-2 text-label text-fg-secondary">{t('privacy.contactHint')}</p>
        </Card>
      </div>

      <Dialog open={dpoOpen} onOpenChange={setDpoOpen}>
        <DialogContent
          title={t('privacy.dpo')}
          description={t('privacy.dpoHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setDpoOpen(false)}>
                {t('privacy.dpoClose')}
              </Button>
              <Button onClick={() => window.open('mailto:dpo@budgettracker.example', '_self')}>dpo@budgettracker.example</Button>
            </div>
          }
        >
          <ul className="space-y-2 text-label text-fg-secondary">
            <li>{t('privacy.dpoRequest1')}</li>
            <li>{t('privacy.dpoRequest2')}</li>
            <li>{t('privacy.dpoRequest3')}</li>
          </ul>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
