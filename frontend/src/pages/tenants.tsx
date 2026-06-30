import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Input, Skeleton } from '@/components/ui'
import { toast } from 'react-hot-toast'
import ApiClient, { ApiError } from '@/services/ApiClient'
import type { Tenant } from '@/types/api'

export default function TenantsPage() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => ApiClient.tenants.list(),
    refetchInterval: 15_000,
  })

  const tenants = Array.isArray(data) ? data : []

  const registerMut = useMutation({
    mutationFn: () => ApiClient.tenants.register(name.trim(), slug.trim() || undefined),
    onSuccess: () => {
      toast.success('Tenant registered!')
      setName(''); setSlug(''); setFormError(null)
      void queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
    onError: (err) => {
      setFormError(err instanceof ApiError ? err.message : 'Registration failed')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { setFormError('Tenant name is required'); return }
    setFormError(null)
    registerMut.mutate()
  }

  const statusColor = (s: Tenant['status']) => {
    if (s === 'running') return 'text-success-400'
    if (s === 'failed') return 'text-danger-400'
    if (s === 'provisioning') return 'text-warning-400'
    return 'text-neutral-400'
  }

  return (
    <AppLayout title="Tenants">
      <PageHeader title="Tenants" subtitle={`${tenants.length} registered`} />

      {/* Inline registration form */}
      <div className="mt-6 rounded-xl border border-neutral-700 bg-neutral-900 p-6 max-w-lg">
        <h2 className="text-sm font-semibold text-neutral-200 mb-4">Register New Tenant</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          {formError && <p role="alert" className="text-sm text-danger-400">{formError}</p>}
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="Acme Corp" />
          <Input label="Slug (optional)" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="acme-corp" />
          <Button type="submit" loading={registerMut.isPending}>Register</Button>
        </form>
      </div>

      {/* Tenant list */}
      <div className="mt-6">
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : tenants.length === 0 ? (
          <div className="py-16 text-center text-neutral-500">No tenants yet.</div>
        ) : (
          <div className="space-y-3">
            {tenants.map((t) => (
              <div key={t.id} className="flex items-center justify-between rounded-lg border border-neutral-700 bg-neutral-900 px-4 py-3">
                <div>
                  <p className="font-medium text-neutral-200">{t.name}</p>
                  <p className="text-xs text-neutral-500">{t.slug}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-medium ${statusColor(t.status)}`}>{t.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
