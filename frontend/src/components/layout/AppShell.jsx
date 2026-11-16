import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import NotificationToast from '../notifications/NotificationToast'
import { apiClient } from '../../client'
import { RefreshCw } from 'lucide-react'

export default function AppShell() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [backendWakingUp, setBackendWakingUp] = useState(false)

  useEffect(() => {
    let active = true
    const checkHealth = async () => {
      try {
        const res = await apiClient.get('/health', { timeout: 4000 })
        if (res.data?.status === 'ok' && active) {
          setBackendWakingUp(false)
        }
      } catch (err) {
        if (active) {
          setBackendWakingUp(true)
          setTimeout(checkHealth, 5000)
        }
      }
    }
    checkHealth()
    return () => { active = false }
  }, [])

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} />
      <div className="flex flex-col flex-1 w-full overflow-hidden">
        {backendWakingUp && (
          <div className="bg-amber-600 text-white text-xs sm:text-sm px-4 py-2 flex items-center justify-center space-x-2 shadow-sm animate-pulse shrink-0">
            <RefreshCw className="w-4 h-4 animate-spin shrink-0" />
            <span>Backend service may be spinning up from cold sleep (takes ~50s on Render Free tier). Reconnecting...</span>
          </div>
        )}
        <TopBar onMenuClick={() => setIsMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
      <NotificationToast />
    </div>
  )
}
