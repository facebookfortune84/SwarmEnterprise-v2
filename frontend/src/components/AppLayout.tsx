import React, { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', icon: '🏠' },
  { path: '/companies', label: 'Companies', icon: '🏢' },
  { path: '/deployments', label: 'Deployments', icon: '🚀' },
  { path: '/tenants', label: 'Tenants', icon: '🏗️' },
  { path: '/tickets', label: 'Tickets', icon: '🎫' },
  { path: '/leads', label: 'Leads', icon: '📋' },
  { path: '/outreach', label: 'Outreach', icon: '📧' },
  { path: '/workflows', label: 'Workflows', icon: '⚙️' },
  { path: '/analytics', label: 'Analytics', icon: '📊' },
]

interface AppLayoutProps {
  children: React.ReactNode
  title?: string
}

export function AppLayout({ children, title }: AppLayoutProps) {
  const { logout } = useAuth()
  const { getDecodedToken } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const decoded = getDecodedToken()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-neutral-950">
      {/* Sidebar overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 flex w-56 flex-col border-r border-neutral-800 bg-neutral-950 transition-transform',
          'lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-14 items-center gap-2 border-b border-neutral-800 px-4">
          <span className="text-xl">⚡</span>
          <span className="text-sm font-bold text-neutral-100">SwarmEnterprise</span>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-0.5" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.path === '/dashboard'
                ? location.pathname === '/dashboard'
                : location.pathname.startsWith(item.path)
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-900 text-brand-300'
                    : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200',
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            )
          })}
          {decoded?.role === 'admin' && (
            <Link
              to="/admin"
              onClick={() => setSidebarOpen(false)}
              className={clsx(
                'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                location.pathname === '/admin'
                  ? 'bg-brand-900 text-brand-300'
                  : 'text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200',
              )}
              aria-current={location.pathname === '/admin' ? 'page' : undefined}
            >
              <span>🛡️</span>
              <span>Admin</span>
            </Link>
          )}
        </nav>

        <div className="border-t border-neutral-800 p-3 space-y-0.5">
          <Link
            to="/profile"
            className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200 transition-colors"
          >
            <span>👤</span>
            <span className="truncate">{decoded?.sub ?? 'Profile'}</span>
          </Link>
          <button
            onClick={() => { void handleLogout() }}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-neutral-400 hover:bg-neutral-800 hover:text-danger-300 transition-colors"
          >
            <span>🚪</span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <header className="flex h-14 items-center gap-4 border-b border-neutral-800 bg-neutral-950 px-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1 text-neutral-400 hover:text-neutral-200 lg:hidden"
            aria-label="Open sidebar"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          {title && <h2 className="text-sm font-semibold text-neutral-300 hidden sm:block">{title}</h2>}
        </header>
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
