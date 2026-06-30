import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, DataTable, Skeleton } from '@/components/ui'
import { toast } from '@/components/ui/Toast'
import { ApiClient } from '@/services/ApiClient'
import { exportCsv } from '@/lib/csvExport'
import type { DailyMetric } from '@/types/api'
import type { ColumnDef } from '@/components/ui'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Title, Tooltip, Legend, Filler)

const RANGES = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
]

function daysAgo(n: number): Date {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d
}

export default function AnalyticsPage() {
  const [range, setRange] = useState(30)

  const start = daysAgo(range)
  const end = new Date()

  const { data: rawMetrics, isLoading } = useQuery({
    queryKey: ['analytics-metrics', range],
    queryFn: () => ApiClient.analytics.metrics(start.toISOString(), end.toISOString()),
  })

  const metrics: DailyMetric[] = (rawMetrics ?? []).filter((m) => {
    const d = new Date(m.date)
    return d >= start && d <= end
  })

  const labels = metrics.map((m) => m.date)

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#94a3b8' } },
      tooltip: { backgroundColor: '#0f172a', borderColor: '#334155', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8' },
    },
    scales: {
      x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(51,65,85,0.5)' } },
      y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(51,65,85,0.5)' } },
    },
  }

  const barData = {
    labels,
    datasets: [
      { label: 'Sent', data: metrics.map((m) => m.sent ?? 0), backgroundColor: 'rgba(96,165,250,0.7)' },
      { label: 'Opened', data: metrics.map((m) => m.opened ?? 0), backgroundColor: 'rgba(74,222,128,0.7)' },
      { label: 'Replied', data: metrics.map((m) => m.replied ?? 0), backgroundColor: 'rgba(251,191,36,0.7)' },
    ],
  }

  const lineData = {
    labels,
    datasets: [
      { label: 'Bounced', data: metrics.map((m) => m.bounced ?? 0), borderColor: '#f87171', backgroundColor: 'rgba(248,113,113,0.1)', fill: true, tension: 0.4 },
      { label: 'Clicked', data: metrics.map((m) => m.clicked ?? 0), borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.1)', fill: true, tension: 0.4 },
    ],
  }

  const columns: ColumnDef<DailyMetric>[] = [
    { key: 'date', header: 'Date', sortable: true },
    { key: 'sent', header: 'Sent', sortable: true },
    { key: 'opened', header: 'Opened', sortable: true },
    { key: 'clicked', header: 'Clicked', sortable: true },
    { key: 'replied', header: 'Replied', sortable: true },
    { key: 'bounced', header: 'Bounced', sortable: true },
    {
      key: 'open_rate',
      header: 'Open Rate',
      render: (row) => {
        const rate = (row.sent ?? 0) > 0 ? (((row.opened ?? 0) / (row.sent ?? 0)) * 100).toFixed(1) : '0.0'
        return `${rate}%`
      },
    },
  ]

  const handleExport = () => {
    exportCsv(metrics as unknown as Record<string, unknown>[], `analytics-${range}d.csv`)
    toast.success('CSV exported')
  }

  return (
    <AppLayout title="Analytics">
      <PageHeader
        title="Analytics"
        subtitle="Outreach performance metrics"
        actions={
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-neutral-700 overflow-hidden">
              {RANGES.map((r) => (
                <button
                  key={r.days}
                  onClick={() => setRange(r.days)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    range === r.days ? 'bg-brand-700 text-white' : 'text-neutral-400 hover:bg-neutral-800'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <Button variant="ghost" size="sm" onClick={handleExport}>
              ↓ Export CSV
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <div className="mt-6 space-y-4">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            {(['sent', 'opened', 'clicked', 'replied', 'bounced'] as const).map((key) => {
              const total = metrics.reduce((sum, m) => sum + (m[key] ?? 0), 0)
              return (
                <div key={key} className="rounded-xl border border-neutral-700 bg-neutral-900 p-4">
                  <p className="text-xs text-neutral-500 capitalize">{key}</p>
                  <p className="text-2xl font-bold text-neutral-100 mt-1 tabular-nums">{total.toLocaleString()}</p>
                </div>
              )
            })}
          </div>

          {/* Bar chart */}
          <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4">
            <h3 className="text-sm font-semibold text-neutral-200 mb-4">Volume by Day</h3>
            <div style={{ height: '240px' }}>
              <Bar data={barData} options={chartOptions} />
            </div>
          </div>

          {/* Line chart */}
          <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-4">
            <h3 className="text-sm font-semibold text-neutral-200 mb-4">Click & Bounce Rates</h3>
            <div style={{ height: '200px' }}>
              <Line data={lineData} options={chartOptions} />
            </div>
          </div>

          {/* Table */}
          <DataTable
            columns={columns}
            data={metrics}
            keyExtractor={(row) => row.date}
            emptyMessage="No data for this period."
          />
        </div>
      )}
    </AppLayout>
  )
}
