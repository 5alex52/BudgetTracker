import { create } from 'zustand'
import { ApiError } from '@/api'
import * as accountsApi from '@/api/accounts'
import * as categoriesApi from '@/api/categories'
import * as currenciesApi from '@/api/currencies'
import * as rulesApi from '@/api/rules'
import * as tagsApi from '@/api/tags'
import * as templatesApi from '@/api/templates'
import { saveAccountTint, toAccount, toCategory, toCategoryTree, toCurrencyRate, toSubcategories } from '@/api/mappers'
import type {
  AccountCreate,
  AccountUpdate,
  CategoryCreate,
  CategoryUpdate,
  RuleCreate,
  RuleDto,
  RuleUpdate,
  TagCreate,
  TagDto,
  TagUpdate,
  TemplateCreate,
  TemplateDto,
  TemplateUpdate,
} from '@/api/types'
import type { Account, Category, CurrencyRate, Subcategory } from '@/__shared__/types/models'

/**
 * Справочные данные приложения: счета, категории, метки, шаблоны, правила, курсы.
 *
 * Их читают почти все экраны, поэтому они живут в одном сторе и подгружаются
 * один раз (`loadAll`), а не в каждом компоненте. Мутации сразу правят локальный
 * список, чтобы интерфейс не мигал повторной загрузкой.
 */
interface FinanceState {
  accounts: Account[]
  categories: Category[]
  tree: Category[]
  tags: TagDto[]
  templates: TemplateDto[]
  rules: RuleDto[]
  rates: CurrencyRate[]
  baseCurrency: string
  loading: boolean
  error: string | null
  /** Загружены ли справочники: защита от повторных запросов */
  ready: boolean

  loadAll: (options?: { force?: boolean }) => Promise<void>
  /** Сбросить справочники: выход из аккаунта и смена пользователя */
  clearData: () => void
  reloadAccounts: () => Promise<void>
  reloadCategories: () => Promise<void>
  reloadTags: () => Promise<void>
  reloadTemplates: () => Promise<void>
  reloadRules: () => Promise<void>
  reloadRates: () => Promise<void>

  accountById: (id: string | number) => Account | undefined
  categoryById: (id: number) => Category | undefined
  /** Подкатегории для формы записи */
  subcategories: () => Subcategory[]
  /** Коды валют, которые встречаются в счетах и справочнике */
  currencyCodes: () => string[]

  createAccount: (payload: AccountCreate, tint?: string) => Promise<Account>
  updateAccount: (id: string | number, payload: AccountUpdate, tint?: string) => Promise<Account>
  deleteAccount: (id: string | number) => Promise<void>

  createCategory: (payload: CategoryCreate) => Promise<Category>
  updateCategory: (id: number, payload: CategoryUpdate) => Promise<Category>
  deleteCategory: (id: number) => Promise<void>

  createTag: (payload: TagCreate) => Promise<TagDto>
  updateTag: (id: number, payload: TagUpdate) => Promise<TagDto>
  deleteTag: (id: number) => Promise<void>

  createTemplate: (payload: TemplateCreate) => Promise<TemplateDto>
  updateTemplate: (id: number, payload: TemplateUpdate) => Promise<TemplateDto>
  deleteTemplate: (id: number) => Promise<void>

  createRule: (payload: RuleCreate) => Promise<RuleDto>
  updateRule: (id: number, payload: RuleUpdate) => Promise<RuleDto>
  deleteRule: (id: number) => Promise<void>

  setUserRate: (code: string, rate: number) => Promise<void>
  resetUserRate: (code: string) => Promise<void>
}

