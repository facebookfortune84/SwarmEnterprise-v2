import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KpiCard } from '@/components/dashboard/KpiCard'

describe('KpiCard', () => {
  it('renders title and value', () => {
    render(<KpiCard title="Total Leads" value={42} />)
    expect(screen.getByText('Total Leads')).toBeDefined()
    expect(screen.getByText('42')).toBeDefined()
  })

  it('shows skeleton when loading', () => {
    const { container } = render(<KpiCard title="Loading" value={0} loading />)
    // Skeleton has animate-pulse class
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows skeleton when isLoading', () => {
    const { container } = render(<KpiCard title="Loading" value={0} isLoading />)
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows green delta for positive values', () => {
    const { container } = render(<KpiCard title="Growth" value={100} delta={15} />)
    const deltaEl = container.querySelector('.text-green-400')
    expect(deltaEl).toBeDefined()
    expect(deltaEl?.textContent).toContain('↑')
    expect(deltaEl?.textContent).toContain('15')
  })

  it('shows red delta for negative values', () => {
    const { container } = render(<KpiCard title="Decline" value={80} delta={-5} />)
    const deltaEl = container.querySelector('.text-red-400')
    expect(deltaEl).toBeDefined()
    expect(deltaEl?.textContent).toContain('↓')
    expect(deltaEl?.textContent).toContain('5')
  })

  it('renders unit string', () => {
    render(<KpiCard title="Rate" value={95} unit="%" />)
    expect(screen.getByText('%')).toBeDefined()
  })

  it('renders with zero delta', () => {
    const { container } = render(<KpiCard title="Flat" value={50} delta={0} />)
    const deltaEl = container.querySelector('.text-neutral-500')
    expect(deltaEl).toBeDefined()
    expect(deltaEl?.textContent).toContain('→')
  })

  it('renders subtitle', () => {
    render(<KpiCard title="Metric" value={100} subtitle="vs last week" />)
    expect(screen.getByText('vs last week')).toBeDefined()
  })

  it('renders trend (legacy prop)', () => {
    const { container } = render(<KpiCard title="Trend" value={50} trend={10} />)
    const trendEl = container.querySelector('.text-green-400')
    expect(trendEl).toBeDefined()
  })

  it('renders icon', () => {
    render(<KpiCard title="Icon" value={1} icon={<span data-testid="icon">🔥</span>} />)
    expect(screen.getByTestId('icon')).toBeDefined()
  })

  it('applies success border color', () => {
    const { container } = render(<KpiCard title="OK" value={1} color="success" />)
    const card = container.firstElementChild as HTMLElement
    expect(card.className).toContain('border-green-800')
  })

  it('applies danger border color', () => {
    const { container } = render(<KpiCard title="Error" value={0} color="danger" />)
    const card = container.firstElementChild as HTMLElement
    expect(card.className).toContain('border-red-800')
  })
})
