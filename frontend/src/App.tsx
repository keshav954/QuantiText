/**
 * App root — auth guard + layout shell with sidebar + router.
 */

import { Routes, Route, Navigate } from 'react-router-dom'
import { DateRangeProvider } from '@/store/date-range-context'
import { Sidebar } from '@/components/layout/sidebar'
import { TopBar } from '@/components/layout/top-bar'
import { Dashboard } from '@/pages/dashboard'
import { LoginPage } from '@/pages/login'
import { ForecastsPage } from '@/pages/forecasts'
import { InventoryPage } from '@/pages/inventory'
import { AlertsPage } from '@/pages/alerts'
import { CopilotPage } from '@/pages/copilot'
import { ReportsPage } from '@/pages/reports'
import { AdminPage } from '@/pages/admin'
import { getToken } from '@/api/auth'

/** Redirects to /login if no JWT token is stored. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function AppShell() {
  return (
    <DateRangeProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/copilot" element={<CopilotPage />} />
              <Route path="/forecasts" element={<ForecastsPage />} />
              <Route path="/inventory" element={<InventoryPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </DateRangeProvider>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      />
    </Routes>
  )
}
