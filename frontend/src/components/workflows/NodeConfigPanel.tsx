import { useState, useEffect } from 'react'
import { Input, Select } from '@/components/ui'
import type { WorkflowNode } from '@/types/api'

export interface NodeConfigPanelProps {
  node: WorkflowNode | null
  onChange: (nodeId: string, config: Record<string, unknown>) => void
}

const TRIGGER_EVENTS = [
  { value: 'lead_created', label: 'Lead Created' },
  { value: 'email_opened', label: 'Email Opened' },
  { value: 'email_replied', label: 'Email Replied' },
  { value: 'form_submitted', label: 'Form Submitted' },
]

const ACTION_TYPES = [
  { value: 'send_email', label: 'Send Email' },
  { value: 'enroll_sequence', label: 'Enroll in Sequence' },
  { value: 'update_lead', label: 'Update Lead Status' },
  { value: 'notify_slack', label: 'Notify Slack' },
]

const OPERATORS = [
  { value: 'eq', label: 'equals' },
  { value: 'ne', label: 'not equals' },
  { value: 'gt', label: 'greater than' },
  { value: 'lt', label: 'less than' },
  { value: 'contains', label: 'contains' },
]

export function NodeConfigPanel({ node, onChange }: NodeConfigPanelProps) {
  const [config, setConfig] = useState<Record<string, unknown>>({})

  useEffect(() => {
    setConfig({})
  }, [node?.id])

  if (!node) {
    return (
      <div className="w-72 rounded-xl border border-neutral-700 bg-neutral-900 p-4 flex items-center justify-center h-40 shrink-0">
        <p className="text-sm text-neutral-600 text-center">Select a node to configure it</p>
      </div>
    )
  }

  const update = (key: string, value: unknown) => {
    const next = { ...config, [key]: value }
    setConfig(next)
    onChange(node.id, next)
  }

  return (
    <div className="w-72 rounded-xl border border-neutral-700 bg-neutral-900 p-4 shrink-0 overflow-y-auto">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-neutral-200">Configure Node</h3>
        <p className="text-xs text-neutral-500 mt-0.5 font-mono">
          [{node.type}] {node.label}
        </p>
      </div>

      <div className="space-y-3">
        {node.type === 'trigger' && (
          <Select
            label="Event"
            options={TRIGGER_EVENTS}
            value={String(config.event ?? '')}
            onChange={e => update('event', e.target.value)}
          />
        )}

        {node.type === 'condition' && (
          <>
            <Input
              label="Field"
              value={String(config.field ?? '')}
              onChange={e => update('field', e.target.value)}
              placeholder="lead.intent_score"
            />
            <Select
              label="Operator"
              options={OPERATORS}
              value={String(config.operator ?? 'eq')}
              onChange={e => update('operator', e.target.value)}
            />
            <Input
              label="Value"
              value={String(config.value ?? '')}
              onChange={e => update('value', e.target.value)}
              placeholder="70"
            />
          </>
        )}

        {node.type === 'action' && (
          <>
            <Select
              label="Action Type"
              options={ACTION_TYPES}
              value={String(config.action_type ?? '')}
              onChange={e => update('action_type', e.target.value)}
            />
            <Input
              label="Parameters (JSON)"
              value={String(config.parameters ?? '')}
              onChange={e => update('parameters', e.target.value)}
              placeholder='{"key": "value"}'
            />
          </>
        )}

        {node.type === 'delay' && (
          <Input
            label="Delay (days)"
            type="number"
            value={String(config.delay_days ?? 1)}
            onChange={e => update('delay_days', Number(e.target.value))}
            min="0"
            max="365"
          />
        )}
      </div>
    </div>
  )
}
