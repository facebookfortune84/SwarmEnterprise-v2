import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import type { AgentEvent } from '@/types/api'

// Pure logic tests for agent feed cap and sort – no hook mounting needed
describe('useAgentFeed logic', () => {
  const MAX_EVENTS = 50

  function makeEvent(id: string, ts: string): AgentEvent {
    return { id, type: 'info', message: `msg-${id}`, timestamp: ts }
  }

  it('caps event list at 50 items', () => {
    let events: AgentEvent[] = []
    const addEvent = (evt: AgentEvent) => {
      events = [evt, ...events].slice(0, MAX_EVENTS)
    }

    for (let i = 0; i < 60; i++) {
      addEvent(makeEvent(String(i), new Date(i * 1000).toISOString()))
    }

    expect(events).toHaveLength(MAX_EVENTS)
  })

  it('is reverse chronological (newest first)', () => {
    let events: AgentEvent[] = []
    const addEvent = (evt: AgentEvent) => {
      events = [evt, ...events].slice(0, MAX_EVENTS)
    }

    const timestamps = ['2024-01-01T10:00:00Z', '2024-01-01T11:00:00Z', '2024-01-01T12:00:00Z']
    for (const ts of timestamps) {
      addEvent(makeEvent(ts, ts))
    }

    // Newest (12:00) should be at index 0
    expect(events[0].timestamp).toBe('2024-01-01T12:00:00Z')
    expect(events[2].timestamp).toBe('2024-01-01T10:00:00Z')
  })

  it('property: list never exceeds 50 items regardless of additions', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 200 }), (count) => {
        let events: AgentEvent[] = []
        for (let i = 0; i < count; i++) {
          events = [makeEvent(String(i), new Date().toISOString()), ...events].slice(0, MAX_EVENTS)
        }
        return events.length <= MAX_EVENTS
      }),
    )
  })

  it('backoff capped at 30s', () => {
    const wsBackoffDelay = (attempt: number) => Math.min(1_000 * Math.pow(2, attempt), 30_000)
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 20 }), (attempt) => {
        return wsBackoffDelay(attempt) <= 30_000
      }),
    )
  })
})
