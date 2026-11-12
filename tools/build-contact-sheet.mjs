#!/usr/bin/env node
/**
 * Builds a static mockup showcase: docs/design/mockups/index.html.
 * Opens with a double click, no server — for design review.
 */
import { readdir, writeFile } from 'node:fs/promises'

const dir = 'docs/design/mockups'
const files = (await readdir(dir)).filter((name) => name.endsWith('.png') && !name.startsWith('_'))
const webkitFiles = (await readdir(`${dir}/webkit`)).filter((name) => name.endsWith('.png'))
const enFiles = files.filter((name) => name.startsWith('en-'))

const SCREENS = [
  ['login', 'Окно входа', 'Промо + форма. Разделение на две колонки, на 390 px — в столбик.'],
  ['dashboard', 'Обзор', 'Плитки счетов, навигатор месяца и шесть виджетов.'],
  ['accounts', 'Счета', 'Группы по типу счёта, итог по группе, исключённые и архивные.'],
  ['records', 'Записи', 'Фильтры слева (на мобиле — в Sheet), список по дням, итог за период.'],
  ['analytics', 'Аналитика', 'Четыре вкладки, таблица месяцы × категории со sticky-колонкой.'],
  ['settings', 'Настройки', 'Две группы навигации, профиль, предпочтения, удаление данных.'],
  ['design', 'Дизайн-система', 'Витрина компонентов и состояний материала.'],
]

const STATES = [
  ['record-modal-desktop', 'Модал «Добавить запись»', 'Две колонки: основное и «Другие детали».'],
  ['records-filters-mobile', 'Фильтры в Sheet (390)', 'Одиннадцать групп фильтров на мобиле.'],
  ['analytics-advanced-desktop', 'Аналитика: премиум-вкладка', 'Заглушка вкладки с апселлом.'],
]

const pick = (prefix) => {
  if (prefix.startsWith('webkit-')) {
    const base = prefix.replace('webkit-', '')
    return webkitFiles
      .filter((name) => name.startsWith(`${base}-`))
      .map((name) => `webkit/${name}`)
      .sort((a, b) => (a.includes('dark') ? -1 : 1) - (b.includes('dark') ? -1 : 1) || a.localeCompare(b))
  }
  return files
    .filter((name) => name.startsWith(`${prefix}-`))
    .sort((a, b) => (a.includes('dark') ? -1 : 1) - (b.includes('dark') ? -1 : 1) || a.localeCompare(b))
}

const section = (title, note, items) => `
  <section>
    <h2>${title}</h2>
    ${note ? `<p class="note">${note}</p>` : ''}
    <div class="grid">
      ${items
        .map(
          ([prefix]) => `
        <figure>
          <figcaption>${prefix}</figcaption>
          ${pick(prefix)
            .map(
              (file) => `
            <a class="shot" href="${file}" target="_blank" rel="noreferrer">
              <img src="${file}" alt="${file}" loading="lazy" />
              <span>${file.replace(`${prefix}-`, '').replace('.png', '')}</span>
            </a>`,
            )
            .join('')}
        </figure>`,
        )
        .join('')}
    </div>
  </section>`

