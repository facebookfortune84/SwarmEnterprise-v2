import { useRef } from 'react'
import type { WorkflowNode, WorkflowEdge } from '@/types/api'

export interface WorkflowCanvasProps {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  onNodeClick: (nodeId: string) => void
  onAddNode: (type: string) => void
}

const NODE_COLORS: Record<string, string> = {
  trigger: '#6366f1',
  condition: '#f59e0b',
  action: '#10b981',
  delay: '#6b7280',
}

const NODE_TYPES = ['trigger', 'condition', 'action', 'delay']

export function WorkflowCanvas({ nodes, edges, onNodeClick, onAddNode }: WorkflowCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  const getNodeCenter = (node: WorkflowNode) => ({
    x: node.x + 80,
    y: node.y + 30,
  })

  const getEdgePath = (edge: WorkflowEdge) => {
    const src = nodes.find(n => n.id === edge.source)
    const tgt = nodes.find(n => n.id === edge.target)
    if (!src || !tgt) return ''
    const s = getNodeCenter(src)
    const t = getNodeCenter(tgt)
    const mx = (s.x + t.x) / 2
    return `M ${s.x} ${s.y} C ${mx} ${s.y} ${mx} ${t.y} ${t.x} ${t.y}`
  }

  return (
    <div className="relative w-full h-full rounded-xl border border-neutral-700 bg-neutral-950 overflow-hidden">
      {/* Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex gap-2 bg-neutral-900 border border-neutral-700 rounded-lg p-2">
        {NODE_TYPES.map(type => (
          <button
            key={type}
            onClick={() => onAddNode(type)}
            className="px-2 py-1 text-xs font-medium text-neutral-300 hover:bg-neutral-700 rounded capitalize"
            style={{ borderLeft: `3px solid ${NODE_COLORS[type]}` }}
            aria-label={`Add ${type} node`}
          >
            {type}
          </button>
        ))}
      </div>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        className="w-full h-full"
        role="img"
        aria-label="Workflow canvas"
        style={{ background: 'transparent' }}
      >
        {/* Grid dots */}
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <circle cx="16" cy="16" r="1" fill="#374151" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Edges */}
        {edges.map(edge => (
          <path
            key={edge.id}
            d={getEdgePath(edge)}
            fill="none"
            stroke="#6366f1"
            strokeWidth="2"
            strokeDasharray="4 2"
            opacity={0.7}
          />
        ))}

        {/* Nodes */}
        {nodes.map(node => (
          <g
            key={node.id}
            transform={`translate(${node.x},${node.y})`}
            onClick={() => onNodeClick(node.id)}
            style={{ cursor: 'pointer' }}
            role="button"
            aria-label={`Node: ${node.label}`}
          >
            <rect
              width="160"
              height="60"
              rx="8"
              fill="#1f2937"
              stroke={NODE_COLORS[node.type] ?? '#6b7280'}
              strokeWidth="2"
            />
            <text
              x="80"
              y="22"
              textAnchor="middle"
              fill={NODE_COLORS[node.type] ?? '#9ca3af'}
              fontSize="10"
              fontWeight="600"
              className="uppercase tracking-wide"
            >
              {node.type}
            </text>
            <text
              x="80"
              y="42"
              textAnchor="middle"
              fill="#e5e7eb"
              fontSize="12"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>

      {/* Empty state */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-neutral-600 text-sm">Click a node type above to add it to the canvas</p>
        </div>
      )}
    </div>
  )
}
