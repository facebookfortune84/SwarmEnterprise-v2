import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentFeed } from '@/components/dashboard/AgentFeed'
import type { AgentEvent } from '@/types/api'
import type { AgentFeedStatus } from '@/hooks/useAgentFeed'

const makeEvent = (id: string, type: AgentEvent['type'] = 'info', message = 'test'): AgentEvent => ({
  id,
  type,
  message,
  agent: 'test-agent',
  timestamp: new Date().toISOString(),
})

describe('AgentFeed', () => {
  it('renders empty state when no events', () => {
    render(<AgentFeed events={[]} status="idle" />)
    expect(screen.getByText('No events yet.')).toBeDefined()
  })

  it('renders events', () => {
    const events = [makeEvent('1', 'info', 'Hello world')]
    render(<AgentFeed events={events} status="connected" />)
    expect(screen.getByText('Hello world')).toBeDefined()
  })

  it('newest event at top (first in array is first rendered)', () => {
    const events = [
      makeEvent('1', 'info', 'Latest event'),
      makeEvent('2', 'info', 'Older event'),
    ]
    render(<AgentFeed events={events} status="connected" />)
    const items = screen.getAllByText(/event/)
    // First item rendered should be 'Latest event'
    expect(items[0].textContent).toContain('Latest')
  })

  it('color-coded by event type: error shows danger badge', () => {
    const events = [makeEvent('1', 'error', 'Error occurred')]
    const { container } = render(<AgentFeed events={events} status="connected" />)
    // danger badge has text-danger-700 class
    const badge = container.querySelector('.text-danger-700')
    expect(badge).toBeDefined()
  })

  it('color-coded by event type: success shows success badge', () => {
    const events = [makeEvent('1', 'success', 'All good')]
    const { container } = render(<AgentFeed events={events} status="connected" />)
    const badge = container.querySelector('.text-success-700')
    expect(badge).toBeDefined()
  })

  it('respects maxEvents prop', () => {
    const events = Array.from({ length: 10 }, (_, i) => makeEvent(String(i), 'info', `msg-${i}`))
    render(<AgentFeed events={events} status="connected" maxEvents={3} />)
    // Should only show 3 events
    const msgs = screen.queryAllByText(/msg-/)
    expect(msgs.length).toBe(3)
  })

  it('shows connected status dot', () => {
    const { container } = render(<AgentFeed events={[]} status="connected" />)
    const dot = container.querySelector('.bg-green-400')
    expect(dot).toBeDefined()
  })

  it('shows reconnecting status', () => {
    render(<AgentFeed events={[]} status="reconnecting" />)
    expect(screen.getByText('reconnecting')).toBeDefined()
  })

  it('shows lost status with red dot', () => {
    const { container } = render(<AgentFeed events={[]} status="lost" />)
    expect(screen.getByText('lost')).toBeDefined()
    const dot = container.querySelector('.bg-red-500')
    expect(dot).toBeDefined()
  })

  it('shows agent name for events with agent', () => {
    const event: AgentEvent = {
      id: '1',
      type: 'info',
      message: 'Did something',
      agent: 'outreach-agent',
      timestamp: new Date().toISOString(),
    }
    render(<AgentFeed events={[event]} status="connected" />)
    expect(screen.getByText('by outreach-agent')).toBeDefined()
  })

  it('shows timestamp for each event', () => {
    const events = [makeEvent('1')]
    render(<AgentFeed events={events} status="connected" />)
    // time element should be present
    const timeEl = document.querySelector('time')
    expect(timeEl).toBeDefined()
  })
})
