import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Card } from '@/components/ui/Card'

describe('Card', () => {
  it('renders children', () => {
    render(<Card><p>Body</p></Card>)
    expect(screen.getByText('Body')).toBeInTheDocument()
  })

  it('renders header slot', () => {
    render(<Card header="Card Title"><p>Body</p></Card>)
    expect(screen.getByText('Card Title')).toBeInTheDocument()
  })

  it('renders footer slot', () => {
    render(<Card footer="Footer text"><p>Body</p></Card>)
    expect(screen.getByText('Footer text')).toBeInTheDocument()
  })

  it('is not interactive without onClick', () => {
    render(<Card><p>Static</p></Card>)
    const card = screen.getByText('Static').closest('div')
    expect(card).not.toHaveAttribute('role', 'button')
  })

  it('has role="button" with onClick', () => {
    const onClick = vi.fn()
    render(<Card onClick={onClick}><p>Clickable</p></Card>)
    const card = screen.getByRole('button')
    expect(card).toBeInTheDocument()
  })

  it('fires onClick when clicked', async () => {
    const onClick = vi.fn()
    render(<Card onClick={onClick}><p>Click me</p></Card>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('fires onClick on Enter key', async () => {
    const onClick = vi.fn()
    render(<Card onClick={onClick}><p>Key</p></Card>)
    const card = screen.getByRole('button')
    card.focus()
    await userEvent.keyboard('{Enter}')
    expect(onClick).toHaveBeenCalled()
  })

  it('passes className', () => {
    const { container } = render(<Card className="my-class"><p>X</p></Card>)
    expect(container.firstChild).toHaveClass('my-class')
  })
})
