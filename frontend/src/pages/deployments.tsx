import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, DataTable, Badge, Modal, Skeleton } from '@/components/ui'
import { toast } from 'react-hot-toast'
import ApiClient from '@/services/ApiClient'
import type { Deployment } from '@/types/api'
import type { ColumnDef } from '@/components/ui'

export default function DeploymentsPage() {
  const queryClient = useQueryClient()
  const [logsTarget, setLogsTarget] = useState<Deployment | null>(null)
  const [logLines, setLogLines] = useState<string[]>([])
  const [logsLoading, setLogsLoading] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['deployments'],
    queryFn: () => ApiClient.deployments.list(),
    refetchInterval: 15_000,
  })

  const deployments = data ?? []

  const actionMut = useMutation({
    mutationFn: ({ action, id }: { action: 'start' | 'stop' | 'restart'; id: string }) => {
      // Optimistic update
      queryClient.setQueryData<Deployment[]>(['deployments'], (prev) =>
        (prev ?? []).map((d) =>
          d.id === id ? { ...d, status: action === 'stop' ? 'stopped' : 'running' } : d
        )
      )
      if (action === 'start') return ApiClient.deployments.start(id)
      if (action === 'stop') return ApiClient.deployments.stop(id)
      return ApiClient.deployments.restart(id)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['deployments'] })
      toast.success('Action performed')
    },
    onError: (_err, vars) => {
      // Revert optimistic update within 2s
      setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: ['deployments'] })
      }, 2_000)
      toast.error(`Failed to ${vars.action} deployment`)
    },
  })

  const openLogs = useCallback(async (dep: Deployment) => {
    setLogsTarget(dep)
    setLogsLoading(true)
    try {
      const result = await ApiClient.deployments.logs(dep.id, 200)
      setLogLines((result as { logs?: string[] }).logs ?? [])
    } catch {
      toast.error('Failed to fetch logs')
    } finally {
      setLogsLoading(false)
    }
  }, [])

  const statusColor = (s: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' => {
    if (s === 'success' || s === 'running') return 'success'
    if (s === 'in_progress' || s === 'queued') return 'info'
    if (s === 'failed' || s === 'rolled_back') return 'danger'
    return 'neutral'
  }

  const columns: ColumnDef<Deployment>[] = [
    { key: 'tenant_name', header: 'Tenant', sortable: true },
    { key: 'subdomain', header: 'Subdomain', sortable: true },
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
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex gap-1.5 flex-wrap">
          <Button variant="ghost" size="sm" onClick={() => actionMut.mutate({ action: 'start', id: row.id })}>Start</Button>
          <Button variant="ghost" size="sm" onClick={() => actionMut.mutate({ action: 'stop', id: row.id })}>Stop</Button>
          <Button variant="ghost" size="sm" onClick={() => actionMut.mutate({ action: 'restart', id: row.id })}>Restart</Button>
          <Button variant="secondary" size="sm" onClick={() => void openLogs(row)}>Logs</Button>
        </div>
      ),
    },
  ]

  return (
    <AppLayout title="Deployments">
      <PageHeader title="Deployments" subtitle={`${deployments.length} deployments`} />

      <div className="mt-6">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <DataTable
            columns={columns}
            data={deployments}
            keyExtractor={(row) => row.id}
            emptyMessage="No deployments found."
          />
        )}
      </div>

      {/* Logs slide-over */}
      <Modal
        isOpen={!!logsTarget}
        onClose={() => { setLogsTarget(null); setLogLines([]) }}
        title={`Logs — ${logsTarget?.tenant_name ?? ''}`}
        className="max-w-3xl"
      >
        <div className="bg-neutral-950 rounded-lg p-4 font-mono text-xs overflow-y-auto max-h-96 min-h-32">
          {logsLoading ? (
            <p className="text-neutral-500">Loading logs…</p>
          ) : logLines.length === 0 ? (
            <p className="text-neutral-600">No logs available.</p>
          ) : (
            logLines.map((line, i) => (
              <div key={i} className="leading-relaxed text-neutral-300 whitespace-pre-wrap">{line}</div>
            ))
          )}
        </div>
      </Modal>
    </AppLayout>
  )
}
