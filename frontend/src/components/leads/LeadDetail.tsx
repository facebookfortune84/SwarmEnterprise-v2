import { Badge } from '@/components/ui'
import type { Lead, TimelineEntry } from '@/types/api'
import { useQuery } from '@tanstack/react-query'
import ApiClient from '@/services/ApiClient'

export interface LeadDetailProps {
  lead: Lead
  onClose: () => void
}

export function LeadDetail({ lead, onClose }: LeadDetailProps) {
  const { data: timeline, isLoading: timelineLoading } = useQuery({
    queryKey: ['lead-timeline', lead.id],
    queryFn: () => ApiClient.leads.timeline(lead.id),
  })

  const intentBadge = (score?: number) => {
    if (score === undefined) return 'neutral' as const
    if (score >= 70) return 'success' as const
    if (score >= 40) return 'warning' as const
    return 'danger' as const
  }

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 w-96 bg-neutral-900 border-l border-neutral-700 shadow-2xl flex flex-col"
      role="dialog"
      aria-label="Lead detail"
      aria-modal="true"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-800">
        <h2 className="text-base font-semibold text-neutral-100">
          {lead.name ?? lead.email ?? 'Lead Detail'}
        </h2>
        <button
          onClick={onClose}
          aria-label="Close panel"
          className="text-neutral-400 hover:text-neutral-200 text-xl"
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {/* Basic info */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-neutral-500 text-xs">Email</p>
            <p className="text-neutral-200 mt-0.5">{lead.email ?? '—'}</p>
          </div>
          <div>
            <p className="text-neutral-500 text-xs">Company</p>
            <p className="text-neutral-200 mt-0.5">{lead.company ?? '—'}</p>
          </div>
          <div>
            <p className="text-neutral-500 text-xs">Website</p>
            <p className="text-neutral-200 mt-0.5 break-all">{lead.website ?? '—'}</p>
          </div>
          <div>
            <p className="text-neutral-500 text-xs">LinkedIn</p>
            {lead.linkedin_url ? (
              <a
                href={lead.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:underline text-xs mt-0.5 block truncate"
              >
                {lead.linkedin_url}
              </a>
            ) : (
              <p className="text-neutral-200 mt-0.5">—</p>
            )}
          </div>
          <div>
            <p className="text-neutral-500 text-xs">Status</p>
            <Badge color="neutral" size="sm" className="mt-0.5">{lead.status}</Badge>
          </div>
          <div>
            <p className="text-neutral-500 text-xs">Intent Score</p>
            <Badge color={intentBadge(lead.intent_score)} size="sm" className="mt-0.5">
              {lead.intent_score ?? '—'}
            </Badge>
          </div>
        </div>

        {/* Flags */}
        <div className="flex gap-2 flex-wrap">
          {lead.needs_review && <Badge color="warning" size="sm">Needs Review</Badge>}
          {lead.email_invalid && <Badge color="danger" size="sm">Invalid Email</Badge>}
        </div>

        {/* Timeline */}
        <div>
          <h3 className="text-sm font-semibold text-neutral-300 mb-2">Timeline</h3>
          {timelineLoading ? (
            <p className="text-xs text-neutral-500">Loading...</p>
          ) : !timeline || timeline.length === 0 ? (
            <p className="text-xs text-neutral-500">No timeline entries.</p>
          ) : (
            <div className="space-y-2">
              {(timeline as TimelineEntry[]).map((entry, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full bg-brand-500 mt-1 shrink-0" />
                  <div>
                    <p className="text-neutral-300">
                      {entry.from_status ?? 'Initial'} → {entry.to_status}
                    </p>
                    <p className="text-neutral-500">
                      {entry.triggered_by} · {new Date(entry.occurred_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
