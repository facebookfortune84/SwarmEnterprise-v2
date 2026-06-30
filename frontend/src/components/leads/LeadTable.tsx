import { DataTable, Badge, Skeleton } from '@/components/ui'
import type { Lead } from '@/types/api'
import type { ColumnDef } from '@/components/ui'

export interface LeadTableProps {
  leads: Lead[]
  loading?: boolean
  onSelect: (ids: string[]) => void
  selectedIds: string[]
}

function intentColor(score?: number): 'success' | 'warning' | 'danger' | 'neutral' {
  if (score === undefined || score === null) return 'neutral'
  if (score >= 70) return 'success'
  if (score >= 40) return 'warning'
  return 'danger'
}

export function LeadTable({ leads, loading, onSelect, selectedIds }: LeadTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    )
  }

  const allSelected = leads.length > 0 && leads.every(l => selectedIds.includes(l.id))

  const toggleAll = () => {
    if (allSelected) {
      onSelect([])
    } else {
      onSelect(leads.map(l => l.id))
    }
  }

  const toggleOne = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelect(selectedIds.filter(s => s !== id))
    } else {
      onSelect([...selectedIds, id])
    }
  }

  const columns: ColumnDef<Lead>[] = [
    {
      key: 'id',
      header: '',
      width: '40px',
      render: (row) => (
        <input
          type="checkbox"
          checked={selectedIds.includes(row.id)}
          onChange={() => toggleOne(row.id)}
          aria-label={`Select lead ${row.email ?? row.id}`}
          className="rounded"
        />
      ),
    },
    { key: 'name', header: 'Name', sortable: true },
    { key: 'email', header: 'Email', sortable: true },
    { key: 'company', header: 'Company', sortable: true },
    {
      key: 'intent_score',
      header: 'Intent Score',
      sortable: true,
      render: (row) => (
        <Badge color={intentColor(row.intent_score)}>
          {row.intent_score ?? '—'}
        </Badge>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge color="neutral">{row.status}</Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
  ]

  return (
    <div>
      <div className="px-4 py-2 border-b border-neutral-800 flex items-center gap-2">
        <input
          type="checkbox"
          checked={allSelected}
          onChange={toggleAll}
          aria-label="Select all leads"
          className="rounded"
        />
        <span className="text-xs text-neutral-500">{leads.length} leads</span>
      </div>
      <DataTable
        columns={columns as unknown as ColumnDef<Record<string, unknown>>[]}
        data={leads as unknown as Record<string, unknown>[]}
        keyExtractor={(row) => (row as unknown as Lead).id}
        emptyMessage="No leads found."
      />
    </div>
  )
}
