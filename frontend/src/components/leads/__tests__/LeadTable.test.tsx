import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LeadTable } from '@/components/leads/LeadTable'
import type { Lead } from '@/types/api'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const makeQC = () => new QueryClient({ defaultOptions: { queries: { retry: false } } })

const makeLead = (overrides?: Partial<Lead>): Lead => ({
  id: 'lead-1',
  email: 'alice@example.com',
  name: 'Alice Smith',
  company: 'Acme Corp',
  status: 'NEW',
  created_at: '2024-01-01T00:00:00Z',
  ...overrides,
})

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeQC()}>
      {children}
    </QueryClientProvider>
  )
}

describe('LeadTable', () => {
  it('renders column headers', () => {
    render(<LeadTable leads={[]} onSelect={vi.fn()} selectedIds={[]} />, { wrapper })
    expect(screen.getByText('Name')).toBeDefined()
    expect(screen.getByText('Email')).toBeDefined()
    expect(screen.getByText('Company')).toBeDefined()
    expect(screen.getByText('Intent Score')).toBeDefined()
    expect(screen.getByText('Status')).toBeDefined()
  })

  it('shows loading skeleton', () => {
    const { container } = render(
      <LeadTable leads={[]} loading onSelect={vi.fn()} selectedIds={[]} />,
      { wrapper }
    )
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('calls onSelect when checkbox clicked', () => {
    const onSelect = vi.fn()
    const lead = makeLead()
    render(<LeadTable leads={[lead]} onSelect={onSelect} selectedIds={[]} />, { wrapper })
    const checkboxes = screen.getAllByRole('checkbox')
    // First is "select all", second is row checkbox
    fireEvent.click(checkboxes[1])
    expect(onSelect).toHaveBeenCalled()
  })

  it('intent score ≥70 shows green badge', () => {
    const lead = makeLead({ intent_score: 85 })
    const { container } = render(
      <LeadTable leads={[lead]} onSelect={vi.fn()} selectedIds={[]} />,
      { wrapper }
    )
    const badge = container.querySelector('.text-success-700')
    expect(badge).toBeDefined()
  })

  it('intent score 40-69 shows yellow badge', () => {
    const lead = makeLead({ intent_score: 55 })
    const { container } = render(
      <LeadTable leads={[lead]} onSelect={vi.fn()} selectedIds={[]} />,
      { wrapper }
    )
    const badge = container.querySelector('.text-warning-700')
    expect(badge).toBeDefined()
  })

  it('intent score <40 shows red badge', () => {
    const lead = makeLead({ intent_score: 20 })
    const { container } = render(
      <LeadTable leads={[lead]} onSelect={vi.fn()} selectedIds={[]} />,
      { wrapper }
    )
    const badge = container.querySelector('.text-danger-700')
    expect(badge).toBeDefined()
  })

  it('renders lead name and email', () => {
    const lead = makeLead()
    render(<LeadTable leads={[lead]} onSelect={vi.fn()} selectedIds={[]} />, { wrapper })
    expect(screen.getByText('Alice Smith')).toBeDefined()
    expect(screen.getByText('alice@example.com')).toBeDefined()
  })

  it('shows empty state for empty leads', () => {
    render(<LeadTable leads={[]} onSelect={vi.fn()} selectedIds={[]} />, { wrapper })
    expect(screen.getByText('No leads found.')).toBeDefined()
  })

  it('selects all when select-all checkbox clicked', () => {
    const onSelect = vi.fn()
    const leads = [makeLead({ id: 'l1' }), makeLead({ id: 'l2', email: 'b@b.com' })]
    render(<LeadTable leads={leads} onSelect={onSelect} selectedIds={[]} />, { wrapper })
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0]) // select all
    expect(onSelect).toHaveBeenCalledWith(['l1', 'l2'])
  })

  it('deselects all when all are selected and select-all clicked', () => {
    const onSelect = vi.fn()
    const leads = [makeLead({ id: 'l1' })]
    render(
      <LeadTable leads={leads} onSelect={onSelect} selectedIds={['l1']} />,
      { wrapper }
    )
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    expect(onSelect).toHaveBeenCalledWith([])
  })
})
