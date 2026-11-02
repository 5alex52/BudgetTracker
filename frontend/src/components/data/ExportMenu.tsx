import { Download, FileDown, FileJson, FileSpreadsheet, FileText } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import type { RecordItem } from '@/__shared__/types/models'
import { exportRecords, type ExportFormat } from '@/__shared__/utils/export-records'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'

/** Меню «Экспорт»: форматы файлов, которые реально формируются на клиенте. */
const EXPORT_FORMATS: Array<{ value: ExportFormat; labelKey: TranslationKey; icon: typeof FileSpreadsheet }> = [
  { value: 'csv', labelKey: 'export.csv', icon: FileText },
  { value: 'tsv', labelKey: 'export.tsv', icon: FileText },
  { value: 'xls', labelKey: 'export.xls', icon: FileSpreadsheet },
  { value: 'json', labelKey: 'export.json', icon: FileJson },
  { value: 'pdf', labelKey: 'export.pdf', icon: FileDown },
]

export function ExportMenu({ items }: { items: RecordItem[] }) {
  const { t, locale } = useI18n()
  const { toast } = useToast()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="glass" size="sm" className="gap-1.5">
          <Download className="size-4" aria-hidden="true" />
          {t('records.export')}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>{t('records.export')}</DropdownMenuLabel>
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
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

