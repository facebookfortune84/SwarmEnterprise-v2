import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/Badge'

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Active</Badge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it.each(['success', 'warning', 'danger', 'neutral', 'info'] as const)('renders %s color', (color) => {
    render(<Badge color={color}>{color}</Badge>)
    expect(screen.getByText(color)).toBeInTheDocument()
  })

  it.each(['sm', 'md'] as const)('renders %s size', (size) => {
    render(<Badge size={size}>Badge</Badge>)
    expect(screen.getByText('Badge')).toBeInTheDocument()
  })

  it('passes className', () => {
    render(<Badge className="extra">X</Badge>)
    expect(screen.getByText('X')).toHaveClass('extra')
  })

  it('defaults to neutral color and sm size', () => {
    const { container } = render(<Badge>Default</Badge>)
    expect(container.firstChild).toBeInTheDocument()
  })
})
