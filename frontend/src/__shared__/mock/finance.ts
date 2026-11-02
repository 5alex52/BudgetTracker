/**
 * Демо-данные, повторяющие набор из референсов (счета, записи, аналитика).
 * Валюта справочная — BYN. Пока фронтенд не подключён к API, это единственный
 * источник данных; бизнес-логика бэкенда не затрагивается.
 */

/**
 * Демонстрационные данные для витрины компонентов (`/design`).
 *
 * Рабочие экраны берут данные из API, а витрине нужны стабильные примеры,
 * поэтому здесь остаётся фиксированный набор. Типы общие — из `types/models`,
 * чтобы компоненты не знали, откуда пришли объекты.
 */
import type {
  Account,
  AnalyticsRow,
  Currency,
  CurrencyRate,
  RecordItem,
  Subcategory,
} from '@/__shared__/types/models'

export const CURRENCY_LABEL: Record<Currency, string> = {
  BYN: 'BYN',
  RUB: '₽',
  USD: '$',
  EUR: '€',
}

export const accounts: Account[] = [
  { id: 'alfa', name: 'Alfa', kind: 'checking', balance: 54.8, currency: 'BYN', tint: '#d94b4b' },
  { id: 'alfa-safe', name: 'Alfa Сейф', kind: 'savings', balance: 11759.91, currency: 'BYN', tint: '#e06fa0' },
  { id: 'cash', name: 'Наличные', kind: 'cash', balance: 370, currency: 'BYN', tint: '#2ba7d6' },
  { id: 'alfa-rub', name: 'Alfa RUB', kind: 'checking', balance: 0, currency: 'RUB', tint: '#e08a3c', locked: true },
  { id: 'tinkoff', name: 'Tinkoff', kind: 'cash', balance: 109401.99, currency: 'RUB', tint: '#e0873c', locked: true },
  {
    id: 'alfa-usd',
    name: 'Alfa USD',
    kind: 'checking',
    balance: 240,
    currency: 'USD',
    tint: '#d94b4b',
    excluded: true,
    locked: true,
  },
  {
    id: 'cash-usd',
    name: 'Cash USD',
    kind: 'cash',
    balance: 5345,
    currency: 'USD',
    tint: '#3aa76d',
    excluded: true,
    locked: true,
  },
  {
    id: 'cash-eur',
    name: 'Cash EUR',
    kind: 'cash',
    balance: 0,
    currency: 'EUR',
    tint: '#8b6fd6',
    excluded: true,
    locked: true,
  },
  {
    id: 'tinkoff-usd',
    name: 'Tinkoff USD',
    kind: 'cash',
    balance: 0,
    currency: 'USD',
    tint: '#e0873c',
    archived: true,
    locked: true,
  },
  {
    id: 'savings',
    name: 'Накопительный',
    kind: 'savings',
    balance: 0,
    currency: 'RUB',
    tint: '#e06fa0',
    archived: true,
    locked: true,
  },
  {
    id: 'turnover',
    name: 'Оборотный',
    kind: 'savings',
    balance: 0,
    currency: 'RUB',
    tint: '#2ba7d6',
    archived: true,
  },
]

/** Категории витрины: короткие примеры для иконок и цветов, без id из БД. */
export interface CategorySample {
  id: string
  name: string
  icon: string
  color: string
}

export const categories: CategorySample[] = [
  { id: 'food', name: 'Еда и напитки', icon: 'utensils', color: '#e0913c' },
  { id: 'life', name: 'Жизнь и развлечения', icon: 'theater', color: '#8b6fd6' },
  { id: 'shopping', name: 'Покупки', icon: 'shopping-bag', color: '#3aa76d' },
  { id: 'transport', name: 'Транспорт', icon: 'bus', color: '#2ba7d6' },
  { id: 'housing', name: 'Жилье', icon: 'house', color: '#d94b4b' },
  { id: 'books', name: 'Книги, аудио, подписки', icon: 'book', color: '#c26bd6' },
  { id: 'restaurant', name: 'Ресторан, фаст-фуд', icon: 'chef-hat', color: '#e06fa0' },
  { id: 'gifts', name: 'Подарки', icon: 'gift', color: '#e0a03c' },
  { id: 'finance', name: 'Финансовые расходы', icon: 'landmark', color: '#5b8fd6' },
  { id: 'invest', name: 'Инвестиции', icon: 'chart-line', color: '#2b9a8f' },
  { id: 'other', name: 'Прочее', icon: 'box', color: '#7d8a86' },
  { id: 'income', name: 'Доход', icon: 'arrow-down-left', color: '#2b9a6d' },
]

