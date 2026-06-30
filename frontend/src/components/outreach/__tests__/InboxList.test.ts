import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import type { InboxReply } from '@/types/api'

// Pure sort logic tests
describe('InboxList sort: interested always at top', () => {
  function makeReply(id: string, sentiment: string | undefined, received_at: string): InboxReply {
    return { id, mailbox: 'default', uid: id, received_at, sentiment: sentiment as InboxReply['sentiment'] }
  }

  function sortReplies(replies: InboxReply[]): InboxReply[] {
    return [...replies].sort((a, b) => {
      if (a.sentiment === 'interested' && b.sentiment !== 'interested') return -1
      if (b.sentiment === 'interested' && a.sentiment !== 'interested') return 1
      return new Date(b.received_at).getTime() - new Date(a.received_at).getTime()
    })
  }

  it('puts interested replies before others', () => {
    const replies = [
      makeReply('1', 'not_interested', '2024-01-03T00:00:00Z'),
      makeReply('2', 'interested', '2024-01-01T00:00:00Z'),
      makeReply('3', 'neutral', '2024-01-02T00:00:00Z'),
    ]
    const sorted = sortReplies(replies)
    expect(sorted[0].sentiment).toBe('interested')
  })

  it('property: interested replies always precede non-interested', () => {
    const sentiments: InboxReply['sentiment'][] = ['interested', 'not_interested', 'neutral', 'out_of_office', 'unsubscribe']
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.uuid(),
            sentiment: fc.constantFrom(...sentiments),
          }),
          { minLength: 0, maxLength: 20 },
        ),
        (items) => {
          const replies = items.map((item) =>
            makeReply(item.id, item.sentiment, new Date().toISOString()),
          )
          const sorted = sortReplies(replies)
          let seenNonInterested = false
          for (const r of sorted) {
            if (r.sentiment !== 'interested') seenNonInterested = true
            if (seenNonInterested && r.sentiment === 'interested') return false
          }
          return true
        },
      ),
    )
  })
})
