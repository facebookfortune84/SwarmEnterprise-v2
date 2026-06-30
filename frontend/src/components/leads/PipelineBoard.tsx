import React, { useState } from 'react'
import type { Lead } from '@/types/api'
import { LeadDetail } from './LeadDetail'

export interface PipelineBoardProps {
  leads: Lead[]
  onStatusChange: (leadId: string, newStatus: string) => void
}

const COLUMNS = [
  { key: 'NEW', label: 'New' },
  { key: 'CONTACTED', label: 'Contacted' },
  { key: 'QUALIFIED', label: 'Replied' },
  { key: 'COLD', label: 'Converted' },
  { key: 'COLD_REJECTED', label: 'Unsubscribed' },
] as const

type LeadStatus = typeof COLUMNS[number]['key']

export function PipelineBoard({ leads, onStatusChange }: PipelineBoardProps) {
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)

  const getLeadsByStatus = (status: LeadStatus) =>
    leads.filter(l => l.status === status)

  const handleDragStart = (e: React.DragEvent, leadId: string) => {
    e.dataTransfer.setData('leadId', leadId)
  }

  const handleDrop = (e: React.DragEvent, status: LeadStatus) => {
    e.preventDefault()
    const leadId = e.dataTransfer.getData('leadId')
    if (leadId) onStatusChange(leadId, status)
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
        {COLUMNS.map(col => {
          const colLeads = getLeadsByStatus(col.key)
          return (
            <div
              key={col.key}
              className="rounded-xl border border-neutral-700 bg-neutral-900 min-h-48"
              onDragOver={e => e.preventDefault()}
              onDrop={e => handleDrop(e, col.key)}
            >
              <div className="border-b border-neutral-700 px-3 py-2 flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
                  {col.label}
                </h3>
                <span className="text-xs text-neutral-600">{colLeads.length}</span>
              </div>
              <div className="p-2 space-y-2">
                {colLeads.map(lead => (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={e => handleDragStart(e, lead.id)}
                    onClick={() => setSelectedLead(lead)}
                    className="cursor-pointer rounded-lg border border-neutral-700 bg-neutral-800 p-2 hover:border-neutral-600 transition-colors"
                    role="button"
                    tabIndex={0}
                    aria-label={`Lead: ${lead.name ?? lead.email}`}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setSelectedLead(lead) }}
                  >
                    <p className="text-xs font-medium text-neutral-200 truncate">
                      {lead.name ?? lead.email ?? '—'}
                    </p>
                    {lead.company && (
                      <p className="text-xs text-neutral-500 truncate">{lead.company}</p>
                    )}
                  </div>
                ))}
                {colLeads.length === 0 && (
                  <p className="text-xs text-neutral-700 px-1 py-2">Drop leads here</p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {selectedLead && (
        <LeadDetail lead={selectedLead} onClose={() => setSelectedLead(null)} />
      )}
    </>
  )
}
