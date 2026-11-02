import { useMemo, useState } from 'react'
import { Plus } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { categories, subcategories as initialSubs, type Subcategory } from '@/__shared__/mock/finance'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { readableOnTint } from '@/__shared__/utils/contrast'
import { useTheme } from '@/hooks/useTheme'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { CategoryIcon } from '@/__shared__/utils/category-icon'

const CHARACTER: Array<{ value: Subcategory['character']; key: TranslationKey }> = [
  { value: 'essential', key: 'settings.categories.characterEssential' },
  { value: 'optional', key: 'settings.categories.characterOptional' },
  { value: 'income', key: 'settings.categories.characterIncome' },
]

const PALETTE = ['#e0913c', '#e06fa0', '#3aa76d', '#2ba7d6', '#d94b4b', '#8b6fd6', '#c26bd6', '#5b8fd6']

/**
 * «Настройки → Категории».
 *
 * Слева — родительские категории, справа — подкатегории выбранной.
 * Редактирование открывается в стеклянном модале: название, цвет, иконка,
 * характер расходов и переключатель «Скрыть» — как в референсе.
 * Добавление подкатегории работает на локальном состоянии.
 */
export function SettingsCategoriesPage() {
  const { t } = useI18n()
  const { isDark } = useTheme()
  const { toast } = useToast()
  const [activeParent, setActiveParent] = useState(categories[0]?.id ?? 'food')
  const [subs, setSubs] = useState<Subcategory[]>(initialSubs)
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState<Subcategory | null>(null)

  const rows = useMemo(() => subs.filter((item) => item.parent === activeParent), [subs, activeParent])
  const parent = categories.find((item) => item.id === activeParent)

  const openEdit = (item: Subcategory) => {
    setDraft({ ...item })
    setCreating(false)
  }

  const openCreate = () => {
    setCreating(true)
    setDraft({
      id: `sc-${Date.now()}`,
      name: '',
      parent: activeParent,
      icon: 'box',
      color: PALETTE[0],
      character: 'optional',
    })
  }

  const save = () => {
    if (!draft || !draft.name.trim()) return
    setSubs((prev) => {
      const exists = prev.some((item) => item.id === draft.id)
      return exists ? prev.map((item) => (item.id === draft.id ? draft : item)) : [...prev, draft]
    })
    setCreating(false)
    setDraft(null)
    toast({ title: t('settings.categories.saved'), description: draft.name, tone: 'success' })
  }

  return (
    <SettingsLayout
      title={t('settings.categories')}
      subtitle={parent?.name}
      actions={
        <Button className="gap-1.5" onClick={openCreate}>
          <Plus className="size-4" aria-hidden="true" />
          {t('settings.categories.addSub')}
        </Button>
      }
    >
      <div className="grid gap-4 md:grid-cols-[260px_1fr]">
        {/* Родительские категории */}
        <Card className="h-fit p-2">
          <ul>
            {categories.map((item) => {
              const count = subs.filter((sub) => sub.parent === item.id).length
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setActiveParent(item.id)}
                    aria-pressed={activeParent === item.id}
                    className={cn(
                      'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-label transition-colors duration-fast',
                      activeParent === item.id
                        ? 'bg-accent/12 font-medium text-accent'
                        : 'text-fg-secondary hover:bg-surface-2 hover:text-fg-primary',
                    )}
                  >
                    <span
                      className="grid size-6 shrink-0 place-items-center rounded-pill"
                      style={{
                        backgroundColor: `${item.color}22`,
                        color: readableOnTint(item.color, { dark: isDark, threshold: 3 }),
                      }}
                    >
                      <CategoryIcon name={item.icon} className="size-3.5" />
                    </span>
                    <span className="min-w-0 flex-1 truncate">{item.name}</span>
                    <span className="text-caption text-fg-tertiary">{count}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </Card>

        {/* Подкатегории */}
        <Card className="overflow-hidden p-0">
          <div className="border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('settings.categories.subcategories')}</h2>
          </div>
          {rows.length === 0 && (
            <p className="px-4 py-8 text-center text-label text-fg-tertiary">{t('settings.categories.empty')}</p>
          )}
          <ul>
            {rows.map((item, index) => (
              <li
                key={item.id}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 transition-colors duration-fast hover:bg-surface-2/70',
                  index > 0 && 'border-t border-stroke-subtle',
                )}
              >
                <span
                  className="grid size-8 shrink-0 place-items-center rounded-pill"
                  style={{
                    backgroundColor: `${item.color}22`,
                    color: readableOnTint(item.color, { dark: isDark, threshold: 3 }),
                  }}
                >
                  <CategoryIcon name={item.icon} className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className={cn('truncate text-label font-medium', item.hidden ? 'text-fg-tertiary line-through' : 'text-fg-primary')}>
                    {item.name}
                  </p>
                  <p className="text-caption text-fg-tertiary">
                    {t(CHARACTER.find((entry) => entry.value === item.character)?.key ?? 'settings.categories.characterOptional')}
                    {item.hidden && ` · ${t('settings.categories.hide')}`}
                  </p>
                </div>
                <Button variant="ghost" size="sm" className="text-caption text-accent" onClick={() => openEdit(item)}>
                  {t('common.edit')}
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Модал редактирования/создания подкатегории */}
      <Dialog
        open={Boolean(draft)}
        onOpenChange={(open) => {
          if (!open) {
            setDraft(null)
                    setCreating(false)
          }
        }}
      >
        <DialogContent
          title={creating ? t('settings.categories.addSub') : t('common.edit')}
          description={parent?.name}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setDraft(null)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={save} disabled={!draft?.name.trim()}>
                {t('common.save')}
              </Button>
            </div>
          }
        >
          {draft && (
            <div className="space-y-4">
              <Field label={t('settings.categories.name')}>
                <Input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} autoFocus />
              </Field>

              <div>
                <p className="mb-2 text-label font-medium text-fg-primary">{t('settings.categories.color')}</p>
                <div className="flex flex-wrap gap-2">
                  {PALETTE.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setDraft({ ...draft, color })}
                      aria-label={color}
                      aria-pressed={draft.color === color}
                      className={cn(
                        'size-6 rounded-pill border-2 transition-transform',
                        draft.color === color ? 'border-fg-primary scale-110' : 'border-transparent hover:scale-105',
                      )}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-label font-medium text-fg-primary">{t('settings.categories.character')}</p>
                <SegmentedControl
                  aria-label={t('settings.categories.character')}
                  value={draft.character}
                  onValueChange={(value) => setDraft({ ...draft, character: value as Subcategory['character'] })}
                  items={CHARACTER.map((entry) => ({ value: entry.value, label: t(entry.key) }))}
                />
              </div>

              <Switch
                checked={Boolean(draft.hidden)}
                onCheckedChange={(next) => setDraft({ ...draft, hidden: next })}
                label={t('settings.categories.hide')}
              />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
