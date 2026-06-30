import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BulkActionsToolbar } from '@/components/leads/BulkActionsToolbar'

describe('BulkActionsToolbar', () => {
  it('does not render when selectedCount=0', () => {
    const { container } = render(
      <BulkActionsToolbar
        selectedCount={0}
        onEnrich={vi.fn()}
        onExport={vi.fn()}
        onDelete={vi.fn()}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders when selectedCount>0', () => {
    render(
      <BulkActionsToolbar
        selectedCount={3}
        onEnrich={vi.fn()}
        onExport={vi.fn()}
        onDelete={vi.fn()}
      />
    )
    expect(screen.getByText('3 selected')).toBeDefined()
  })

  it('shows count badge', () => {
    render(
      <BulkActionsToolbar
        selectedCount={7}
        onEnrich={vi.fn()}
        onExport={vi.fn()}
        onDelete={vi.fn()}
      />
    )
    expect(screen.getByText('7 selected')).toBeDefined()
  })

  it('calls onEnrich when Enrich clicked', () => {
    const onEnrich = vi.fn()
    render(
      <BulkActionsToolbar
        selectedCount={1}
        onEnrich={onEnrich}
        onExport={vi.fn()}
        onDelete={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('Enrich'))
    expect(onEnrich).toHaveBeenCalled()
  })

  it('calls onExport when Export clicked', () => {
    const onExport = vi.fn()
    render(
      <BulkActionsToolbar
        selectedCount={1}
        onEnrich={vi.fn()}
        onExport={onExport}
        onDelete={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('Export'))
    expect(onExport).toHaveBeenCalled()
  })

  it('shows confirm dialog before calling onDelete', () => {
    const onDelete = vi.fn()
    render(
      <BulkActionsToolbar
        selectedCount={2}
        onEnrich={vi.fn()}
        onExport={vi.fn()}
        onDelete={onDelete}
      />
    )
    // Click Delete button
    fireEvent.click(screen.getByText('Delete'))
    // Should show confirm dialog, NOT call onDelete yet
    expect(onDelete).not.toHaveBeenCalled()
    expect(screen.getByText('Are you sure?')).toBeDefined()
  })

  it('calls onDelete after confirmation', () => {
    const onDelete = vi.fn()
    render(
      <BulkActionsToolbar
        selectedCount={2}
        onEnrich={vi.fn()}
        onExport={vi.fn()}
        onDelete={onDelete}
      />
    )
    fireEvent.click(screen.getByText('Delete'))
    fireEvent.click(screen.getByText('Confirm'))
    expect(onDelete).toHaveBeenCalled()
  })

  it('cancel closes confirm dialog without calling onDelete', () => {
    const onDelete = vi.fn()
    render(
      <BulkActionsToolbar
        selectedCount={2}
        onEnrich={vi.fn()}
        onExport={vi.fn()}
        onDelete={onDelete}
      />
    )
    fireEvent.click(screen.getByText('Delete'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(onDelete).not.toHaveBeenCalled()
    expect(screen.queryByText('Are you sure?')).toBeNull()
  })

  it('does not call onEnrich when disabled', () => {
    const onEnrich = vi.fn()
    render(
      <BulkActionsToolbar
        selectedCount={1}
        onEnrich={onEnrich}
        onExport={vi.fn()}
        onDelete={vi.fn()}
        disabled
      />
    )
    const btn = screen.getByText('Enrich').closest('button')
    expect(btn?.disabled).toBe(true)
  })
})