const rawRecords: Array<Omit<RecordItem, 'categoryId' | 'accountId' | 'iso' | 'tags' | 'isExcluded'>> = [
  {
    id: 'r1',
    type: 'income',
    category: 'Доход',
    categoryIcon: 'arrow-down-left',
    categoryColor: '#2b9a6d',
    account: 'Наличные',
    accountTint: '#2ba7d6',
    amount: 84,
    currency: 'BYN',
    date: '2025-10-11',
    time: '16:27',
  },
  {
    id: 'r2',
    type: 'income',
    category: 'Корректировка',
    categoryIcon: 'scale',
    categoryColor: '#5b8fd6',
    account: 'Alfa',
    accountTint: '#d94b4b',
    amount: 0.63,
    currency: 'BYN',
    date: '2025-10-11',
    time: '16:17',
  },
  {
    id: 'r3',
    type: 'expense',
    category: 'Книги, аудио, подписки',
    categoryIcon: 'book',
    categoryColor: '#c26bd6',
    account: 'Alfa',
    accountTint: '#d94b4b',
    amount: -15,
    currency: 'BYN',
    date: '2025-10-11',
    time: '16:16',
  },
  {
    id: 'r4',
    type: 'expense',
    category: 'Продукты',
    categoryIcon: 'shopping-cart',
    categoryColor: '#3aa76d',
    account: 'Tinkoff',
    accountTint: '#e0873c',
    amount: -1202.5,
    currency: 'RUB',
    date: '2025-10-10',
    time: '16:19',
  },
  {
    id: 'r5',
    type: 'expense',
    category: 'Ресторан, фаст-фуд',
    categoryIcon: 'chef-hat',
    categoryColor: '#e06fa0',
    account: 'Tinkoff',
    accountTint: '#e0873c',
    amount: -2400.42,
    currency: 'RUB',
    date: '2025-10-10',
    time: '16:19',
  },
  {
    id: 'r6',
    type: 'income',
    category: 'Подарки',
    categoryIcon: 'gift',
    categoryColor: '#e0a03c',
    account: 'Tinkoff',
    accountTint: '#e0873c',
    amount: 110000,
    currency: 'RUB',
    date: '2025-10-10',
    time: '16:18',
  },
  {
    id: 'r7',
    type: 'expense',
    category: 'Продукты',
    categoryIcon: 'shopping-cart',
    categoryColor: '#3aa76d',
    account: 'Alfa',
    accountTint: '#d94b4b',
    amount: -23.98,
    currency: 'BYN',
    date: '2025-10-10',
    time: '16:16',
  },
  {
    id: 'r8',
    type: 'expense',
    category: 'Покупки',
    categoryIcon: 'shopping-bag',
    categoryColor: '#3aa76d',
    account: 'Alfa',
    accountTint: '#d94b4b',
    amount: -15.42,
    currency: 'BYN',
    date: '2025-10-10',
    time: '16:15',
  },
  {
    id: 'r9',
    type: 'expense',
    category: 'Катя',
    categoryIcon: 'user',
    categoryColor: '#7d8a86',
    account: 'Наличные',
    accountTint: '#2ba7d6',
    amount: -100,
    currency: 'BYN',
    date: '2025-10-09',
    time: '16:15',
    payer: 'Катя',
  },
  {
    id: 'r10',
    type: 'expense',
    category: 'Продукты',
    categoryIcon: 'shopping-cart',
    categoryColor: '#3aa76d',
    account: 'Alfa',
    accountTint: '#d94b4b',
    amount: -26.17,
    currency: 'BYN',
    date: '2025-10-09',
    time: '16:15',
  },
]

/** Строки отчёта «Аналитика»: 6 месяцев, суммы как в референсе. */
/**
 * Записи витрины: в UI-модели нужны id категории и счёта, полная ISO-дата и метки.
 * Сами примеры остаются короткими — недостающие поля добавляются здесь.
 */
export const records: RecordItem[] = rawRecords.map((item) => ({
  ...item,
  categoryId: 0,
  accountId: '0',
  iso: `${item.date}T${item.time}:00`,
  tags: [],
  isExcluded: false,
}))

export const analyticsMonths = [
  { key: '2025-10', label: 'октябрь 2025', labelEn: 'October 2025' },
  { key: '2025-09', label: 'сентябрь 2025', labelEn: 'September 2025' },
  { key: '2025-08', label: 'август 2025', labelEn: 'August 2025' },
  { key: '2025-07', label: 'июль 2025', labelEn: 'July 2025' },
  { key: '2025-06', label: 'июнь 2025', labelEn: 'June 2025' },
  { key: '2025-05', label: 'май 2025', labelEn: 'May 2025' },
] as const

