import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '../hooks/useTheme'
import { I18nProvider } from '../i18n'
import { AppRoot } from './AppRoot'
import { DashboardPage } from '../__pages__/Dashboard'
import { AccountsPage } from '../__pages__/Accounts'
import { RecordsPage } from '../__pages__/Records'
import type { RecordItem } from '@/__shared__/mock/finance'
import { AnalyticsPage } from '../__pages__/Analytics'
import { SettingsPage } from '../__pages__/Settings'
import { SettingsCurrenciesPage } from '../__pages__/SettingsCurrencies'
import { SettingsCategoriesPage } from '../__pages__/SettingsCategories'
import { SettingsPrivacyPage, SettingsRulesPage, SettingsTagsPage, SettingsTemplatesPage } from '../__pages__/SettingsExtras'
import { SettingsPaymentsPage } from '../__pages__/SettingsPayments'
import { AccountDetailPage } from '../__pages__/AccountDetail'
import { LoginPage } from '../__pages__/Login'
import { DesignPage } from '../__pages__/Design'
import { AddRecordDialog } from '../components/records/AddRecordDialog'
import { RecordDialogProvider } from '../components/records/RecordDialogContext'
import '../styles/globals.css'

function App() {
  // Один инстанс модала на всё приложение: его открывают навбар, записи и дашборд.
  const [addOpen, setAddOpen] = useState(false)
  /** Запись, которую редактируем: null — режим создания */
  const [editingRecord, setEditingRecord] = useState<RecordItem | null>(null)
  const openAddRecord = () => {
    setEditingRecord(null)
    setAddOpen(true)
  }
  const openEditRecord = (item: RecordItem) => {
    setEditingRecord(item)
    setAddOpen(true)
  }

  return (
    <ThemeProvider>
      <I18nProvider>
        <BrowserRouter>
          <AppRoot>
            <RecordDialogProvider value={{ openCreate: openAddRecord, openEdit: openEditRecord }}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/accounts" element={<AccountsPage />} />
              <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
              <Route path="/records" element={<RecordsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/settings/currencies" element={<SettingsCurrenciesPage />} />
              <Route path="/settings/categories" element={<SettingsCategoriesPage />} />
              <Route path="/settings/templates" element={<SettingsTemplatesPage />} />
              <Route path="/settings/tags" element={<SettingsTagsPage />} />
              <Route path="/settings/rules" element={<SettingsRulesPage />} />
              <Route path="/settings/payments" element={<SettingsPaymentsPage />} />
              <Route path="/settings/privacy" element={<SettingsPrivacyPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/design" element={<DesignPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            </RecordDialogProvider>
            <AddRecordDialog
          open={addOpen}
          onOpenChange={(next) => {
            setAddOpen(next)
            if (!next) setEditingRecord(null)
          }}
          record={editingRecord}
        />
          </AppRoot>
        </BrowserRouter>
      </I18nProvider>
    </ThemeProvider>
  )
}

const rootElement = document.getElementById('root')
if (!rootElement) throw new Error('Failed to find the root element')
createRoot(rootElement).render(<App />)
