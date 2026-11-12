import type { RecordItem } from '@/__shared__/types/models'

/**
 * Record export. Formats are produced on the client, no backend:
 * CSV and TSV — flat tables, JSON — full objects, XLS — SpreadsheetML
 * (Excel opens it as a regular workbook), PDF — via browser printing
 * ("Save as PDF" in the print dialog).
 *
 * The PDF prints a separate document, not the app page itself: white sheet,
 * black text, thin lines — a formal look that reads the same on paper
 * and on screen. UI colors never reach the printout.
 */

export type ExportFormat = 'csv' | 'tsv' | 'json' | 'xls' | 'pdf'

const COLUMNS = ['date', 'time', 'type', 'category', 'account', 'amount', 'currency', 'note'] as const

function rows(items: RecordItem[], locale: string) {
  const header = locale === 'ru'
    ? ['Дата', 'Время', 'Тип', 'Категория', 'Счёт', 'Сумма', 'Валюта', 'Заметка']
    : ['Date', 'Time', 'Type', 'Category', 'Account', 'Amount', 'Currency', 'Note']

  const body = items.map((item) => [
    item.date,
    item.time,
    item.type,
    item.category,
    item.account,
    String(item.amount).replace('.', ','),
    item.currency,
    item.note ?? '',
  ])

  return { header, body }
}

function download(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

const escapeDelimited = (value: string, delimiter: string) =>
  value.includes(delimiter) || value.includes('"') || value.includes('\n')
    ? `"${value.replace(/"/g, '""')}"`
    : value

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

/** Totals by currency: in the PDF different currencies can't be summed into one number. */
function totalsByCurrency(items: RecordItem[]) {
  const totals = new Map<string, number>()
  for (const item of items) {
    totals.set(item.currency, (totals.get(item.currency) ?? 0) + item.amount)
  }
  return [...totals.entries()].sort(([left], [right]) => left.localeCompare(right))
}

const formatMoney = (value: number, locale: string) =>
  new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)

/**
 * Print a formal document: white background, black text, thin border.
 * Opens in a separate window, so app styles don't affect the result.
 */
