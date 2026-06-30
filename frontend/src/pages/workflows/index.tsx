import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Badge, DataTable, Skeleton } from '@/components/ui'
import { toast } from 'react-hot-toast'
import ApiClient from '@/services/ApiClient'
import type { Workflow } from '@/types/api'
import type { ColumnDef } from '@/components/ui'

const statusColor = (s: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' => {
  if (s === 'completed') return 'success'
  if (s === 'running') return 'info'
  if (s === 'paused') return 'warning'
  if (s === 'failed') return 'danger'
  return 'neutral'
}

export default function WorkflowsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      try {
        return await ApiClient.workflows.list()
      } catch {
        // Return empty array if endpoint doesn't exist
        return []
      }
    },
  })

  const workflows = Array.isArray(data) ? data : []

  const launchMut = useMutation({
    mutationFn: (id: string) => ApiClient.workflows.trigger(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['workflows'] })
      toast.success('Workflow launched!')
    },
    onError: () => { toast.error('Failed to launch workflow') },
  })

  const columns: ColumnDef<Workflow>[] = [
    { key: 'name', header: 'Name', sortable: true },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <Badge color={statusColor(row.status)}>{row.status}</Badge>,
    },
    {
      key: 'current_step',
      header: 'Step',
      render: (row) => String(row.current_step),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <Button
          size="sm"
          variant="secondary"
          disabled={row.status === 'running'}
          onClick={() => launchMut.mutate(row.id)}
        >
          {row.status === 'running' ? 'Running…' : 'Trigger'}
        </Button>
      ),
    },
  ]

  return (
    <AppLayout title="Workflows">
      <PageHeader
        title="Workflows"
        subtitle={`${workflows.length} workflows`}
        actions={
          <Button onClick={() => navigate('/workflows/builder')}>+ Builder</Button>
        }
      />

      <div className="mt-6">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <DataTable
            columns={columns as unknown as ColumnDef<Record<string, unknown>>[]}
            data={workflows as unknown as Record<string, unknown>[]}
            keyExtractor={(row) => (row as unknown as Workflow).id}
            emptyMessage="No workflows yet. Create one in the builder."
          />
        )}
      </div>
    </AppLayout>
  )
}
