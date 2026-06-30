import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Badge, Skeleton } from '@/components/ui'
import { ApiClient } from '@/services/ApiClient'

export default function CompanyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: company, isLoading, error } = useQuery({
    queryKey: ['company', id],
    queryFn: () => ApiClient.companies.get(id!),
    enabled: !!id,
    retry: false,
  })

  if (isLoading) {
    return (
      <AppLayout title="Company">
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
          <Skeleton className="h-48 w-full" />
        </div>
      </AppLayout>
    )
  }

  if (error || !company) {
    return (
      <AppLayout title="Company Not Found">
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <span className="text-5xl mb-4">🏢</span>
          <h2 className="text-xl font-semibold text-neutral-200 mb-2">Company Not Found</h2>
          <p className="text-neutral-500 mb-6">The company you're looking for doesn't exist or was deleted.</p>
          <Button onClick={() => navigate('/companies')}>← Back to Companies</Button>
        </div>
      </AppLayout>
    )
  }

  const statusColorMap: Record<string, 'success' | 'warning' | 'danger' | 'neutral' | 'info'> = {
    completed: 'success', running: 'success', generating: 'info', pending: 'neutral', failed: 'danger',
  }

  return (
    <AppLayout title={company.name}>
      <PageHeader
        title={company.name}
        subtitle={`ID: ${company.id}`}
        actions={
          <Button variant="ghost" onClick={() => navigate('/companies')}>← Back</Button>
        }
      />

      <div className="mt-6 grid gap-6 max-w-3xl">
        <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-6">
          <div className="flex items-center gap-3 mb-6">
            <Badge color={statusColorMap[company.status] ?? 'neutral'} size="md">{company.status}</Badge>
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-neutral-500">Tech Stack</dt>
              <dd className="text-neutral-200 font-medium mt-1">{company.tech_stack ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-neutral-500">Created</dt>
              <dd className="text-neutral-200 font-medium mt-1">{new Date(company.created_at).toLocaleDateString()}</dd>
            </div>
            <div>
              <dt className="text-neutral-500">Updated</dt>
              <dd className="text-neutral-200 font-medium mt-1">
                {company.updated_at ? new Date(company.updated_at).toLocaleDateString() : '—'}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </AppLayout>
  )
}