function printOfficialDocument(items: RecordItem[], locale: string) {
  const ru = locale === 'ru'
  const { header, body } = rows(items, locale)
  const title = ru ? 'Выписка по записям' : 'Transaction statement'
  const printedAt = new Intl.DateTimeFormat(ru ? 'ru-RU' : 'en-US', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(new Date())

  const totals = totalsByCurrency(items)
  const totalRows = totals
    .map(
      ([currency, amount]) =>
        `<tr><td class="label">${ru ? 'Итого' : 'Total'} · ${escapeHtml(currency)}</td>` +
        `<td class="amount${amount < 0 ? ' negative' : ''}">${escapeHtml(formatMoney(amount, locale))} ${escapeHtml(currency)}</td></tr>`,
    )
    .join('')

  const tableRows = body
    .map(
      (row) =>
        '<tr>' +
        row
          .map((cell, index) => {
            const align = index === 5 ? ' class="amount"' : ''
            return `<td${align}>${escapeHtml(cell)}</td>`
          })
          .join('') +
        '</tr>',
    )
    .join('')

  const html = `<!doctype html>
<html lang="${ru ? 'ru' : 'en'}">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
<style>
  @page { size: A4 portrait; margin: 18mm 14mm; }
  * { box-sizing: border-box; }
  html, body { background: #ffffff; color: #000000; margin: 0; padding: 0; }
  body {
    font-family: "Times New Roman", Georgia, "DejaVu Serif", serif;
    font-size: 10.5pt;
    line-height: 1.35;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  h1 {
    font-size: 15pt;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0 0 2mm;
    border-bottom: 0.6pt solid #000000;
    padding-bottom: 2mm;
  }
  .meta { font-size: 9pt; margin-bottom: 6mm; color: #000000; }
  table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
  thead th {
    text-align: left;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 8.5pt;
    letter-spacing: 0.03em;
    border-top: 0.9pt solid #000000;
    border-bottom: 0.9pt solid #000000;
    padding: 1.8mm 1.5mm;
  }
  tbody td { border-bottom: 0.35pt solid #808080; padding: 1.5mm; vertical-align: top; }
  tbody tr:last-child td { border-bottom: 0.9pt solid #000000; }
  td.amount { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .negative { font-weight: 700; }
  .totals { margin-top: 4mm; width: auto; min-width: 60mm; margin-left: auto; }
  .totals td { border: none; padding: 0.8mm 1.5mm; font-size: 10pt; }
  .totals .label { text-align: right; font-weight: 700; text-transform: uppercase; font-size: 8.5pt; letter-spacing: 0.03em; }
  footer { margin-top: 8mm; padding-top: 2mm; border-top: 0.35pt solid #808080; font-size: 8pt; }
  /* Nothing extra: no backgrounds, no shadows — text and lines only */
  @media print { a { color: #000000; text-decoration: none; } }
</style>
</head>
<body>
  <h1>${escapeHtml(title)}</h1>
  <p class="meta">${ru ? 'Сформировано' : 'Generated'}: ${escapeHtml(printedAt)} · ${ru ? 'записей' : 'records'}: ${items.length}</p>
  <table>
    <thead><tr>${header.map((cell) => `<th>${escapeHtml(cell)}</th>`).join('')}</tr></thead>
    <tbody>${tableRows}</tbody>
  </table>
  <table class="totals">${totalRows}</table>
  <footer>BudgetTracker · ${escapeHtml(printedAt)}</footer>
  <script>window.onload = function () { window.print(); };</script>
</body>
</html>`

  const printWindow = window.open('', '_blank', 'width=900,height=1200')
  if (!printWindow) {
    // Popup blocked — print the current page, as before
    window.print()
    return
  }
  printWindow.document.open()
  printWindow.document.write(html)
  printWindow.document.close()
}

export function exportRecords(items: RecordItem[], format: ExportFormat, locale: string) {
  const stamp = new Date().toISOString().slice(0, 10)

  if (format === 'pdf') {
    printOfficialDocument(items, locale)
    return { filename: 'print' }
  }

  if (format === 'json') {
    const payload = items.map((item) =>
      Object.fromEntries(COLUMNS.map((key) => [key, item[key as keyof RecordItem] ?? null])),
    )
    download(JSON.stringify(payload, null, 2), `records-${stamp}.json`, 'application/json')
    return { filename: `records-${stamp}.json` }
  }

  const { header, body } = rows(items, locale)

  if (format === 'xls') {
    // SpreadsheetML: Excel and LibreOffice open it without format warnings.
    const cell = (value: string) =>
      `<Cell><Data ss:Type="${/^-?\d+([.,]\d+)?$/.test(value) ? 'Number' : 'String'}">${value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')}</Data></Cell>`
    const xml =
      `<?xml version="1.0"?>\n<?mso-application progid="Excel.Sheet"?>\n` +
      `<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">` +
      `<Worksheet ss:Name="Records"><Table>` +
      `<Row>${header.map(cell).join('')}</Row>` +
      body.map((row) => `<Row>${row.map(cell).join('')}</Row>`).join('') +
      `</Table></Worksheet></Workbook>`
    download(xml, `records-${stamp}.xls`, 'application/vnd.ms-excel')
    return { filename: `records-${stamp}.xls` }
  }

  const delimiter = format === 'tsv' ? '\t' : ';'
  // BOM so Excel reads Cyrillic from the CSV correctly.
  const content = '\ufeff' + [header, ...body].map((row) => row.map((v) => escapeDelimited(v, delimiter)).join(delimiter)).join('\r\n')
  download(content, `records-${stamp}.${format}`, format === 'tsv' ? 'text/tab-separated-values' : 'text/csv')
  return { filename: `records-${stamp}.${format}` }
}
