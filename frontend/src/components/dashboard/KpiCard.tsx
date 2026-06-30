import React from 'react'
import { Skeleton } from '@/components/ui'

interface KpiCardProps {
  title: string
  value: number | string
  delta?: number
  unit?: string
  loading?: boolean
  // Legacy compat props
  subtitle?: string
  trend?: number
  icon?: React.ReactNode
  isLoading?: boolean
  color?: 'default' | 'success' | 'warning' | 'danger'
}

export function KpiCard({
  title,
  value,
  delta,
  unit,
  loading,
  subtitle,
  trend,
  icon,
  isLoading,
  color = 'default',
}: KpiCardProps) {
  const showLoading = loading ?? isLoading ?? false
  const effectiveDelta = delta ?? trend

  const colorBorder: Record<string, string> = {
    default: 'border-neutral-700',
    success: 'border-green-800',
    warning: 'border-yellow-800',
    danger: 'border-red-800',
  }

  return (
    <div className={`rounded-xl border bg-neutral-900 p-5 ${colorBorder[color]}`}>
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-neutral-400">{title}</p>
        {icon && <span className="text-neutral-500">{icon}</span>}
      </div>

      {showLoading ? (
        <div className="mt-2 space-y-2">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : (
        <>
          <p className="mt-2 text-3xl font-bold text-neutral-100 tabular-nums">
            {value}{unit ? <span className="text-lg ml-1 text-neutral-400">{unit}</span> : null}
          </p>
          <div className="mt-1 flex items-center gap-2">
            {effectiveDelta !== undefined && (
              <span
                className={`text-xs font-semibold ${
                  effectiveDelta > 0
                    ? 'text-green-400'
                    : effectiveDelta < 0
                      ? 'text-red-400'
                      : 'text-neutral-500'
                }`}
              >
                {effectiveDelta > 0 ? '↑' : effectiveDelta < 0 ? '↓' : '→'}{' '}
                {Math.abs(effectiveDelta)}%
              </span>
            )}
            {subtitle && (
              <span className="text-xs text-neutral-500">{subtitle}</span>
            )}
          </div>
        </>
      )}
    </div>
  )
}