export const analyticsRows: AnalyticsRow[] = [
  {
    id: 'total-income',
    name: 'Общий доход',
    values: [12267.07, 8297.03, 8327.88, 8844.89, 9273.42, 7476.1],
    trends: [48, 0, -6, -5, 24, 8],
  },
  {
    id: 'income',
    name: 'Доход',
    values: [12267.07, 8297.03, 8327.88, 8844.89, 9273.42, 7476.1],
    trends: [48, 0, -6, -5, 24, 8],
  },
  {
    id: 'total-expense',
    name: 'Общие расходы',
    values: [-2329.15, -7468.59, -7099.09, -10437.72, -9290.7, -4894.89],
    trends: [69, -5, 32, -12, -90, -2],
  },
  {
    id: 'food',
    name: 'Еда и напитки',
    icon: 'utensils',
    color: '#e0913c',
    values: [-609.4, -1344.45, -1128.86, -1137.05, -1233.0, -968.31],
    trends: [55, -19, 1, 8, -27, -52],
  },
  {
    id: 'shopping',
    name: 'Покупки',
    icon: 'shopping-bag',
    color: '#3aa76d',
    values: [-142.98, -108.34, -19.03, -395.46, -1052.51, -846.67],
    trends: [-32, -469, 95, 62, -24, -709],
  },
  {
    id: 'housing',
    name: 'Жилье',
    icon: 'house',
    color: '#d94b4b',
    values: [0, -1462.16, -1279.33, -1269.07, -1264.2, -1304.62],
    trends: [100, -14, -1, 0, 3, 2],
  },
  {
    id: 'transport',
    name: 'Транспорт',
    icon: 'bus',
    color: '#2ba7d6',
    values: [-119, -333.62, -287.4, -322.26, -372.9, -158.82],
    trends: [64, -16, 11, 14, -135, 14],
  },
  {
    id: 'life',
    name: 'Жизнь и развлечения',
    icon: 'theater',
    color: '#8b6fd6',
    values: [-1450.76, -3305.17, -3369.48, -6058.58, -4879.15, -1469.47],
    trends: [56, 2, 44, -24, -232, 41],
  },
  {
    id: 'books',
    name: 'Связь, компьютер',
    icon: 'smartphone',
    color: '#c26bd6',
    values: [0, -51.33, -51.03, -61.55, -51.93, -67.0],
    trends: [100, -1, 17, -19, 22, -44],
  },
  {
    id: 'finance',
    name: 'Финансовые расходы',
    icon: 'landmark',
    color: '#5b8fd6',
    values: [-7.01, -863.53, -880.34, -1073.75, -7.01, 0],
    trends: [99, 2, 18, -999, -100, 100],
  },
  {
    id: 'invest',
    name: 'Инвестиции',
    icon: 'chart-line',
    color: '#2b9a8f',
    values: [0, 0, -120, -430, -80, 0],
    trends: [0, 0, 100, 72, -437, -100],
  },
  {
    id: 'other',
    name: 'Прочее',
    icon: 'box',
    color: '#7d8a86',
    values: [0, 0, -83.62, 0, 0, 0],
    trends: [0, 0, 100, 0, 0, 0],
  },
]

/** Счёт-карта на дашборде (первые пять из активных) */
export const dashboardCards = accounts.filter((a) => !a.excluded && !a.archived).slice(0, 8)

/** Данные для графиков дашборда */
export const balanceSeries = [
  { label: '1 окт.', value: 12600 },
  { label: '4 окт.', value: 13100 },
  { label: '7 окт.', value: 12880 },
  { label: '10 окт.', value: 13550 },
  { label: '14 окт.', value: 14120 },
  { label: '18 окт.', value: 14500 },
  { label: '22 окт.', value: 15100 },
  { label: '26 окт.', value: 15650 },
  { label: '31 окт.', value: 16059.73 },
]

export const cashflowSeries = [
  { label: '1 окт.', income: 1200, expense: -400 },
  { label: '5 окт.', income: 2100, expense: -600 },
  { label: '9 окт.', income: 900, expense: -1100 },
  { label: '13 окт.', income: 2600, expense: -300 },
  { label: '17 окт.', income: 1400, expense: -800 },
  { label: '21 окт.', income: 3000, expense: -500 },
  { label: '25 окт.', income: 1800, expense: -700 },
  { label: '31 окт.', income: 2200, expense: -900 },
]

export const expenseStructure = [
  { name: 'Жизнь и развлечения', value: 1450.76, color: '#8b6fd6' },
  { name: 'Еда и напитки', value: 609.4, color: '#e0913c' },
  { name: 'Покупки', value: 142.98, color: '#3aa76d' },
  { name: 'Транспорт', value: 119, color: '#2ba7d6' },
  { name: 'Финансовые расходы', value: 7.01, color: '#5b8fd6' },
]

