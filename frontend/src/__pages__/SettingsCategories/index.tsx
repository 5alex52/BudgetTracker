import { useEffect, useMemo, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { Category } from '@/__shared__/types/models'
import { ApiError } from '@/api'
import { useFinanceStore } from '@/store/finance'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { readableOnTint } from '@/__shared__/utils/contrast'
import { useTheme } from '@/hooks/useTheme'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl } from '@/components/ui/toggles'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { CategoryIcon } from '@/__shared__/utils/category-icon'

/** Палитра для выбора цвета категории. */
const PALETTE = ['#e0913c', '#e06fa0', '#3aa76d', '#2ba7d6', '#d94b4b', '#8b6fd6', '#c26bd6', '#5b8fd6']

/** Иконки, которые умеет рисовать `CategoryIcon`. */
const ICONS = [
  'utensils',
  'theater',
  'shopping-bag',
  'shopping-cart',
  'bus',
  'house',
  'book',
  'chef-hat',
  'gift',
  'landmark',
  'chart-line',
  'box',
  'wallet',
  'cash',
  'scale',
]

/**
 * «Настройки → Категории».
 *
 * Слева родительские категории, справа — подкатегории выбранной. Всё пишется
 * на сервер сразу: создание, переименование, цвет, иконка и удаление.
 * «Характер расходов» и «скрыть» из макета убраны: в модели данных категории
 * есть только название, тип, родитель, иконка и цвет.
 */
