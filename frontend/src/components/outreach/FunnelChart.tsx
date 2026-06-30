import { Skeleton } from '@/components/ui'

export interface FunnelChartProps {
  data?: { sent: number; opened: number; replied: number; converted: number }
  loading?: boolean
  isLoading?: boolean
}

export function FunnelChart({ data, loading, isLoading }: FunnelChartProps) {
  const showLoading = loading ?? isLoading ?? false

  if (showLoading) {
    return <Skeleton className="h-64 w-full rounded-xl" />
  }

  const stages = data
    ? [
        { label: 'Sent', value: data.sent, color: '#60a5fa' },
        { label: 'Opened', value: data.opened, color: '#4ade80' },
        { label: 'Replied', value: data.replied, color: '#fbbf24' },
        { label: 'Converted', value: data.converted, color: '#a78bfa' },
      ]
    : []

  const maxVal = Math.max(...stages.map(s => s.value), 1)

  return (
    <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-6">
      <h3 className="text-sm font-semibold text-neutral-200 mb-4">Outreach Funnel</h3>
      {stages.length === 0 ? (
        <div className="py-12 text-center text-sm text-neutral-600">No funnel data yet</div>
      ) : (
        <div className="space-y-3">
          {stages.map((stage, i) => {
            const pct = ((stage.value / maxVal) * 100).toFixed(0)
            const convRate =
              i > 0 && stages[i - 1].value > 0
                ? ((stage.value / stages[i - 1].value) * 100).toFixed(1)
                : null
            return (
              <div key={stage.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-neutral-400">{stage.label}</span>
                  <div className="flex items-center gap-2 text-xs text-neutral-400">
                    <span className="tabular-nums">{stage.value.toLocaleString()}</span>
                    {convRate !== null && (
                      <span className="text-neutral-600">({convRate}% of prev)</span>
                    )}
                  </div>
                </div>
                <div className="h-6 rounded bg-neutral-800 overflow-hidden">
                  <div
                    className="h-full rounded transition-all"
                    style={{ width: `${pct}%`, backgroundColor: stage.color, opacity: 0.85 }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
