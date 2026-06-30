import React from 'react'
import { clsx } from 'clsx'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
  helperText?: string
  showCount?: boolean
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, showCount = false, className, id, maxLength, value, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
    const currentLength = typeof value === 'string' ? value.length : 0

    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-neutral-300">
            {label}
            {props.required && <span className="ml-1 text-danger-400" aria-hidden="true">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          maxLength={maxLength}
          value={value}
          aria-invalid={!!error}
          aria-describedby={
            error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined
          }
          className={clsx(
            'w-full rounded-md border bg-neutral-900 px-3 py-2 text-sm text-neutral-100',
            'placeholder:text-neutral-500 resize-y',
            'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'transition-colors',
            error
              ? 'border-danger-500 focus:ring-danger-500'
              : 'border-neutral-700 hover:border-neutral-600',
            className,
          )}
          {...props}
        />
        <div className="flex justify-between items-start">
          <div>
            {error && (
              <p id={`${inputId}-error`} role="alert" className="text-xs text-danger-400">
                {error}
              </p>
            )}
            {!error && helperText && (
              <p id={`${inputId}-helper`} className="text-xs text-neutral-500">
                {helperText}
              </p>
            )}
          </div>
          {showCount && maxLength && (
            <span
              className={clsx(
                'text-xs tabular-nums ml-auto',
                currentLength >= maxLength ? 'text-danger-400' : 'text-neutral-500',
              )}
            >
              {currentLength}/{maxLength}
            </span>
          )}
        </div>
      </div>
    )
  },
)

Textarea.displayName = 'Textarea'
