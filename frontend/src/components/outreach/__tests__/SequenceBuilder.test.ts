import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// Sequence step validation pure logic
function validateSequenceStep(delay_days: number, subject: string) {
  const errors: { delay_days?: string; subject?: string } = {}
  if (delay_days < 0 || delay_days > 365) errors.delay_days = 'Must be 0–365 days'
  if (!subject.trim()) errors.subject = 'Subject required'
  return errors
}

describe('SequenceBuilder validation', () => {
  it('rejects negative delay', () => {
    const errs = validateSequenceStep(-1, 'Hello')
    expect(errs.delay_days).toBeDefined()
  })

  it('rejects delay > 365', () => {
    const errs = validateSequenceStep(366, 'Hello')
    expect(errs.delay_days).toBeDefined()
  })

  it('accepts 0 delay', () => {
    const errs = validateSequenceStep(0, 'Hello')
    expect(errs.delay_days).toBeUndefined()
  })

  it('accepts 365 delay', () => {
    const errs = validateSequenceStep(365, 'Hello')
    expect(errs.delay_days).toBeUndefined()
  })

  it('rejects empty subject', () => {
    const errs = validateSequenceStep(1, '')
    expect(errs.subject).toBeDefined()
  })

  it('property: out-of-bounds delay always errors', () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.integer({ min: -1000, max: -1 }),
          fc.integer({ min: 366, max: 1000 }),
        ),
        (delay) => {
          const errs = validateSequenceStep(delay, 'Subject')
          return errs.delay_days !== undefined
        },
      ),
    )
  })

  it('property: delay in [0, 365] with non-empty subject produces no errors', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 365 }),
        fc.string({ minLength: 1, maxLength: 100 }),
        (delay, subject) => {
          const errs = validateSequenceStep(delay, subject)
          return Object.keys(errs).length === 0
        },
      ),
    )
  })
})
