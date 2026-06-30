import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as fc from 'fast-check'
import { Modal } from '@/components/ui/Modal'

function TestModal({ isOpen = true, onClose = vi.fn() }: { isOpen?: boolean; onClose?: () => void }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Test Modal" footer={<button>Action</button>}>
      <p>Modal body content</p>
    </Modal>
  )
}

describe('Modal', () => {
  it('renders when isOpen is true', () => {
    render(<TestModal />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Test Modal')).toBeInTheDocument()
    expect(screen.getByText('Modal body content')).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(<TestModal isOpen={false} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('has aria-modal="true"', () => {
    render(<TestModal />)
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true')
  })

  it('calls onClose when close button clicked', async () => {
    const onClose = vi.fn()
    render(<TestModal onClose={onClose} />)
    await userEvent.click(screen.getByLabelText('Close modal'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose on Escape key', async () => {
    const onClose = vi.fn()
    render(<TestModal onClose={onClose} />)
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calls onClose on backdrop click', async () => {
    const onClose = vi.fn()
    render(<TestModal onClose={onClose} />)
    // Backdrop is aria-hidden, click the fixed container's backdrop div
    const backdrop = document.querySelector('[aria-hidden="true"]')
    if (backdrop) await userEvent.click(backdrop)
    expect(onClose).toHaveBeenCalled()
  })

  it('renders footer slot', () => {
    render(<TestModal />)
    expect(screen.getByText('Action')).toBeInTheDocument()
  })

  it('has aria-labelledby pointing to title', () => {
    render(<TestModal />)
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title')
    expect(document.getElementById('modal-title')).toHaveTextContent('Test Modal')
  })

  it('Tab wraps focus from last to first focusable element', async () => {
    render(<TestModal />)
    // Wait for focus to settle (Modal uses setTimeout of 10ms)
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20))
    })
    const dialog = screen.getByRole('dialog')
    const focusableEls = dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    const lastEl = focusableEls[focusableEls.length - 1]
    // Focus the last focusable element
    lastEl.focus()
    expect(document.activeElement).toBe(lastEl)
    // Fire Tab — focus-trap should wrap to first
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: false })
    expect(document.activeElement).toBe(focusableEls[0])
  })

  it('Shift+Tab wraps focus from first to last focusable element', async () => {
    render(<TestModal />)
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20))
    })
    const dialog = screen.getByRole('dialog')
    const focusableEls = dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    const firstEl = focusableEls[0]
    // Focus the first focusable element
    firstEl.focus()
    expect(document.activeElement).toBe(firstEl)
    // Fire Shift+Tab — focus-trap should wrap to last
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(focusableEls[focusableEls.length - 1])
  })

  it('Tab with no focusable elements is prevented (no throw)', async () => {
    // Render modal with no interactive children
    render(
      <Modal isOpen={true} onClose={vi.fn()} title="Empty Modal">
        <span>Just text, no buttons</span>
      </Modal>,
    )
    // Should not throw even with no focusable elements
    expect(() =>
      fireEvent.keyDown(document, { key: 'Tab', shiftKey: false }),
    ).not.toThrow()
  })

  it('property: onClose is called once per Escape key press', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 5 }), (presses) => {
        const onClose = vi.fn()
        const { unmount } = render(<TestModal onClose={onClose} />)
        for (let i = 0; i < presses; i++) {
          fireEvent.keyDown(document, { key: 'Escape' })
        }
        const callCount = onClose.mock.calls.length
        unmount()
        return callCount === presses
      }),
      { numRuns: 100 },
    )
  })
})
