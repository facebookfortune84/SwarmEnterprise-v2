import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Input, DataTable, Badge, Modal, Skeleton } from '@/components/ui'
import { toast } from '@/components/ui/Toast'
import { ApiClient, ApiError } from '@/services/ApiClient'
import type { Company } from '@/types/api'
import type { ColumnDef } from '@/components/ui'
import { useDebounce } from '@/hooks/useDebounce'

export default function CompaniesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', tech_stack: 'nextjs' })
  const [fieldError, setFieldError] = useState<string | null>(null)
  const debouncedSearch = useDebounce(search, 300)
  const limit = 25

  const { data, isLoading } = useQuery({
    queryKey: ['companies', page, debouncedSearch],
    queryFn: () => ApiClient.companies.list({ skip: page * limit, limit }),
  })

  const createMut = useMutation({
    mutationFn: () =>
      ApiClient.companies.create({
        name: form.name.trim(),
        description: form.description.trim(),
        tech_stack: form.tech_stack,
      }),
    onSuccess: () => {
      toast.success('Company generation started!')
      setShowCreate(false)
      setForm({ name: '', description: '', tech_stack: 'nextjs' })
      void queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        setFieldError('A company with this name already exists.')
      } else {
        toast.error('Failed to create company')
      }
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => ApiClient.companies.delete(id),
    onSuccess: () => {
      toast.success('Company deleted')
      void queryClient.invalidateQueries({ queryKey: ['companies'] })
    },
    onError: () => { toast.error('Failed to delete company') },
  })

  const columns: ColumnDef<Company>[] = [
    { key: 'name', header: 'Name', sortable: true },
    { key: 'tech_stack', header: 'Stack' },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => {
        const colorMap: Record<string, 'success' | 'warning' | 'danger' | 'neutral' | 'info'> = {
          completed: 'success', running: 'success', generating: 'info',
          pending: 'neutral', failed: 'danger',
        }
        return <Badge color={colorMap[row.status] ?? 'neutral'}>{row.status}</Badge>
      },
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
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(`/companies/${row.id}`)}>View</Button>
          <Button variant="danger" size="sm" onClick={() => deleteMut.mutate(row.id)}>Delete</Button>
        </div>
      ),
    },
  ]

  const total = (data ?? []).length
  const totalPages = Math.ceil(total / limit)

  const handleCreate = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    setFieldError(null)
    if (!form.name.trim()) { setFieldError('Name is required'); return }
    createMut.mutate()
  }, [form, createMut])

  return (
    <AppLayout title="Companies">
      <PageHeader
        title="Companies"
        subtitle={`${total} companies`}
        actions={
          <Button onClick={() => setShowCreate(true)}>+ Generate Company</Button>
        }
      />

      <div className="mt-4">
        <Input
          placeholder="Search companies…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      <div className="mt-4">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <DataTable
            columns={columns}
            data={data ?? []}
            keyExtractor={(row) => row.id}
            emptyMessage={search ? 'No companies match your search.' : 'No companies yet. Generate one!'}
            onRowClick={(row) => navigate(`/companies/${row.id}`)}
            pagination={
              totalPages > 1 ? (
                <div className="flex items-center gap-3 text-sm text-neutral-400">
                  <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Prev</Button>
                  <span>{page + 1} / {totalPages}</span>
                  <Button variant="ghost" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>Next →</Button>
                </div>
              ) : undefined
            }
          />
        )}
      </div>

      <Modal
        isOpen={showCreate}
        onClose={() => { setShowCreate(false); setFieldError(null) }}
        title="Generate Company"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button loading={createMut.isPending} onClick={handleCreate}>Generate</Button>
          </>
        }
      >
        <form onSubmit={handleCreate} className="space-y-4">
          {fieldError && <p role="alert" className="text-sm text-danger-400">{fieldError}</p>}
          <Input label="Company Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required error={fieldError && !form.name ? fieldError : undefined} />
          <Input label="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          <Input label="Tech Stack" value={form.tech_stack} onChange={(e) => setForm((f) => ({ ...f, tech_stack: e.target.value }))} />
        </form>
      </Modal>
    </AppLayout>
  )
}
