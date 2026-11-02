import { useState, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from '../hooks/useTheme'
import { I18nProvider } from '../i18n'
import { AppRoot } from './AppRoot'
import { RequireAuth, SessionGate } from './SessionGate'
import { DashboardPage } from '../__pages__/Dashboard'
import { AccountsPage } from '../__pages__/Accounts'
import { RecordsPage } from '../__pages__/Records'
import type { RecordItem } from '@/__shared__/types/models'
import { AnalyticsPage } from '../__pages__/Analytics'
import { SettingsPage } from '../__pages__/Settings'
import { SettingsCurrenciesPage } from '../__pages__/SettingsCurrencies'
import { SettingsCategoriesPage } from '../__pages__/SettingsCategories'
import { SettingsPrivacyPage, SettingsRulesPage, SettingsTagsPage, SettingsTemplatesPage } from '../__pages__/SettingsExtras'
import { SettingsPaymentsPage } from '../__pages__/SettingsPayments'
import { AccountDetailPage } from '../__pages__/AccountDetail'
import { LoginPage } from '../__pages__/Login'
import { RegisterPage } from '../__pages__/Register'
import { VerifyEmailPage } from '../__pages__/VerifyEmail'
import { FeaturesPage } from '../__pages__/Features'
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

  /** Рабочие экраны — только после входа: сессия проверяется один раз в SessionGate. */
  const guarded = (page: ReactNode) => <RequireAuth>{page}</RequireAuth>

  return (
    <ThemeProvider>
      <I18nProvider>
        <BrowserRouter>
          <AppRoot>
            <SessionGate>
              <RecordDialogProvider value={{ openCreate: openAddRecord, openEdit: openEditRecord }}>
                <Routes>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/verify-email" element={<VerifyEmailPage />} />
                  <Route path="/features" element={<FeaturesPage />} />
                  <Route path="/" element={guarded(<DashboardPage />)} />
                  <Route path="/accounts" element={guarded(<AccountsPage />)} />
                  <Route path="/accounts/:accountId" element={guarded(<AccountDetailPage />)} />
                  <Route path="/records" element={guarded(<RecordsPage />)} />
                  <Route path="/analytics" element={guarded(<AnalyticsPage />)} />
                  <Route path="/settings" element={guarded(<SettingsPage />)} />
                  <Route path="/settings/currencies" element={guarded(<SettingsCurrenciesPage />)} />
                  <Route path="/settings/categories" element={guarded(<SettingsCategoriesPage />)} />
                  <Route path="/settings/templates" element={guarded(<SettingsTemplatesPage />)} />
                  <Route path="/settings/tags" element={guarded(<SettingsTagsPage />)} />
                  <Route path="/settings/rules" element={guarded(<SettingsRulesPage />)} />
                  <Route path="/settings/payments" element={guarded(<SettingsPaymentsPage />)} />
                  <Route path="/settings/privacy" element={guarded(<SettingsPrivacyPage />)} />
                  {/* Витрина компонентов: не требует данных и остаётся доступной */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
                <AddRecordDialog
                  open={addOpen}
                  onOpenChange={(next) => {
                    setAddOpen(next)
                    if (!next) setEditingRecord(null)
                  }}
                  record={editingRecord}
                />
              </RecordDialogProvider>
            </SessionGate>
          </AppRoot>
        </BrowserRouter>
      </I18nProvider>
    </ThemeProvider>
  )
}

const rootElement = document.getElementById('root')
if (!rootElement) throw new Error('Failed to find the root element')
createRoot(rootElement).render(<App />)
