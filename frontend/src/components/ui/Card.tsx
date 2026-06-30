import React from 'react'
import { clsx } from 'clsx'

export interface CardProps {
  header?: React.ReactNode
  footer?: React.ReactNode
  children?: React.ReactNode
  className?: string
  onClick?: () => void
}

export function Card({ header, footer, children, className, onClick }: CardProps) {
  const isClickable = !!onClick

  return (
    <div
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick()
              }
            }
          : undefined
      }
      className={clsx(
        'rounded-xl border border-neutral-700 bg-neutral-900 shadow-md',
        isClickable && 'cursor-pointer hover:border-neutral-600 hover:shadow-lg transition-all',
        className,
      )}
    >
      {header && (
        <div className="border-b border-neutral-700 px-5 py-4 font-semibold text-neutral-100">
          {header}
        </div>
      )}
      {children && <div className="px-5 py-4">{children}</div>}
      {footer && (
        <div className="border-t border-neutral-700 px-5 py-3 text-sm text-neutral-400">
          {footer}
        </div>
      )}
    </div>
  )
}
