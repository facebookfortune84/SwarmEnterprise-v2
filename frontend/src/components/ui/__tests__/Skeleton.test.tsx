import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skeleton } from '@/components/ui/Skeleton'

describe('Skeleton', () => {
  it('renders with role="status"', () => {
    render(<Skeleton />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('has default aria-label', () => {
    render(<Skeleton />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading…')
  })

  it('accepts custom aria-label', () => {
    render(<Skeleton aria-label="Custom loading" />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Custom loading')
  })

  it('passes className', () => {
    render(<Skeleton className="h-8 w-32" />)
    expect(screen.getByRole('status')).toHaveClass('h-8', 'w-32')
  })
})
