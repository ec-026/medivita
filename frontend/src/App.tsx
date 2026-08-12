import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layouts/AppShell'
import { ChatPage } from './pages/ChatPage'
import { HealthCheckPage } from './pages/HealthCheckPage'
import { NewsPage } from './pages/NewsPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SourcesPage } from './pages/SourcesPage'

export default function App() {
  return <Routes>
    <Route element={<AppShell />}>
      <Route index element={<Navigate to="/chat" replace />} />
      <Route path="chat" element={<ChatPage />} />
      <Route path="health-check" element={<HealthCheckPage />} />
      <Route path="news" element={<NewsPage />} />
      <Route path="sources" element={<SourcesPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Route>
  </Routes>
}
