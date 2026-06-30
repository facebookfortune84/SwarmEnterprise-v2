import { Badge, Skeleton } from '@/components/ui'

type Classification = 'interested' | 'not_interested' | 'auto_reply' | 'bounce' | 'neutral'

const classificationColor = (c?: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' => {
  if (c === 'interested') return 'success'
  if (c === 'not_interested' || c === 'bounce') return 'danger'
  if (c === 'auto_reply' || c === 'unsubscribe') return 'warning'
  return 'neutral'
}

const GROUP_ORDER: Classification[] = ['interested', 'not_interested', 'auto_reply', 'bounce', 'neutral']
const GROUP_LABELS: Record<string, string> = {
  interested: 'Interested',
  not_interested: 'Not Interested',
  auto_reply: 'Auto Reply',
  bounce: 'Bounce',
  neutral: 'Neutral',
}

export interface InboxListProps {
  items?: Array<{ uid: string; from?: string; subject?: string; classification?: string; received_at: string }>
  loading?: boolean
}

export function InboxList({ items = [], loading }: InboxListProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
      </div>
    )
  }

  const grouped = GROUP_ORDER.reduce<Record<string, typeof items>>((acc, key) => {
    acc[key] = items.filter(
      item => (item.classification ?? 'neutral') === key
    )
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {GROUP_ORDER.map(group => {
        const groupItems = grouped[group] ?? []
        return (
          <div key={group}>
            <div className="flex items-center gap-2 mb-2">
              <Badge color={classificationColor(group)} size="sm">
                {GROUP_LABELS[group]}
              </Badge>
              <span className="text-xs text-neutral-500">{groupItems.length} items</span>
            </div>
            {groupItems.length === 0 ? (
              <p className="text-xs text-neutral-600 px-2">No messages</p>
            ) : (
              <div className="space-y-2">
                {groupItems.map(item => (
                  <div
                    key={item.uid}
                    className="rounded-lg border border-neutral-700 bg-neutral-900 p-3"
                    role="row"
                    aria-label={`Inbox item: ${item.subject ?? 'No subject'}`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-neutral-200 truncate">
                          {item.from ?? '—'}
                        </p>
                        <p className="text-xs text-neutral-400 mt-0.5 truncate">
                          {item.subject ?? '(No subject)'}
                        </p>
                      </div>
                      <time className="text-xs text-neutral-600 shrink-0">
                        {new Date(item.received_at).toLocaleDateString()}
                      </time>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
