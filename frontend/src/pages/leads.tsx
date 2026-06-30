import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Badge, DataTable, Skeleton } from '@/components/ui'
import { ApiClient } from '@/services/ApiClient'
import type { Lead } from '@/types/api'
import type { ColumnDef } from '@/components/ui'

const statusColor = (s: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' => {
  if (s === 'CONVERTED') return 'success'
  if (s === 'QUALIFIED') return 'info'
  if (s === 'CONTACTED') return 'warning'
  if (s === 'DISQUALIFIED') return 'danger'
  return 'neutral'
}

export default function LeadsPage() {
  const [view, setView] = useState<'table' | 'pipeline'>('table')
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data, isLoading } = useQuery({
    queryKey: ['leads'],
    queryFn: () => ApiClient.leads.list(),
  })
  const leads = data ?? []

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => setSelected(new Set(leads.map((l) => l.id)))
  const clearAll = () => setSelected(new Set())

  const PIPELINE_STAGES = ['awareness', 'interest', 'consideration', 'intent', 'purchase'] as const

  const columns: ColumnDef<Lead>[] = [
    {
      key: 'select',
      header: '',
      width: '40px',
      render: (row) => (
        <input
          type="checkbox"
          checked={selected.has(row.id)}
          onChange={() => toggleSelect(row.id)}
          aria-label={`Select lead ${row.email ?? row.id}`}
          className="rounded border-neutral-600 bg-neutral-800 text-brand-600"
        />
      ),
    },
    { key: 'email', header: 'Email', sortable: true },
    { key: 'name', header: 'Name', sortable: true },
    { key: 'company', header: 'Company', sortable: true },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <Badge color={statusColor(row.status)}>{row.status}</Badge>,
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
  ]

  return (
    <AppLayout title="Leads">
      <PageHeader
        title="Leads"
        subtitle={`${leads.length} leads`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant={view === 'table' ? 'primary' : 'ghost'} size="sm" onClick={() => setView('table')}>Table</Button>
            <Button variant={view === 'pipeline' ? 'primary' : 'ghost'} size="sm" onClick={() => setView('pipeline')}>Pipeline</Button>
          </div>
        }
      />

      {/* Bulk actions toolbar */}
      {selected.size > 0 && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-brand-700 bg-brand-950 px-4 py-2 text-sm">
          <span className="text-brand-300">{selected.size} selected</span>
          <Button size="sm" variant="ghost" onClick={clearAll}>Deselect All</Button>
          <Button size="sm" variant="secondary" onClick={() => { /* bulk action */ }}>Export Selected</Button>
        </div>
      )}

      <div className="mt-4">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : view === 'table' ? (
          <DataTable
            columns={columns}
            data={leads}
            keyExtractor={(row) => row.id}
            emptyMessage="No leads yet."
          />
        ) : (
          /* Pipeline Kanban */
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
            {PIPELINE_STAGES.map((stage) => (
              <div key={stage} className="rounded-xl border border-neutral-700 bg-neutral-900 min-h-32">
                <div className="border-b border-neutral-700 px-4 py-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-400 capitalize">{stage}</h3>
                </div>
                <div className="p-2 space-y-2">
                  {leads.map((lead) => (
                    <div key={lead.id} className="rounded-lg border border-neutral-700 bg-neutral-800 p-2">
                      <p className="text-xs font-medium text-neutral-200">{lead.name ?? lead.email}</p>
                      <p className="text-xs text-neutral-500">{lead.company ?? '—'}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected.size > 0 && (
        <div className="mt-4">
          <Button variant="ghost" size="sm" onClick={selectAll}>Select All ({leads.length})</Button>
        </div>
      )}
    </AppLayout>
  )
}