export const periodComparison = [
  { label: '1 окт.', cashflow: 11000, expense: 7000, income: 3500 },
  { label: '8 окт.', cashflow: 8200, expense: 5200, income: 2600 },
  { label: '15 окт.', cashflow: 9600, expense: 6100, income: 3100 },
  { label: '22 окт.', cashflow: 7400, expense: 4700, income: 2300 },
  { label: '31 окт.', cashflow: 10200, expense: 6800, income: 3200 },
]

/* ------------------- валюты, категории, метки, правила -------------------- */

/** Порядок и значения — как в референсе «Валюты». */
const CURRENCY_NAMES: Array<[string, string, string, number, boolean]> = [
  ['USD', 'United States Dollar', '$', 2.97, false],
  ['RUB', 'Russian Ruble', '₽', 0.03542, false],
  ['EUR', 'Euro', '€', 3.477, false],
  ['BYN', 'New Belarusian Ruble', 'Br', 1, true],
]

export const currencies: CurrencyRate[] = CURRENCY_NAMES.map(([code, name, symbol, rate, base]) => ({
  code,
  name,
  symbol,
  rate,
  base,
}))

/** Подкатегории по родительским категориям — как в референсе «Категории». */
const rawSubcategories: Array<{
  id: string
  name: string
  parent: string
  icon: string
  color: string
  character: 'essential' | 'optional' | 'income'
  hidden?: boolean
}> = [
  { id: 'sc-bar', name: 'Бар, кафе', parent: 'food', icon: 'utensils', color: '#e0913c', character: 'optional' },
  { id: 'sc-fastfood', name: 'Ресторан, фаст-фуд', parent: 'food', icon: 'chef-hat', color: '#e06fa0', character: 'optional' },
  { id: 'sc-grocery', name: 'Продукты', parent: 'food', icon: 'shopping-cart', color: '#3aa76d', character: 'essential' },
  { id: 'sc-delivery', name: 'Доставка еды', parent: 'food', icon: 'box', color: '#c26bd6', character: 'optional', hidden: true },
  { id: 'sc-cinema', name: 'Кино', parent: 'life', icon: 'theater', color: '#8b6fd6', character: 'optional' },
  { id: 'sc-taxi', name: 'Такси', parent: 'transport', icon: 'bus', color: '#2ba7d6', character: 'optional' },
  { id: 'sc-fuel', name: 'Топливо', parent: 'transport', icon: 'bus', color: '#5b8fd6', character: 'essential' },
  { id: 'sc-rent', name: 'Аренда', parent: 'housing', icon: 'house', color: '#d94b4b', character: 'essential' },
  { id: 'sc-books', name: 'Книги и аудио', parent: 'books', icon: 'book', color: '#c26bd6', character: 'optional' },
  { id: 'sc-salary', name: 'Зарплата', parent: 'income', icon: 'arrow-down-left', color: '#2b9a6d', character: 'income' },
]

/** Подкатегории витрины: строковые ключи превращаются в числовые id модели. */
export const subcategories: Subcategory[] = rawSubcategories.map((item, index) => ({
  id: index + 1,
  name: item.name,
  parent: ((rawSubcategories.findIndex((parent) => parent.id === item.parent) % 1000) + 1) || null,
  icon: item.icon,
  color: item.color,
  type: (item.character === 'income' ? 'income' : 'expense') as Subcategory['type'],
}))

export interface TagItem {
  id: string
  name: string
  color: string
  usage: number
}

export const tags: TagItem[] = [
  { id: 't-work', name: 'работа', color: '#5b8fd6', usage: 24 },
  { id: 't-family', name: 'семья', color: '#e06fa0', usage: 17 },
  { id: 't-trip', name: 'поездка', color: '#2ba7d6', usage: 8 },
  { id: 't-health', name: 'здоровье', color: '#3aa76d', usage: 5 },
]

export interface RuleItem {
  id: string
  field: string
  match: string
  action: string
  value: string
  enabled: boolean
}

export const rules: RuleItem[] = [
  { id: 'rule-1', field: 'Назначение платежа', match: 'СОДЕРЖИТ «PYATEROCHKA»', action: 'Категория', value: 'Продукты', enabled: true },
  { id: 'rule-2', field: 'Сумма', match: 'БОЛЬШЕ 1 000', action: 'Метка', value: 'крупная покупка', enabled: true },
  { id: 'rule-3', field: 'Тип платежа', match: 'РАВНО «Перевод»', action: 'Скрыть из статистики', value: '—', enabled: false },
]
