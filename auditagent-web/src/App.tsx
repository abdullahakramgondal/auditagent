import { Route, Routes } from 'react-router'
import { AppShell } from './app/AppShell'
import { AuditPage } from './pages/AuditPage'
import { HistoryPage } from './pages/HistoryPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { UploadPage } from './pages/UploadPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<UploadPage />} />
        <Route path="audits/:id" element={<AuditPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}