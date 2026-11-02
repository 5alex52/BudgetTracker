import { Download, FileDown, FileJson, FileSpreadsheet, FileText, Server } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import type { RecordItem } from '@/__shared__/types/models'
import type { TransactionFilters } from '@/api/types'
import { exportTransactionsUrl } from '@/api/transactions'
import { exportRecords, type ExportFormat } from '@/__shared__/utils/export-records'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'

/** Меню «Экспорт»: форматы файлов, которые реально формируются на клиенте. */
const EXPORT_FORMATS: Array<{ value: ExportFormat; labelKey: TranslationKey; icon: typeof FileSpreadsheet }> = [
  { value: 'csv', labelKey: 'export.csv', icon: FileText },
  { value: 'tsv', labelKey: 'export.tsv', icon: FileText },
  { value: 'xls', labelKey: 'export.xls', icon: FileSpreadsheet },
  { value: 'json', labelKey: 'export.json', icon: FileJson },
  { value: 'pdf', labelKey: 'export.pdf', icon: FileDown },
]

/**
 * Меню «Экспорт».
 *
 * Две группы: пять форматов собираются на клиенте из загруженной страницы
 * (включая PDF через печать), а CSV и JSON выгружает сервер — он отдаёт весь
 * список под текущими фильтрами, а не только то, что успело загрузиться.
 */
export function ExportMenu({
  items,
  serverFilters,
}: {
  items: RecordItem[]
  /** Фильтры для серверной выгрузки: без них вторая группа не показывается */
  serverFilters?: TransactionFilters
}) {
  const { t, locale } = useI18n()
  const { toast } = useToast()

  /** Серверная выгрузка: переход по ссылке, cookie уедет вместе с запросом. */
  const downloadFromServer = (format: 'csv' | 'json') => {
    if (!serverFilters) return
    const link = document.createElement('a')
    link.href = exportTransactionsUrl({ ...serverFilters, format })
    link.rel = 'noopener'
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="glass" size="sm" className="gap-1.5">
          <Download className="size-4" aria-hidden="true" />
          {t('records.export')}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>{t('records.exportLoaded')}</DropdownMenuLabel>
        {EXPORT_FORMATS.map((format) => (
          <DropdownMenuItem
            key={format.value}
            onSelect={() => {
              exportRecords(items, format.value, locale)
              toast({
                title: format.value === 'pdf' ? t('records.export') : t('export.done'),
                description: format.value === 'pdf' ? t('export.print') : t(format.labelKey),
                tone: 'success',
              })
            }}
          >
            <format.icon className="size-4 text-fg-tertiary" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">{t(format.labelKey)}</span>
          </DropdownMenuItem>
        ))}

        {serverFilters && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel>{t('records.exportAll')}</DropdownMenuLabel>
            {(['csv', 'json'] as const).map((format) => (
              <DropdownMenuItem
                key={`server-${format}`}
                onSelect={() => {
                  downloadFromServer(format)
                  toast({ title: t('export.done'), description: t(`export.${format}`), tone: 'success' })
                }}
              >
                <Server className="size-4 text-fg-tertiary" aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate">
                  {t(`export.${format}`)} · {t('records.exportFromServer')}
                </span>
              </DropdownMenuItem>
            ))}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

