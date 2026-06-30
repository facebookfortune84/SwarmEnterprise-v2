import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button, Input, Textarea, Select } from '@/components/ui'
import { toast } from 'react-hot-toast'
import ApiClient from '@/services/ApiClient'
import type { Sequence } from '@/types/api'
import { renderTemplate } from '@/lib/mergeFields'

export interface CampaignComposerProps {
  onEnroll?: (sequenceId: string, leadIds: string[]) => Promise<void>
  sequences?: Sequence[]
}

export function CampaignComposer({ onEnroll, sequences }: CampaignComposerProps) {
  const [selectedSequenceId, setSelectedSequenceId] = useState('')
  const [recipients, setRecipients] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [fromName, setFromName] = useState('SwarmOS')
  const [errors, setErrors] = useState<{ recipients?: string; subject?: string; body?: string; sequence?: string }>({})

  const preview = renderTemplate(body, {
    first_name: 'Jane',
    last_name: 'Smith',
    company: 'Acme Corp',
    website: 'https://acme.com',
  })

  const sendMut = useMutation({
    mutationFn: () => {
      const recipientList = recipients
        .split(/[\n,]+/)
        .map((r) => r.trim())
        .filter((r) => r.includes('@'))
      return ApiClient.outreach.campaign({
        recipients: recipientList,
        subject: subject.trim(),
        body: body.trim(),
        from_name: fromName.trim(),
      })
    },
    onSuccess: (data) => {
      toast.success(`Campaign queued for ${(data as { queued: number }).queued} recipients`)
      setRecipients('')
      setSubject('')
      setBody('')
    },
    onError: () => { toast.error('Failed to send campaign') },
  })

  const validate = () => {
    const errs: typeof errors = {}
    const list = recipients.split(/[\n,]+/).map((r) => r.trim()).filter(Boolean)
    if (list.length === 0) errs.recipients = 'At least one valid recipient is required'
    else if (list.some((r) => !r.includes('@'))) errs.recipients = 'Some emails appear invalid'
    if (!subject.trim()) errs.subject = 'Subject is required'
    if (!body.trim()) errs.body = 'Body is required'
    return errs
  }

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setErrors({})
    sendMut.mutate()
  }

  const handleEnroll = async () => {
    if (!selectedSequenceId) { setErrors(e => ({ ...e, sequence: 'Select a sequence' })); return }
    if (!onEnroll) return
    const leadIds = recipients
      .split(/[\n,]+/)
      .map(r => r.trim())
      .filter(r => r.length > 0)
    await onEnroll(selectedSequenceId, leadIds)
  }

  const sequenceOptions = [
    { value: '', label: 'Select a sequence…' },
    ...(sequences ?? []).map(s => ({ value: s.id, label: s.name })),
  ]

  return (
    <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-6 max-w-2xl">
      <h2 className="text-base font-semibold text-neutral-200 mb-4">Campaign Composer</h2>

      {/* Sequence enroll section */}
      {sequences && (
        <div className="mb-6 p-4 rounded-lg border border-neutral-800 bg-neutral-800/40">
          <h3 className="text-sm font-medium text-neutral-300 mb-3">Enroll in Sequence</h3>
          <Select
            label="Sequence"
            options={sequenceOptions}
            value={selectedSequenceId}
            onChange={e => setSelectedSequenceId(e.target.value)}
            error={errors.sequence}
          />
          <Button
            className="mt-3"
            size="sm"
            variant="secondary"
            onClick={() => void handleEnroll()}
            disabled={!selectedSequenceId}
          >
            Enroll Selected Leads
          </Button>
        </div>
      )}

      <form onSubmit={handleSend} className="space-y-4">
        <Textarea
          label="Recipients"
          value={recipients}
          onChange={(e) => setRecipients(e.target.value)}
          error={errors.recipients}
          rows={4}
          placeholder="jane@example.com, bob@example.com"
        />
        <Input label="From Name" value={fromName} onChange={(e) => setFromName(e.target.value)} />
        <Input label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} error={errors.subject} />
        <Textarea
          label="Body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          error={errors.body}
          rows={6}
          maxLength={5000}
          showCharCount
          placeholder="Hi {{first_name}}, I wanted to reach out about…"
        />
        {body && (
          <div className="mt-2 rounded-md border border-neutral-700 bg-neutral-800 p-3">
            <p className="text-xs text-neutral-500 mb-1">Preview:</p>
            <p className="text-sm text-neutral-300 whitespace-pre-wrap">{preview}</p>
          </div>
        )}
        <div className="flex gap-3">
          <Button type="submit" loading={sendMut.isPending} disabled={!subject.trim()}>
            Send Campaign
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => { setRecipients(''); setSubject(''); setBody('') }}
          >
            Clear
          </Button>
        </div>
      </form>
    </div>
  )
}