export function SettingsCategoriesPage() {
  const { t } = useI18n()
  const { isDark } = useTheme()
  const { toast } = useToast()

  const tree = useFinanceStore((state) => state.tree)
  const createCategory = useFinanceStore((state) => state.createCategory)
  const updateCategory = useFinanceStore((state) => state.updateCategory)
  const deleteCategory = useFinanceStore((state) => state.deleteCategory)

  const parents = tree
  const [activeParent, setActiveParent] = useState<number | null>(null)
  const [draft, setDraft] = useState<Category | null>(null)
  const [creating, setCreating] = useState(false)
  const [pending, setPending] = useState(false)

  /* Дерево приходит асинхронно: держим выбор валидным при первой загрузке */
  useEffect(() => {
    if (activeParent === null && parents[0]) setActiveParent(parents[0].id)
  }, [parents, activeParent])

  const parent = useMemo(() => parents.find((item) => item.id === activeParent), [parents, activeParent])
  const rows = parent?.children ?? []
  const childCount = (category: Category) => category.children?.length ?? 0

  const openCreate = () => {
    if (!parent) return
    setCreating(true)
    setDraft({
      id: 0,
      name: '',
      icon: parent.icon,
      color: parent.color,
      type: parent.type,
      parentId: parent.id,
      transactionsCount: 0,
      children: [],
    })
  }

  const openEdit = (category: Category) => {
    setCreating(false)
    setDraft({ ...category })
  }

  const save = async () => {
    if (!draft || !draft.name.trim()) return
    setPending(true)
    try {
      if (creating) {
        await createCategory({
          name: draft.name.trim(),
          type: draft.type,
          parent_id: draft.parentId ?? null,
          icon: draft.icon,
          color: draft.color,
        })
        toast({ title: t('settings.categories.saved'), description: draft.name, tone: 'success' })
      } else {
        await updateCategory(draft.id, { name: draft.name.trim(), icon: draft.icon, color: draft.color })
        toast({ title: t('state.saved'), description: draft.name, tone: 'success' })
      }
      setDraft(null)
      setCreating(false)
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

  const destroy = async (category: Category) => {
    setPending(true)
    try {
      await deleteCategory(category.id)
      toast({ title: t('state.deleted'), description: category.name, tone: 'info' })
      setDraft(null)
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

  return (
    <SettingsLayout
      title={t('settings.categories')}
      subtitle={parent?.name ?? t('state.loading')}
      actions={
        <Button className="gap-1.5" onClick={openCreate} disabled={!parent}>
          <Plus className="size-4" aria-hidden="true" />
          {t('settings.categories.addSub')}
        </Button>
      }
    >
      <div className="grid gap-4 md:grid-cols-[260px_1fr]">
        {/* Родительские категории */}
        <Card className="h-fit p-2">
          {parents.length === 0 && (
            <p className="px-2 py-4 text-caption text-fg-tertiary">{t('state.empty')}</p>
          )}
          <ul>
            {parents.map((item) => (
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
                  <span className="text-caption text-fg-tertiary">
                    {childCount(item) || (item.transactionsCount ?? 0)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        {/* Подкатегории выбранного родителя */}
        <Card className="overflow-hidden p-0">
          <div className="flex items-center justify-between gap-2 border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">
              {t('settings.categories.subcategories')}
            </h2>
            {parent && (
              <Button variant="ghost" size="sm" className="text-caption" onClick={() => openEdit(parent)}>
                {t('common.edit')}
              </Button>
            )}
          </div>

          {rows.length === 0 && (
            <p className="px-4 py-8 text-center text-label text-fg-tertiary">
              {t('settings.categories.empty')}
            </p>
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
                  <p className="truncate text-label font-medium text-fg-primary">{item.name}</p>
                  <p className="truncate text-caption text-fg-tertiary">
                    {t('records.found', { count: item.transactionsCount ?? 0 })}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-caption text-accent"
                  onClick={() => openEdit(item)}
                >
                  {t('common.edit')}
                </Button>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Dialog open={Boolean(draft)} onOpenChange={(next) => !next && setDraft(null)}>
        <DialogContent
          title={creating ? t('settings.categories.addSub') : t('common.edit')}
          description={parent?.name}
          footer={
            <div className="flex flex-wrap items-center justify-between gap-2">
              {!creating && draft ? (
                <Button
                  variant="ghost"
                  className="gap-1.5 text-[var(--negative)]"
                  disabled={pending}
                  onClick={() => void destroy(draft)}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                  {t('common.delete')}
                </Button>
              ) : (
                <span />
              )}
              <div className="flex gap-2">
                <Button variant="subtle" onClick={() => setDraft(null)}>
                  {t('common.cancel')}
                </Button>
                <Button onClick={() => void save()} disabled={!draft?.name.trim() || pending}>
                  {pending ? t('state.saving') : t('common.save')}
                </Button>
              </div>
            </div>
          }
        >
          {draft && (
            <div className="space-y-4">
              <Field label={t('settings.categories.name')}>
                <Input
                  value={draft.name}
                  onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                  aria-label={t('settings.categories.name')}
                  autoFocus
                />
              </Field>

              {creating && (
                <Field label={t('recordForm.type')}>
                  <SegmentedControl
                    aria-label={t('recordForm.type')}
                    value={draft.type}
                    onValueChange={(value) => setDraft({ ...draft, type: value as Category['type'] })}
                    items={[
                      { value: 'expense', label: t('recordForm.expense') },
                      { value: 'income', label: t('recordForm.income') },
                    ]}
                  />
                </Field>
              )}

              <div>
                <p className="mb-2 text-label font-medium text-fg-primary">
                  {t('settings.categories.color')}
                </p>
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
                        draft.color === color
                          ? 'scale-110 border-fg-primary'
                          : 'border-transparent hover:scale-105',
                      )}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>

              <div>
                <p className="mb-2 text-label font-medium text-fg-primary">
                  {t('settings.categories.icon')}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {ICONS.map((icon) => (
                    <button
                      key={icon}
                      type="button"
                      onClick={() => setDraft({ ...draft, icon })}
                      aria-label={icon}
                      aria-pressed={draft.icon === icon}
                      className={cn(
                        'grid size-8 place-items-center rounded-sm border transition-colors',
                        draft.icon === icon
                          ? 'border-accent bg-accent-soft text-accent-on-soft'
                          : 'border-stroke-subtle text-fg-secondary hover:border-stroke-strong',
                      )}
                    >
                      <CategoryIcon name={icon} className="size-4" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
