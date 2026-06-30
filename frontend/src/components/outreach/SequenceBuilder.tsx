import { useState } from 'react'
import { Button, Input, Textarea, Badge } from '@/components/ui'
import type { Sequence } from '@/types/api'

interface StepDraft {
  delay_days: number
  subject: string
  body: string
}

export interface SequenceBuilderProps {
  initial?: Partial<Sequence>
  onSave?: (sequence: { name: string; steps: StepDraft[] }) => Promise<void>
}

const EMPTY_STEP: StepDraft = { delay_days: 1, subject: '', body: '' }

export function SequenceBuilder({ initial, onSave }: SequenceBuilderProps) {
  const [name, setName] = useState(initial?.name ?? '')
  const [steps, setSteps] = useState<StepDraft[]>([{ ...EMPTY_STEP }])
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<number, { subject?: string }>>({})

  const addStep = () => setSteps(prev => [...prev, { ...EMPTY_STEP }])

  const removeStep = (idx: number) =>
    setSteps(prev => prev.filter((_, i) => i !== idx))

  const updateStep = (idx: number, field: keyof StepDraft, value: string | number) =>
    setSteps(prev => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)))

  const validate = () => {
    const errs: typeof errors = {}
    steps.forEach((s, i) => {
      if (!s.subject.trim()) errs[i] = { subject: 'Subject required' }
    })
    return errs
  }

  const handleSave = async () => {
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setErrors({})
    if (!onSave) return
    setSaving(true)
    try {
      await onSave({ name, steps })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-6 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-base font-semibold text-neutral-200">Sequence Builder</h2>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={addStep}>+ Add Step</Button>
          <Button size="sm" loading={saving} onClick={() => void handleSave()}>Save</Button>
        </div>
      </div>

      <div className="mb-4">
        <Input
          label="Sequence Name"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="My Outreach Sequence"
        />
      </div>

      <div className="space-y-4">
        {steps.map((step, idx) => (
          <div key={idx} className="rounded-lg border border-neutral-700 bg-neutral-800 p-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant="neutral" size="md">Step {idx + 1}</Badge>
              {steps.length > 1 && (
                <Button size="sm" variant="ghost" onClick={() => removeStep(idx)}>Remove</Button>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Delay (days)"
                type="number"
                value={String(step.delay_days)}
                onChange={e => updateStep(idx, 'delay_days', Number(e.target.value))}
                min="0"
                max="365"
              />
            </div>
            <div className="mt-3">
              <Input
                label="Subject"
                value={step.subject}
                onChange={e => updateStep(idx, 'subject', e.target.value)}
                error={errors[idx]?.subject}
                placeholder="Follow-up: {{company}}"
              />
            </div>
            <div className="mt-3">
              <Textarea
                label="Body"
                value={step.body}
                onChange={e => updateStep(idx, 'body', e.target.value)}
                rows={3}
                placeholder="Hi {{first_name}}, just following up…"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
