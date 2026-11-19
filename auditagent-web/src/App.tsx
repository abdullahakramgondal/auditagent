import { Route, Routes } from 'react-router'
import { AppShell } from './app/AppShell'
import { RequireLogin } from '@/features/auth'
import { AuditPage } from './pages/AuditPage'
import { DashboardPage } from './pages/DashboardPage'
import { HistoryPage } from './pages/HistoryPage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { RegisterPage } from './pages/RegisterPage'
import { UploadPage } from './pages/UploadPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route element={<RequireLogin />}>
          <Route index element={<DashboardPage />} />
          <Route path="new" element={<UploadPage />} />
          <Route path="audits/:id" element={<AuditPage />} />
          <Route path="history" element={<HistoryPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}