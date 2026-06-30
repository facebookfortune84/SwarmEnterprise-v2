import React from 'react'
import { clsx } from 'clsx'

export interface Tab {
  id: string
  label: string
  disabled?: boolean
}

export interface TabsProps {
  tabs: Tab[]
  activeTab: string
  onChange: (id: string) => void
  className?: string
  children?: React.ReactNode
}

export function Tabs({ tabs, activeTab, onChange, className, children }: TabsProps) {
  return (
    <div className={clsx('flex flex-col', className)}>
      <div
        role="tablist"
        aria-label="Navigation tabs"
        className="flex border-b border-neutral-700 overflow-x-auto"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => onChange(tab.id)}
            className={clsx(
              'px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors',
              'border-b-2 -mb-px focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-500',
              'disabled:cursor-not-allowed disabled:opacity-50',
              activeTab === tab.id
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-neutral-400 hover:text-neutral-200 hover:border-neutral-500',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  )
}

export interface TabPanelProps {
  id: string
  activeTab: string
  children: React.ReactNode
  className?: string
}

export function TabPanel({ id, activeTab, children, className }: TabPanelProps) {
  if (activeTab !== id) return null
  return (
    <div
      role="tabpanel"
      id={`tabpanel-${id}`}
      aria-labelledby={`tab-${id}`}
      tabIndex={0}
      className={className}
    >
      {children}
    </div>
  )
}
