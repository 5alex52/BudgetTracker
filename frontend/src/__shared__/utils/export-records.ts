import type { RecordItem } from '@/__shared__/types/models'

/**
 * Экспорт записей. Форматы считаются на клиенте, без бэкенда:
 * CSV и TSV — плоские таблицы, JSON — полные объекты, XLS — SpreadsheetML
 * (Excel открывает его как обычную книгу), PDF — через печать браузера
 * («Сохранить как PDF» в диалоге печати).
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

export function exportRecords(items: RecordItem[], format: ExportFormat, locale: string) {
  const stamp = new Date().toISOString().slice(0, 10)

  if (format === 'pdf') {
    window.print()
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
    // SpreadsheetML: Excel и LibreOffice открывают без предупреждений о формате.
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
  // BOM — чтобы Excel корректно прочитал кириллицу из CSV.
  const content = '\ufeff' + [header, ...body].map((row) => row.map((v) => escapeDelimited(v, delimiter)).join(delimiter)).join('\r\n')
  download(content, `records-${stamp}.${format}`, format === 'tsv' ? 'text/tab-separated-values' : 'text/csv')
  return { filename: `records-${stamp}.${format}` }
}
