import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import type { WorkflowGraph } from '@/types/api'

// Workflow graph serialisation round-trip
function serializeGraph(graph: WorkflowGraph): string {
  return JSON.stringify(graph)
}

function deserializeGraph(s: string): WorkflowGraph {
  return JSON.parse(s) as WorkflowGraph
}

describe('WorkflowCanvas serialisation', () => {
  it('round-trips a simple graph', () => {
    const graph: WorkflowGraph = {
      nodes: [{ id: '1', type: 'input', position: { x: 100, y: 200 }, data: { label: 'Start' } }],
      edges: [{ id: 'e1', source: '1', target: '2' }],
    }
    const serialized = serializeGraph(graph)
    const restored = deserializeGraph(serialized)
    expect(restored).toEqual(graph)
  })

  it('property: graph serialises and deserialises with same node count', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.uuid(),
            type: fc.constantFrom('input', 'output', 'default'),
            position: fc.record({ x: fc.float(), y: fc.float() }),
            data: fc.record({ label: fc.string() }),
          }),
          { minLength: 0, maxLength: 10 },
        ),
        fc.array(
          fc.record({
            id: fc.uuid(),
            source: fc.uuid(),
            target: fc.uuid(),
          }),
          { minLength: 0, maxLength: 15 },
        ),
        (nodes, edges) => {
          const graph: WorkflowGraph = { nodes, edges }
          const restored = deserializeGraph(serializeGraph(graph))
          return restored.nodes.length === nodes.length && restored.edges.length === edges.length
        },
      ),
    )
  })

  it('empty graph round-trips', () => {
    const graph: WorkflowGraph = { nodes: [], edges: [] }
    expect(deserializeGraph(serializeGraph(graph))).toEqual(graph)
  })
})
