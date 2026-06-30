import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageHeader } from '@/components/ui/PageHeader'

describe('PageHeader', () => {
  it('renders title as h1', () => {
    render(<PageHeader title="Dashboard" />)
    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
  })

  it('renders subtitle', () => {
    render(<PageHeader title="Page" subtitle="A description" />)
    expect(screen.getByText('A description')).toBeInTheDocument()
  })

  it('renders actions slot', () => {
    render(<PageHeader title="Page" actions={<button>Action</button>} />)
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
  })

  it('does not render subtitle element when not provided', () => {
    render(<PageHeader title="Page" />)
    expect(screen.queryByText(/description/)).not.toBeInTheDocument()
  })

  it('passes className to header', () => {
    const { container } = render(<PageHeader title="Page" className="custom" />)
    expect(container.firstChild).toHaveClass('custom')
  })
})
