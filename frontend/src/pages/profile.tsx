import React, { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Input, Modal, DataTable, Badge, Skeleton } from '@/components/ui'
import { toast } from '@/components/ui/Toast'
import { ApiClient } from '@/services/ApiClient'
import { useAuthStore } from '@/store/authStore'
import type { APIKey, APIKeyCreatePayload } from '@/types/api'
import type { ColumnDef } from '@/components/ui'

export default function ProfilePage() {
  const { getDecodedToken } = useAuthStore()
  const decoded = getDecodedToken()
  const queryClient = useQueryClient()

  const [fullName, setFullName] = useState(decoded?.sub ?? '')
  const [showCreateKey, setShowCreateKey] = useState(false)
  const [keyName, setKeyName] = useState('')
  const [keyScope, setKeyScope] = useState('read:write')
  const [revokeTarget, setRevokeTarget] = useState<APIKey | null>(null)

  const { data: apiKeys, isLoading: keysLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => ApiClient.profile.listApiKeys(),
  })

  const updateMut = useMutation({
    mutationFn: (data: { full_name: string }) => ApiClient.profile.updateMe(data),
    onSuccess: () => { toast.success('Profile updated') },
    onError: () => { toast.error('Failed to update profile') },
  })

  const createKeyMut = useMutation({
    mutationFn: (payload: APIKeyCreatePayload) => ApiClient.profile.createApiKey(payload),
    onSuccess: () => {
      toast.success('API key created')
      void queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setShowCreateKey(false)
      setKeyName('')
    },
    onError: () => { toast.error('Failed to create API key') },
  })

  const revokeKeyMut = useMutation({
    mutationFn: (id: string) => ApiClient.profile.revokeApiKey(id),
    onSuccess: () => {
      toast.success('API key revoked')
      void queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setRevokeTarget(null)
    },
    onError: () => { toast.error('Failed to revoke key') },
  })

  const handleUpdateProfile = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!fullName.trim()) return
      updateMut.mutate({ full_name: fullName.trim() })
    },
    [fullName, updateMut],
  )

  const columns: ColumnDef<APIKey>[] = [
    { key: 'name', header: 'Name', sortable: true },
    { key: 'scope', header: 'Scope' },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => (
        <Badge color={row.is_active ? 'success' : 'neutral'}>{row.is_active ? 'Active' : 'Revoked'}</Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: '',
      render: (row) =>
        row.is_active ? (
          <Button variant="danger" size="sm" onClick={() => setRevokeTarget(row)}>
            Revoke
          </Button>
        ) : null,
    },
  ]

  return (
    <AppLayout title="Profile">
      <PageHeader title="Profile" subtitle="Manage your account settings" />

      <div className="mt-6 grid gap-6 max-w-2xl">
        {/* Profile form */}
        <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-6">
          <h2 className="text-sm font-semibold text-neutral-200 mb-4">Account Information</h2>
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div>
              <p className="text-xs text-neutral-500 mb-1">Email</p>
              <p className="text-sm text-neutral-300">{decoded?.sub ?? '—'}</p>
            </div>
            <Input
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            <Button type="submit" loading={updateMut.isPending}>
              Save Changes
            </Button>
          </form>
        </div>

        {/* API Keys */}
        <div className="rounded-xl border border-neutral-700 bg-neutral-900 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-neutral-200">API Keys</h2>
            <Button size="sm" onClick={() => setShowCreateKey(true)}>
              + New Key
            </Button>
          </div>
          {keysLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <DataTable
              columns={columns as unknown as ColumnDef<Record<string, unknown>>[]}
              data={(apiKeys ?? []) as APIKey[] as unknown as Record<string, unknown>[]}
              keyExtractor={(row) => (row as unknown as APIKey).id}
              emptyMessage="No API keys yet."
            />
          )}
        </div>
      </div>

      {/* Create key modal */}
      <Modal
        isOpen={showCreateKey}
        onClose={() => setShowCreateKey(false)}
        title="Create API Key"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreateKey(false)}>Cancel</Button>
            <Button
              loading={createKeyMut.isPending}
              onClick={() => { if (keyName.trim()) createKeyMut.mutate({ name: keyName.trim(), scope: keyScope }) }}
            >
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input label="Key Name" value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="My API Key" required />
          <Input label="Scope" value={keyScope} onChange={(e) => setKeyScope(e.target.value)} placeholder="read:write" />
        </div>
      </Modal>

      {/* Revoke confirm modal */}
      <Modal
        isOpen={!!revokeTarget}
        onClose={() => setRevokeTarget(null)}
        title="Revoke API Key"
        footer={
          <>
            <Button variant="ghost" onClick={() => setRevokeTarget(null)}>Cancel</Button>
            <Button
              variant="danger"
              loading={revokeKeyMut.isPending}
              onClick={() => { if (revokeTarget) revokeKeyMut.mutate(revokeTarget.id) }}
            >
              Revoke
            </Button>
          </>
        }
      >
        <p className="text-sm text-neutral-300">
          Are you sure you want to revoke <strong>{revokeTarget?.name}</strong>? This action cannot be undone.
        </p>
      </Modal>
    </AppLayout>
  )
}
