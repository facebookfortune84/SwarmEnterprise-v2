import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Input, Select } from '@/components/ui'
import { toast } from '@/components/ui/Toast'
import { ApiClient } from '@/services/ApiClient'
import { KpiCard } from '@/components/dashboard/KpiCard'
import { AgentFeed } from '@/components/dashboard/AgentFeed'
import { OutreachChart } from '@/components/dashboard/OutreachChart'
import { BuildTerminal } from '@/components/dashboard/BuildTerminal'
import { useAgentFeed } from '@/hooks/useAgentFeed'
import { useBuildStream } from '@/hooks/useBuildStream'

export default function DashboardPage() {
  const { events, status, connect } = useAgentFeed()
  const buildStream = useBuildStream()

  const [buildName, setBuildName] = useState('')
  const [buildDesc, setBuildDesc] = useState('')
  const [buildStack, setBuildStack] = useState('nextjs')

  // Connect to agent feed on mount
  React.useEffect(() => {
    connect()
  }, [connect])

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => ApiClient.health.check(),
    refetchInterval: 30_000,
  })

  const { data: opsData, isLoading: opsLoading } = useQuery({
    queryKey: ['ops-status'],
    queryFn: () => ApiClient.ops.status() as Promise<{ agents_running?: number; tasks_queued?: number; tasks_completed_24h?: number }>,
    refetchInterval: 30_000,
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['outreach-metrics'],
    queryFn: () => ApiClient.analytics.metrics(
      new Date(Date.now() - 7 * 86400000).toISOString(),
      new Date().toISOString(),
    ),
  })

  const handleBuild = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!buildName.trim()) { toast.error('Project name is required'); return }
    try {
      const result = await ApiClient.build.trigger(buildName, buildDesc, buildStack)
      toast.success('Build started!')
      buildStream.start(`/api/build/${(result as { project_id: string }).project_id}/stream`)
    } catch {
      toast.error('Failed to trigger build')
    }
  }

  return (
    <AppLayout title="Dashboard">
      <PageHeader
        title="Dashboard"
        subtitle="System overview and live agent activity"
      />

      {/* KPI Cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="System Status"
          value={(health as { status?: string })?.status ?? '—'}
          color={(health as { status?: string })?.status === 'healthy' ? 'success' : 'warning'}
          isLoading={healthLoading}
          icon={<span>💚</span>}
        />
        <KpiCard
          title="Agents Running"
          value={opsData?.agents_running ?? 0}
          isLoading={opsLoading}
          icon={<span>🤖</span>}
        />
        <KpiCard
          title="Tasks Queued"
          value={opsData?.tasks_queued ?? 0}
          isLoading={opsLoading}
          icon={<span>📋</span>}
        />
        <KpiCard
          title="Completed (24h)"
          value={opsData?.tasks_completed_24h ?? 0}
          color="success"
          isLoading={opsLoading}
          icon={<span>✅</span>}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <AgentFeed events={events} status={status} />
        <OutreachChart metrics={metrics ?? []} isLoading={metricsLoading} />
      </div>

      {/* Build Sprint Form */}
      <div className="mt-6 rounded-xl border border-neutral-700 bg-neutral-900 p-6">
        <h2 className="text-sm font-semibold text-neutral-200 mb-4">Build Sprint</h2>
        <form onSubmit={e => { void handleBuild(e) }} className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <Input
            label="Project Name"
            value={buildName}
            onChange={e => setBuildName(e.target.value)}
            placeholder="my-company"
          />
          <Input
            label="Description"
            value={buildDesc}
            onChange={e => setBuildDesc(e.target.value)}
            placeholder="A brief description"
          />
          <Select
            label="Stack"
            value={buildStack}
            onChange={e => setBuildStack(e.target.value)}
            options={[
              { value: 'nextjs', label: 'Next.js' },
              { value: 'react', label: 'React' },
              { value: 'fastapi', label: 'FastAPI' },
              { value: 'django', label: 'Django' },
            ]}
          />
          <div className="flex items-end gap-2">
            <Button type="submit" loading={buildStream.status === 'streaming'} className="flex-1">
              {buildStream.status === 'streaming' ? 'Building…' : '🚀 Build'}
            </Button>
            {buildStream.status === 'streaming' && (
              <Button variant="ghost" type="button" onClick={buildStream.reset}>Stop</Button>
            )}
          </div>
        </form>

        <div className="mt-4">
          <BuildTerminal
            lines={buildStream.lines}
            isStreaming={buildStream.status === 'streaming'}
            error={buildStream.status === 'error' ? 'Stream error' : null}
            onClear={buildStream.reset}
          />
        </div>
      </div>
    </AppLayout>
  )
}
