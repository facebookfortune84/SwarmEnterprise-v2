import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button, Badge, Modal, Input, Select, Skeleton } from '@/components/ui'
import { toast } from '@/components/ui/Toast'
import { ApiClient } from '@/services/ApiClient'
import type { Ticket } from '@/types/api'

type TicketStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED'
interface TicketForm { title: string; instruction: string; priority: string }

const COLUMNS: TicketStatus[] = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']

const priorityColor = (p: string): 'danger' | 'warning' | 'neutral' | 'info' => {
  if (p === 'critical') return 'danger'
  if (p === 'high') return 'warning'
  if (p === 'medium') return 'info'
  return 'neutral'
}

export default function TicketsPage() {
  const queryClient = useQueryClient()
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<TicketForm>({ title: '', instruction: '', priority: 'medium' })

  const { data, isLoading } = useQuery({
    queryKey: ['tickets'],
    queryFn: () => ApiClient.tickets.list(),
  })

  const allTickets = (data ?? []) as Ticket[]

  const moveMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TicketStatus }) => {
      // Optimistic update
      queryClient.setQueryData<Ticket[]>(['tickets'], (prev) =>
        prev ? prev.map((t: Ticket) => t.id === id ? { ...t, status } : t) : prev
      )
      return ApiClient.tickets.update(id, { status })
    },
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['tickets'] }) },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      toast.error('Failed to move ticket')
    },
  })

  const handleDrop = useCallback((e: React.DragEvent, newStatus: TicketStatus) => {
    e.preventDefault()
    const id = e.dataTransfer.getData('ticketId')
    if (id) moveMut.mutate({ id, status: newStatus })
  }, [moveMut])

  return (
    <AppLayout title="Tickets">
      <PageHeader
        title="Tickets"
        subtitle="Kanban board"
        actions={<Button onClick={() => setShowCreate(true)}>+ New Ticket</Button>}
      />

      {isLoading ? (
        <Skeleton className="h-96 w-full mt-6" />
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {COLUMNS.map((col) => {
            const colTickets = allTickets.filter((t: Ticket) => t.status === col)
            return (
              <div
                key={col}
                className="rounded-xl border border-neutral-700 bg-neutral-900 min-h-64"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleDrop(e, col)}
              >
                <div className="flex items-center justify-between border-b border-neutral-700 px-4 py-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">{col.replace('_', ' ')}</h3>
                  <span className="text-xs text-neutral-600">{colTickets.length}</span>
                </div>
                <div className="p-2 space-y-2">
                  {colTickets.map((ticket: Ticket) => (
                    <div
                      key={ticket.id}
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData('ticketId', ticket.id)}
                      onClick={() => setSelectedTicket(ticket)}
                      className="cursor-pointer rounded-lg border border-neutral-700 bg-neutral-800 p-3 hover:border-neutral-600 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-medium text-neutral-200 leading-snug">{ticket.title}</p>
                        <Badge color={priorityColor(ticket.priority)} size="sm">{ticket.priority}</Badge>
                      </div>
                      <p className="text-xs text-neutral-500 mt-1 font-mono">{ticket.id}</p>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Ticket detail modal */}
      <Modal
        isOpen={!!selectedTicket}
        onClose={() => setSelectedTicket(null)}
        title={selectedTicket?.title ?? ''}
        footer={
          <Button variant="ghost" onClick={() => setSelectedTicket(null)}>Close</Button>
        }
      >
        {selectedTicket && (
          <div className="space-y-3 text-sm">
            <div className="flex gap-3 flex-wrap">
              <Badge color={priorityColor(selectedTicket.priority)}>{selectedTicket.priority}</Badge>
              <Badge color="neutral">{selectedTicket.status}</Badge>
            </div>
            <div>
              <p className="text-neutral-500 text-xs">Instruction</p>
              <p className="text-neutral-300 mt-1">{selectedTicket.instruction}</p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div><span className="text-neutral-500">Created: </span><span className="text-neutral-300">{new Date(selectedTicket.created_at).toLocaleDateString()}</span></div>
              {selectedTicket.due_date && <div><span className="text-neutral-500">Due: </span><span className="text-neutral-300">{new Date(selectedTicket.due_date).toLocaleDateString()}</span></div>}
            </div>
            <div className="pt-2 border-t border-neutral-700">
              <p className="text-neutral-500 text-xs mb-2">Move to:</p>
              <div className="flex flex-wrap gap-2">
                {COLUMNS.filter((c) => c !== selectedTicket.status).map((c) => (
                  <Button key={c} size="sm" variant="ghost" onClick={() => { moveMut.mutate({ id: selectedTicket.id, status: c }); setSelectedTicket(null) }}>
                    {c.replace('_', ' ')}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Create ticket modal */}
      <Modal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        title="Create Ticket"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={() => { toast.info('Create not available'); setShowCreate(false) }}>Create</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input label="Title" value={form.title} onChange={(e) => setForm((f: TicketForm) => ({ ...f, title: e.target.value }))} required />
          <Input label="Instruction" value={form.instruction} onChange={(e) => setForm((f: TicketForm) => ({ ...f, instruction: e.target.value }))} />
          <Select
            label="Priority"
            value={form.priority}
            onChange={(e) => setForm((f: TicketForm) => ({ ...f, priority: e.target.value }))}
            options={[
              { value: 'low', label: 'Low' },
              { value: 'medium', label: 'Medium' },
              { value: 'high', label: 'High' },
              { value: 'critical', label: 'Critical' },
            ]}
          />
        </div>
      </Modal>
    </AppLayout>
  )
}
