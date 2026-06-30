import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Textarea } from '@/components/ui/Textarea'

describe('Textarea', () => {
  it('renders with label', () => {
    render(<Textarea label="Message" />)
    expect(screen.getByLabelText('Message')).toBeInTheDocument()
  })

  it('shows error', () => {
    render(<Textarea label="Field" error="Too short" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Too short')
  })

  it('shows helper text', () => {
    render(<Textarea label="Notes" helperText="Max 500 chars" />)
    expect(screen.getByText('Max 500 chars')).toBeInTheDocument()
  })

  it('shows character counter when showCount and maxLength', () => {
    render(<Textarea label="Bio" showCount maxLength={100} value="hello" onChange={() => undefined} />)
    expect(screen.getByText('5/100')).toBeInTheDocument()
  })

  it('fires onChange', async () => {
    const onChange = vi.fn()
    render(<Textarea label="Message" onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('Message'), 'test')
    expect(onChange).toHaveBeenCalled()
  })

  it('is disabled', () => {
    render(<Textarea label="Disabled" disabled />)
    expect(screen.getByLabelText('Disabled')).toBeDisabled()
  })

  it('forwards ref', () => {
    const ref = { current: null as HTMLTextAreaElement | null }
    render(<Textarea ref={ref} />)
    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement)
  })
})
