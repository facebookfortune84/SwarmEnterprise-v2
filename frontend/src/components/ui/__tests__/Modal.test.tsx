import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
})
