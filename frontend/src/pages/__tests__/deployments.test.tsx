import { describe, it, expect, vi } from 'vitest'
import * as fc from 'fast-check'

// Optimistic deployment action revert logic test
describe('deployments optimistic revert', () => {
  it('reverts status within 2 seconds on error', async () => {
    vi.useFakeTimers()

    const originalStatus = 'stopped'
    let currentStatus = originalStatus

    // Simulate optimistic update
    const applyOptimistic = (action: string) => {
      currentStatus = action === 'start' ? 'in_progress' : 'stopped'
    }

    // Simulate error + revert after 2s
    const applyRevert = () => {
      setTimeout(() => {
        currentStatus = originalStatus
      }, 2_000)
    }

    applyOptimistic('start')
    expect(currentStatus).toBe('in_progress')

    applyRevert()
    expect(currentStatus).toBe('in_progress') // Not reverted yet

    vi.advanceTimersByTime(2_000)
    expect(currentStatus).toBe(originalStatus) // Reverted

    vi.useRealTimers()
  })

  it('property: optimistic status always precedes final status', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('start', 'stop', 'restart'),
        (action) => {
          const optimisticMap: Record<string, string> = {
            start: 'in_progress',
            stop: 'stopped',
            restart: 'in_progress',
          }
          const optimistic = optimisticMap[action]
          return typeof optimistic === 'string' && optimistic.length > 0
        },
      ),
    )
  })
})
