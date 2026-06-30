import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'

// Campaign validation pure logic
function validateCampaign(recipients: string[], subject: string, body: string) {
  const errors: string[] = []
  const valid = recipients.filter((r) => r.trim() && r.includes('@'))
  if (valid.length === 0) errors.push('At least one valid recipient required')
  if (!subject.trim()) errors.push('Subject is required')
  if (!body.trim()) errors.push('Body is required')
  return errors
}

describe('CampaignComposer validation', () => {
  it('rejects empty recipients', () => {
    const errs = validateCampaign([], 'Subject', 'Body')
    expect(errs).toContain('At least one valid recipient required')
  })

  it('rejects invalid email', () => {
    const errs = validateCampaign(['notanemail'], 'Subject', 'Body')
    expect(errs).toContain('At least one valid recipient required')
  })

  it('rejects empty subject', () => {
    const errs = validateCampaign(['a@b.com'], '', 'Body')
    expect(errs).toContain('Subject is required')
  })

  it('rejects empty body', () => {
    const errs = validateCampaign(['a@b.com'], 'Subject', '')
    expect(errs).toContain('Body is required')
  })

  it('accepts valid input', () => {
    const errs = validateCampaign(['a@b.com', 'c@d.com'], 'Hello', 'World')
    expect(errs).toHaveLength(0)
  })

  it('property: valid emails with non-empty subject and body produce no errors', () => {
    fc.assert(
      fc.property(
        fc.array(fc.emailAddress(), { minLength: 1, maxLength: 10 }),
        // Use strings that are non-empty AND non-whitespace
        fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0),
        fc.string({ minLength: 1, maxLength: 200 }).filter(s => s.trim().length > 0),
        (recipients, subject, body) => {
          const errs = validateCampaign(recipients, subject, body)
          return errs.length === 0
        },
      ),
      { numRuns: 100 },
    )
  })

  it('property: empty subject always produces error', () => {
    fc.assert(
      fc.property(
        fc.array(fc.emailAddress(), { minLength: 1 }),
        fc.string({ minLength: 1 }),
        (recipients, body) => {
          const errs = validateCampaign(recipients, '', body)
          return errs.includes('Subject is required')
        },
      ),
    )
  })
})
