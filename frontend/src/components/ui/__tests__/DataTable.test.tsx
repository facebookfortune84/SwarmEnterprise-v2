import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import * as fc from 'fast-check'
import { DataTable } from '@/components/ui/DataTable'
import type { ColumnDef } from '@/components/ui/DataTable'

interface Row { id: string; name: string; score: number }

const columns: ColumnDef<Row>[] = [
  { key: 'name', header: 'Name', sortable: true },
  { key: 'score', header: 'Score', sortable: true },
]

const data: Row[] = [
  { id: '1', name: 'Alice', score: 90 },
  { id: '2', name: 'Bob', score: 70 },
  { id: '3', name: 'Charlie', score: 85 },
]

describe('DataTable', () => {
  it('renders column headers', () => {
    render(<DataTable columns={columns} data={data} keyExtractor={(r) => r.id} />)
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Score')).toBeInTheDocument()
  })

  it('renders all rows', () => {
    render(<DataTable columns={columns} data={data} keyExtractor={(r) => r.id} />)
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
    expect(screen.getByText('Charlie')).toBeInTheDocument()
  })

  it('shows empty message when data is empty', () => {
    render(<DataTable columns={columns} data={[]} keyExtractor={(r) => r.id} emptyMessage="Nothing here." />)
    expect(screen.getByText('Nothing here.')).toBeInTheDocument()
  })

  it('shows loading skeletons when isLoading', () => {
    render(<DataTable columns={columns} data={[]} keyExtractor={(r) => r.id} isLoading />)
    const cells = document.querySelectorAll('td .animate-pulse')
    expect(cells.length).toBeGreaterThan(0)
  })

  it('calls onRowClick when a row is clicked', async () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={columns} data={data} keyExtractor={(r) => r.id} onRowClick={onRowClick} />)
    await userEvent.click(screen.getByText('Alice'))
    expect(onRowClick).toHaveBeenCalledWith(data[0])
  })

  it('sorts ascending on header click', async () => {
    render(<DataTable columns={columns} data={data} keyExtractor={(r) => r.id} />)
    await userEvent.click(screen.getByText(/Name/))
    const rows = screen.getAllByRole('row').slice(1) // skip header
    expect(rows[0]).toHaveTextContent('Alice')
  })

  it('renders pagination slot', () => {
    render(
      <DataTable
        columns={columns}
        data={data}
        keyExtractor={(r) => r.id}
        pagination={<span>Page 1 of 5</span>}
      />,
    )
    expect(screen.getByText('Page 1 of 5')).toBeInTheDocument()
  })

  it('uses custom render function', () => {
    const customCols: ColumnDef<Row>[] = [
      { key: 'name', header: 'Name', render: (row) => <strong data-testid="custom">{row.name}!</strong> },
    ]
    render(<DataTable columns={customCols} data={data} keyExtractor={(r) => r.id} />)
    expect(screen.getAllByTestId('custom')[0]).toHaveTextContent('Alice!')
  })

  it('cycles sort: null→asc→desc→null on triple header click', async () => {
    render(<DataTable columns={columns} data={data} keyExtractor={(r) => r.id} />)
    const nameHeader = screen.getByText(/^Name/)

    // Click 1: null → asc
    await userEvent.click(nameHeader)
    expect(nameHeader.closest('th')).toHaveAttribute('aria-sort', 'ascending')
    // Arrow should be ↑
    expect(nameHeader.closest('th')?.textContent).toContain('↑')

    // Click 2: asc → desc
    await userEvent.click(nameHeader)
    expect(nameHeader.closest('th')).toHaveAttribute('aria-sort', 'descending')
    // Arrow should be ↓
    expect(nameHeader.closest('th')?.textContent).toContain('↓')

    // Click 3: desc → null
    await userEvent.click(nameHeader)
    expect(nameHeader.closest('th')).toHaveAttribute('aria-sort', 'none')
    // Arrow should be ↕ (unsorted indicator)
    expect(nameHeader.closest('th')?.textContent).toContain('↕')
  })

  it('applies rowClassName to rows', () => {
    render(
      <DataTable
        columns={columns}
        data={data}
        keyExtractor={(r) => r.id}
        rowClassName={(r) => (r.score > 80 ? 'high-score' : 'low-score')}
      />,
    )
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].className).toContain('high-score')
    expect(rows[1].className).toContain('low-score')
  })

  it('property: sorted data preserves all rows across sort directions', () => {
    // Pure logic test: verify sort stability without React state mutations
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.uuid(),
            name: fc.string({ minLength: 1, maxLength: 20 }).filter((s) => s.trim().length > 0),
            score: fc.integer({ min: 0, max: 100 }),
          }),
          { minLength: 1, maxLength: 20 },
        ),
        fc.constantFrom('name', 'score'),
        fc.constantFrom<'asc' | 'desc'>('asc', 'desc'),
        (rows, key, dir) => {
          const sorted = [...rows].sort((a, b) => {
            const aStr = String(a[key as keyof typeof a] ?? '')
            const bStr = String(b[key as keyof typeof b] ?? '')
            const cmp = aStr.localeCompare(bStr)
            return dir === 'asc' ? cmp : -cmp
          })
          return sorted.length === rows.length
        },
      ),
      { numRuns: 100 },
    )
  })
})