const html = `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<title>BudgetTracker — макеты для утверждения</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 32px;
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0b0f0e; color: #f2f6f5;
  }
  h1 { font-size: 26px; margin: 0 0 4px; }
  h2 { font-size: 18px; margin: 40px 0 4px; }
  .note { margin: 0 0 16px; color: #a9b6b2; max-width: 80ch; }
  .grid { display: grid; gap: 20px; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); }
  figure { margin: 0; background: #151b1a; border: 1px solid #263230; border-radius: 14px; padding: 12px; }
  figcaption { font-weight: 600; margin-bottom: 8px; }
  .shot { display: block; text-decoration: none; color: #a9b6b2; font-size: 12px; margin-bottom: 10px; }
  .shot img {
    display: block; width: 100%; height: auto; max-height: 320px; object-fit: cover; object-position: top;
    border-radius: 8px; border: 1px solid #2b3634; background: #000;
  }
  .shot span { display: block; margin-top: 4px; }
  header p { color: #a9b6b2; max-width: 90ch; }
</style>
</head>
<body>
<header>
  <h1>BudgetTracker — макеты для утверждения</h1>
  <p>
    Каждый экран снят в двух темах и на двух ширинах: 1440 px (десктоп) и 390 px (мобильный веб).
    Клик по картинке открывает полный размер. Страница статическая, собрана из PNG — приложение для просмотра не нужно.
  </p>
</header>
${section('Экраны', 'Порядок как в продукте: от входа до настроек.', SCREENS)}
${section('Состояния', 'Слои и второстепенные состояния, которые не видны на первом экране.', STATES)}
${section(
  'Второй язык (EN)',
  'Один и тот же интерфейс на английском — проверка длинных подписей и отсутствия обрезки.',
  [['en-dashboard-desktop'], ['en-records-desktop'], ['en-settings-desktop'], ['en-login-desktop']],
)}
${section(
  'Пятая итерация: контраст текста',
  'Аудит по WCAG: перекрашены акцентные кнопки, третичный текст, суммы, плашки счетов и значки категорий в обеих темах.',
  [['v5-contrast-dashboard-dark'], ['v5-contrast-dashboard-light'], ['v5-contrast-accounts-dark'], ['v5-contrast-accounts-light'], ['v5-contrast-records-light'], ['v5-contrast-records-dialog-dark'], ['v6-calendar-dark'], ['v6-calendar-light'], ['v6-calendar-mobile-dark']],
)}
${section(
  'Четвёртая итерация: логотип, счета, живые кнопки',
  'Фирменный знак из макетов, форма счёта (создание и правка), подтверждение удаления, тарифы, шаблоны, правила, обращение к ДПО.',
  [['v4-dashboard-logo-desktop-dark'], ['v4-dashboard-logo-desktop-light'], ['v4-account-create-desktop-dark'], ['v4-account-create-mobile-dark'], ['v4-account-edit-desktop-dark'], ['v4-account-delete-desktop-dark'], ['v4-plan-dialog-desktop-dark'], ['v4-template-edit-desktop-dark'], ['v4-rule-add-desktop-dark'], ['v4-privacy-dpo-desktop-dark'], ['v4-dashboard-month-desktop-dark'], ['en-v4-account-create-desktop-dark']],
)}
${section(
  'Третья итерация: экспорт, правка записи, диапазон дат',
  'Меню форматов, режим редактирования записи, подкатегории, акценты по типу, календарь диапазона, платежи, окно валюты.',
  [['v3-records-export-desktop-dark'], ['v3-record-edit-desktop-dark'], ['v3-record-income-desktop-dark'], ['v3-period-range-desktop-dark'], ['v3-currency-edit-desktop-dark'], ['v3-settings-payments-desktop-dark'], ['v3-login-desktop-dark']],
)}
${section(
  'Вторая итерация: новый каркас и экраны',
  'Вертикальный рельс вместо полосы меню, подразделы настроек, детали счёта и перевод между счетами.',
  [['v2-dashboard-desktop'], ['v2-settings-currencies-desktop'], ['v2-settings-categories-desktop'], ['v2-account-detail-desktop'], ['v2-record-transfer-desktop']],
)}
${section(
  'WebKit (движок Safari)',
  'Тот же интерфейс, отрисованный WKWebView: проверка откатов без Chromium-специфичной рефракции.',
  [['webkit-dashboard-desktop'], ['webkit-records-desktop'], ['webkit-login-desktop'], ['webkit-settings-desktop']],
)}
</body>
</html>`

await writeFile(`${dir}/index.html`, html, 'utf8')
console.log(`showcase: ${dir}/index.html, images: ${files.length + webkitFiles.length} (EN: ${enFiles.length})`)
