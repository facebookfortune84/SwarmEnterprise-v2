import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tabs, TabPanel } from '@/components/ui/Tabs'

const TABS = [
  { id: 'tab1', label: 'First' },
  { id: 'tab2', label: 'Second' },
  { id: 'tab3', label: 'Third', disabled: true },
]

describe('Tabs', () => {
  it('renders all tab buttons', () => {
    render(<Tabs tabs={TABS} activeTab="tab1" onChange={() => undefined} />)
    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
    expect(screen.getByText('Third')).toBeInTheDocument()
  })

  it('marks the active tab with aria-selected', () => {
    render(<Tabs tabs={TABS} activeTab="tab1" onChange={() => undefined} />)
    expect(screen.getByRole('tab', { name: 'First' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Second' })).toHaveAttribute('aria-selected', 'false')
  })

  it('calls onChange when a tab is clicked', async () => {
    const onChange = vi.fn()
    render(<Tabs tabs={TABS} activeTab="tab1" onChange={onChange} />)
    await userEvent.click(screen.getByText('Second'))
    expect(onChange).toHaveBeenCalledWith('tab2')
  })

  it('disabled tab cannot be clicked', async () => {
    const onChange = vi.fn()
    render(<Tabs tabs={TABS} activeTab="tab1" onChange={onChange} />)
    const disabled = screen.getByRole('tab', { name: 'Third' })
    expect(disabled).toBeDisabled()
    await userEvent.click(disabled)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('has role="tablist"', () => {
    render(<Tabs tabs={TABS} activeTab="tab1" onChange={() => undefined} />)
    expect(screen.getByRole('tablist')).toBeInTheDocument()
  })
})

describe('TabPanel', () => {
  it('renders when activeTab matches', () => {
    render(<TabPanel id="tab1" activeTab="tab1"><p>Content</p></TabPanel>)
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('does not render when activeTab does not match', () => {
    render(<TabPanel id="tab2" activeTab="tab1"><p>Hidden</p></TabPanel>)
    expect(screen.queryByText('Hidden')).not.toBeInTheDocument()
  })

  it('has role="tabpanel"', () => {
    render(<TabPanel id="tab1" activeTab="tab1"><p>Panel</p></TabPanel>)
    expect(screen.getByRole('tabpanel')).toBeInTheDocument()
  })
})
