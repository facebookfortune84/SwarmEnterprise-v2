import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Select } from '@/components/ui/Select'

const OPTIONS = [
  { value: 'a', label: 'Option A' },
  { value: 'b', label: 'Option B' },
  { value: 'c', label: 'Option C', disabled: true },
]

describe('Select', () => {
  it('renders all options', () => {
    render(<Select label="Choose" options={OPTIONS} />)
    expect(screen.getByText('Option A')).toBeInTheDocument()
    expect(screen.getByText('Option B')).toBeInTheDocument()
  })

  it('renders placeholder when provided', () => {
    render(<Select options={OPTIONS} placeholder="Pick one" />)
    expect(screen.getByText('Pick one')).toBeInTheDocument()
  })

  it('shows error', () => {
    render(<Select options={OPTIONS} label="Select" error="Required" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Required')
    expect(screen.getByLabelText('Select')).toHaveAttribute('aria-invalid', 'true')
  })

  it('fires onChange', async () => {
    const onChange = vi.fn()
    render(<Select label="Pick" options={OPTIONS} onChange={onChange} />)
    await userEvent.selectOptions(screen.getByLabelText('Pick'), 'a')
    expect(onChange).toHaveBeenCalled()
  })

  it('is disabled', () => {
    render(<Select label="Disabled" options={OPTIONS} disabled />)
    expect(screen.getByLabelText('Disabled')).toBeDisabled()
  })

  it('renders required star', () => {
    render(<Select label="Required" options={OPTIONS} required />)
    expect(screen.getByText('*')).toBeInTheDocument()
  })
})
