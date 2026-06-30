import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, DataTable, Badge, Button, Skeleton } from '@/components/ui'
import { toast } from '@/components/ui/Toast'
import ApiClient from '@/services/ApiClient'
import { useAuthStore } from '@/store/authStore'
import type { User } from '@/types/api'
import type { ColumnDef } from '@/components/ui'

export default function AdminPage() {
  const { getDecodedToken } = useAuthStore()
  const decoded = getDecodedToken()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const limit = 25

  // Redirect non-admins
  React.useEffect(() => {
    if (decoded && decoded.role !== 'admin') {
      toast.error('Admin access required.')
      navigate('/dashboard', { replace: true })
    }
  }, [decoded, navigate])

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page],
    queryFn: () => ApiClient.admin.listUsers(page * limit, limit),
    enabled: decoded?.role === 'admin',
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      ApiClient.admin.toggleUser(id, is_active),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User updated')
    },
    onError: () => { toast.error('Failed to update user') },
  })

  const columns: ColumnDef<User>[] = [
    { key: 'email', header: 'Email', sortable: true },
    { key: 'full_name', header: 'Name', sortable: true },
    {
      key: 'role',
      header: 'Role',
      render: (row) => (
        <Badge color={row.role === 'admin' ? 'info' : 'neutral'}>{row.role}</Badge>
      ),
    },
    { key: 'subscription_tier', header: 'Tier' },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => (
        <Badge color={row.is_active ? 'success' : 'danger'}>{row.is_active ? 'Active' : 'Inactive'}</Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Joined',
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <Button
          variant={row.is_active ? 'danger' : 'secondary'}
          size="sm"
          loading={toggleMut.isPending}
          onClick={() => toggleMut.mutate({ id: row.id, is_active: !row.is_active })}
        >
          {row.is_active ? 'Deactivate' : 'Activate'}
        </Button>
      ),
    },
  ]

  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / limit)

  return (
    <AppLayout title="Admin">
      <PageHeader title="Admin Panel" subtitle={`${total} users total`} />
      <div className="mt-6">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            keyExtractor={(row) => row.id}
            emptyMessage="No users found."
            pagination={
              totalPages > 1 ? (
                <div className="flex items-center gap-3 text-sm text-neutral-400">
                  <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Prev</Button>
                  <span>Page {page + 1} / {totalPages}</span>
                  <Button variant="ghost" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>Next →</Button>
                </div>
              ) : undefined
            }
          />
        )}
      </div>
    </AppLayout>
  )
}