export const useFinanceStore = create<FinanceState>((set, get) => ({
  accounts: [],
  categories: [],
  tree: [],
  tags: [],
  templates: [],
  rules: [],
  rates: [],
  baseCurrency: 'BYN',
  loading: false,
  error: null,
  ready: false,

  clearData: () => {
    // Данные принадлежат пользователю: при выходе их нельзя показывать следующему
    set({
      accounts: [],
      categories: [],
      tree: [],
      tags: [],
      templates: [],
      rules: [],
      rates: [],
      baseCurrency: 'BYN',
      loading: false,
      error: null,
      ready: false,
    })
  },

  loadAll: async (options) => {
    if (get().loading) return
    if (get().ready && !options?.force) return
    set({ loading: true, error: null })
    try {
      const [accountList, tree, tagList, templateList, ruleList, rates] = await Promise.all([
        accountsApi.listAccounts({ includeArchived: true, includeExcluded: true }),
        categoriesApi.getCategoryTree(),
        tagsApi.listTags(),
        templatesApi.listTemplates(),
        rulesApi.listRules(),
        currenciesApi.getRates(),
      ])
      const flatCategories = flattenCategories(tree)
      set({
        accounts: accountList.map(toAccount),
        tree: toCategoryTree(tree),
        categories: flatCategories,
        tags: tagList,
        templates: templateList,
        rules: ruleList,
        rates: rates.map(toCurrencyRate),
        baseCurrency: rates.find((rate) => rate.is_base)?.code ?? get().baseCurrency,
        ready: true,
        loading: false,
      })
    } catch (caught) {
      // Ошибку показываем текстом, но экран не блокируем: часть данных могла
      // загрузиться, а вечная заглушка хуже пустого списка с сообщением.
      set({
        loading: false,
        ready: true,
        error: caught instanceof ApiError ? caught.detail : String(caught),
      })
    }
  },

  reloadAccounts: async () => {
    const list = await accountsApi.listAccounts({ includeArchived: true, includeExcluded: true })
    set({ accounts: list.map(toAccount) })
  },

  reloadCategories: async () => {
    const tree = await categoriesApi.getCategoryTree()
    set({ tree: toCategoryTree(tree), categories: flattenCategories(tree) })
  },

  reloadTags: async () => {
    set({ tags: await tagsApi.listTags() })
  },

  reloadTemplates: async () => {
    set({ templates: await templatesApi.listTemplates() })
  },

  reloadRules: async () => {
    set({ rules: await rulesApi.listRules() })
  },

  reloadRates: async () => {
    const rates = await currenciesApi.getRates()
    set({
      rates: rates.map(toCurrencyRate),
      baseCurrency: rates.find((rate) => rate.is_base)?.code ?? get().baseCurrency,
    })
  },

  accountById: (id) => get().accounts.find((account) => account.id === String(id)),
  categoryById: (id) => get().categories.find((category) => category.id === id),
  subcategories: () => toSubcategories(get().categories),
  currencyCodes: () => {
    const codes = new Set<string>(get().rates.map((rate) => rate.code))
    get().accounts.forEach((account) => codes.add(account.currency))
    return [...codes]
  },

  createAccount: async (payload, tint) => {
    const dto = await accountsApi.createAccount(payload)
    const account = toAccount(dto)
    if (tint) {
      saveAccountTint(account.id, tint)
      account.tint = tint
    }
    // Перезагружаем список целиком: создание меняет лимит и блокировки
    // остальных счетов на бесплатном тарифе.
    await get().reloadAccounts()
    return get().accountById(account.id) ?? account
  },

  updateAccount: async (id, payload, tint) => {
    const dto = await accountsApi.updateAccount(id, payload)
    const account = toAccount(dto)
    if (tint) {
      saveAccountTint(account.id, tint)
      account.tint = tint
    }
    // Архивация/смена валюты пересчитывает блокировки всех счетов.
    await get().reloadAccounts()
    return get().accountById(account.id) ?? account
  },

  deleteAccount: async (id) => {
    await accountsApi.deleteAccount(id)
    // Удаление освобождает слот бесплатного тарифа для других счетов.
    await get().reloadAccounts()
  },

  createCategory: async (payload) => {
    const dto = await categoriesApi.createCategory(payload)
    await get().reloadCategories()
    return toCategory(dto)
  },

  updateCategory: async (id, payload) => {
    const dto = await categoriesApi.updateCategory(id, payload)
    await get().reloadCategories()
    return toCategory(dto)
  },

  deleteCategory: async (id) => {
    await categoriesApi.deleteCategory(id)
    await get().reloadCategories()
  },

  createTag: async (payload) => {
    const tag = await tagsApi.createTag(payload)
    set((state) => ({ tags: [...state.tags, tag] }))
    return tag
  },

  updateTag: async (id, payload) => {
    const tag = await tagsApi.updateTag(id, payload)
    set((state) => ({ tags: state.tags.map((item) => (item.id === id ? tag : item)) }))
    return tag
  },

  deleteTag: async (id) => {
    await tagsApi.deleteTag(id)
    set((state) => ({ tags: state.tags.filter((item) => item.id !== id) }))
  },

  createTemplate: async (payload) => {
    const template = await templatesApi.createTemplate(payload)
    set((state) => ({ templates: [...state.templates, template] }))
    return template
  },

  updateTemplate: async (id, payload) => {
    const template = await templatesApi.updateTemplate(id, payload)
    set((state) => ({
      templates: state.templates.map((item) => (item.id === id ? template : item)),
    }))
    return template
  },

  deleteTemplate: async (id) => {
    await templatesApi.deleteTemplate(id)
    set((state) => ({ templates: state.templates.filter((item) => item.id !== id) }))
  },

  createRule: async (payload) => {
    const rule = await rulesApi.createRule(payload)
    set((state) => ({ rules: [...state.rules, rule] }))
    return rule
  },

  updateRule: async (id, payload) => {
    const rule = await rulesApi.updateRule(id, payload)
    set((state) => ({
      rules: state.rules.map((item) => (item.id === id ? rule : item)),
    }))
    return rule
  },

  deleteRule: async (id) => {
    await rulesApi.deleteRule(id)
    set((state) => ({ rules: state.rules.filter((item) => item.id !== id) }))
  },

  setUserRate: async (code, rate) => {
    await currenciesApi.setUserRate(code, rate)
    await get().reloadRates()
  },

  resetUserRate: async (code) => {
    await currenciesApi.resetUserRate(code)
    await get().reloadRates()
  },
}))

/** Дерево → плоский список: подкатегории и полный набор нужны форме записи. */
function flattenCategories(nodes: Awaited<ReturnType<typeof categoriesApi.getCategoryTree>>): Category[] {
  const result: Category[] = []
  const walk = (items: typeof nodes) => {
    items.forEach((node) => {
      result.push({
        id: node.id,
        name: node.name,
        icon: node.icon || 'circle',
        color: node.color || '#7d8a86',
        type: node.type,
        parentId: node.parent_id,
        transactionsCount: node.transactions_count,
      })
      if (node.children?.length) walk(node.children)
    })
  }
  walk(nodes)
  return result
}
