import { Badge } from '@/components/ui'
import type { AgentEvent } from '@/types/api'
import type { AgentFeedStatus } from '@/hooks/useAgentFeed'

interface AgentFeedProps {
  events: AgentEvent[]
  status: AgentFeedStatus
  className?: string
  maxEvents?: number
}

type BadgeVariant = 'info' | 'warning' | 'danger' | 'success' | 'neutral'

const eventTypeColor: Record<string, BadgeVariant> = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  error: 'danger',
  build: 'neutral',
  deploy: 'info',
}

function StatusDot({ status }: { status: AgentFeedStatus }) {
  const colorClass =
    status === 'connected'
      ? 'bg-green-400'
      : status === 'reconnecting'
        ? 'bg-yellow-400 animate-pulse'
        : status === 'lost'
          ? 'bg-red-500'
          : 'bg-neutral-500'
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full shrink-0 ${colorClass}`}
      aria-label={`Feed status: ${status}`}
    />
  )
}

export function AgentFeed({ events, status, className = '', maxEvents = 50 }: AgentFeedProps) {
  const displayed = events.slice(0, maxEvents)
  return (
    <div className={`flex flex-col rounded-xl border border-neutral-700 bg-neutral-900 ${className}`}>
      <div className="flex items-center justify-between border-b border-neutral-700 px-4 py-3">
        <h3 className="text-sm font-semibold text-neutral-200">Agent Feed</h3>
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <StatusDot status={status} />
          <span className="capitalize">{status}</span>
        </div>
      </div>

      <div
        className="flex flex-col overflow-y-auto"
        style={{ maxHeight: '360px' }}
        aria-live="polite"
        aria-label="Agent event feed"
      >
        {displayed.length === 0 ? (
          <div className="py-12 text-center text-sm text-neutral-600">
            No events yet.
          </div>
        ) : (
          displayed.map((event, i) => (
            <div
              key={event.id ?? i}
              className="flex items-start gap-3 border-b border-neutral-800 px-4 py-3 last:border-0"
            >
              <Badge color={eventTypeColor[event.type ?? 'info'] ?? 'neutral'}>
                {event.type ?? 'info'}
              </Badge>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-neutral-200 break-words">{event.message}</p>
                {event.agent && (
                  <p className="text-xs text-neutral-500 mt-0.5">by {event.agent}</p>
                )}
              </div>
              <time className="text-xs text-neutral-600 shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </time>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
