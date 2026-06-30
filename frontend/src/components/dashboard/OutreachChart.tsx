import { Skeleton } from '@/components/ui'
import type { DailyMetric } from '@/types/api'

interface OutreachChartProps {
  data?: Array<{ date: string; sent: number; opened: number; replied: number; bounced: number }>
  metrics?: DailyMetric[]
  loading?: boolean
  isLoading?: boolean
}

export function OutreachChart({ data, metrics, loading, isLoading }: OutreachChartProps) {
  const showLoading = loading ?? isLoading ?? false

  // Normalize data from either prop
  const chartData = data ?? (metrics ?? []).map(m => ({
    date: m.date,
    sent: m.sent ?? 0,
    opened: m.opened ?? 0,
    replied: m.replied ?? 0,
    bounced: m.bounced ?? 0,
  }))

  if (showLoading) {
    return <Skeleton className="h-64 w-full rounded-xl" />
  }

  if (chartData.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4 flex items-center justify-center h-64">
        <p className="text-neutral-600 text-sm">No outreach data yet</p>
      </div>
    )
  }

  const maxVal = Math.max(...chartData.flatMap(d => [d.sent, d.opened, d.replied, d.bounced]), 1)
  const svgHeight = 180
  const svgWidth = 600
  const padLeft = 40
  const padBottom = 30
  const plotW = svgWidth - padLeft - 10
  const plotH = svgHeight - padBottom

  const xs = chartData.map((_, i) => padLeft + (i / Math.max(chartData.length - 1, 1)) * plotW)
  const ys = (key: keyof typeof chartData[0]) =>
    chartData.map(d => plotH - (Number(d[key]) / maxVal) * plotH)

  const toPath = (yVals: number[]) =>
    xs
      .map((x, i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${(yVals[i] ?? 0).toFixed(1)}`)
      .join(' ')

  const series = [
    { key: 'sent' as const, color: '#60a5fa', label: 'Sent' },
    { key: 'opened' as const, color: '#4ade80', label: 'Opened' },
    { key: 'replied' as const, color: '#fbbf24', label: 'Replied' },
    { key: 'bounced' as const, color: '#f87171', label: 'Bounced' },
  ]

  return (
    <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4">
      <h3 className="text-sm font-semibold text-neutral-200 mb-4">Outreach Overview</h3>
      <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full" role="img" aria-label="Outreach chart">
        {/* Y-axis labels */}
        {[0, 0.5, 1].map((frac) => {
          const y = plotH - frac * plotH
          return (
            <g key={frac}>
              <line x1={padLeft} y1={y} x2={svgWidth - 10} y2={y} stroke="#374151" strokeWidth="0.5" />
              <text x={padLeft - 4} y={y + 4} textAnchor="end" fill="#6b7280" fontSize="10">
                {Math.round(frac * maxVal)}
              </text>
            </g>
          )
        })}
        {/* X-axis date labels (every nth) */}
        {chartData.map((d, i) => {
          if (i % Math.ceil(chartData.length / 6) !== 0) return null
          return (
            <text key={i} x={xs[i]} y={svgHeight - 4} textAnchor="middle" fill="#6b7280" fontSize="9">
              {d.date.slice(5)}
            </text>
          )
        })}
        {/* Lines */}
        {series.map(s => (
          <path
            key={s.key}
            d={toPath(ys(s.key))}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinejoin="round"
          />
        ))}
      </svg>
      {/* Legend */}
      <div className="flex gap-4 mt-2 flex-wrap">
        {series.map(s => (
          <div key={s.key} className="flex items-center gap-1.5 text-xs text-neutral-400">
            <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: s.color }} />
            {s.label}
          </div>
        ))}
      </div>
    </div>
  )
}
