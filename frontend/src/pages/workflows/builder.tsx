import { useState } from 'react'
import { AppLayout } from '@/components/AppLayout'
import { PageHeader, Button } from '@/components/ui'
import { WorkflowCanvas } from '@/components/workflows/WorkflowCanvas'
import { NodeConfigPanel } from '@/components/workflows/NodeConfigPanel'
import { toast } from 'react-hot-toast'
import ApiClient from '@/services/ApiClient'
import type { WorkflowNode, WorkflowEdge } from '@/types/api'

let nodeIdCounter = 1

export default function WorkflowBuilderPage() {
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [edges] = useState<WorkflowEdge[]>([])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const selectedNode = nodes.find(n => n.id === selectedNodeId) ?? null

  const handleAddNode = (type: string) => {
    const id = `node-${nodeIdCounter++}`
    const newNode: WorkflowNode = {
      id,
      type,
      label: type.charAt(0).toUpperCase() + type.slice(1),
      x: 100 + (nodes.length % 4) * 200,
      y: 100 + Math.floor(nodes.length / 4) * 120,
    }
    setNodes(prev => [...prev, newNode])
  }

  const handleNodeChange = (nodeId: string, config: Record<string, unknown>) => {
    setNodes(prev =>
      prev.map(n => n.id === nodeId ? { ...n, label: String(config.label ?? n.label) } : n)
    )
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await ApiClient.workflows.create({ nodes, edges })
      toast.success('Workflow saved!')
    } catch {
      toast.error('Failed to save workflow')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AppLayout title="Workflow Builder">
      <PageHeader
        title="Workflow Builder"
        subtitle="Design automation workflows visually"
        actions={
          <Button loading={saving} onClick={() => void handleSave()}>
            Save Workflow
          </Button>
        }
      />
      <div className="mt-4 flex gap-4" style={{ height: 'calc(100vh - 14rem)' }}>
        <div className="flex-1">
          <WorkflowCanvas
            nodes={nodes}
            edges={edges}
            onNodeClick={setSelectedNodeId}
            onAddNode={handleAddNode}
          />
        </div>
        <NodeConfigPanel
          node={selectedNode}
          onChange={handleNodeChange}
        />
      </div>
    </AppLayout>
  )
}
