import React from 'react'
import { clsx } from 'clsx'

export type BadgeColor = 'success' | 'warning' | 'danger' | 'neutral' | 'info'
export type BadgeSize = 'sm' | 'md'

export interface BadgeProps {
  color?: BadgeColor
  size?: BadgeSize
  children: React.ReactNode
  className?: string
}

const colorClasses: Record<BadgeColor, string> = {
  success: 'bg-success-900 text-success-300 border-success-800',
  warning: 'bg-warning-950 text-warning-300 border-warning-800',
  danger: 'bg-danger-950 text-danger-300 border-danger-800',
  neutral: 'bg-neutral-800 text-neutral-300 border-neutral-700',
  info: 'bg-brand-950 text-brand-300 border-brand-800',
}

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
}

export function Badge({ color = 'neutral', size = 'sm', children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border font-semibold uppercase tracking-wide',
        colorClasses[color],
        sizeClasses[size],
        className,
      )}
    >
      {children}
    </span>
  )
}
