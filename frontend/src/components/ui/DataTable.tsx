import React, { useState, useCallback } from 'react'
import { clsx } from 'clsx'

export type SortDirection = 'asc' | 'desc' | null

export interface ColumnDef<T> {
  key: string
  header: string
  sortable?: boolean
  width?: string
  className?: string
  render?: (row: T, index: number) => React.ReactNode
}

export interface DataTableProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  keyExtractor: (row: T, index: number) => string
  isLoading?: boolean
  emptyMessage?: string
  pagination?: React.ReactNode
  className?: string
  onRowClick?: (row: T) => void
  rowClassName?: (row: T) => string
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading = false,
  emptyMessage = 'No data found.',
  pagination,
  className,
  onRowClick,
  rowClassName,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDirection>(null)

  const handleSort = useCallback(
    (key: string) => {
      if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : d === 'desc' ? null : 'asc'))
        if (sortDir === 'desc') setSortKey(null)
      } else {
        setSortKey(key)
        setSortDir('asc')
      }
    },
    [sortKey, sortDir],
  )

  const sortedData = React.useMemo(() => {
    if (!sortKey || !sortDir) return data
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey]
      const bVal = (b as Record<string, unknown>)[sortKey]
      const aStr = String(aVal ?? '')
      const bStr = String(bVal ?? '')
      const cmp = aStr.localeCompare(bStr)
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  return (
    <div className={clsx('overflow-x-auto rounded-lg border border-neutral-700', className)}>
      <table
        className="w-full text-sm text-left text-neutral-300"
        role="grid"
        aria-rowcount={data.length}
      >
        <thead className="text-xs uppercase bg-neutral-800 text-neutral-400">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                style={{ width: col.width }}
                className={clsx(
                  'px-4 py-3 whitespace-nowrap',
                  col.sortable && 'cursor-pointer select-none hover:text-neutral-100',
                  col.className,
                )}
                aria-sort={
                  sortKey === col.key
                    ? sortDir === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : 'none'
                }
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {col.sortable && (
                    <span aria-hidden="true" className="text-neutral-600">
                      {sortKey === col.key ? (sortDir === 'asc' ? '↑' : sortDir === 'desc' ? '↓' : '↕') : '↕'}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={`skeleton-${i}`} className="border-t border-neutral-700">
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3">
                    <div className="h-4 rounded bg-gradient-to-r from-neutral-800 via-neutral-700 to-neutral-800 animate-pulse" />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedData.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-neutral-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((row, index) => (
              <tr
                key={keyExtractor(row, index)}
                role="row"
                aria-rowindex={index + 1}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={clsx(
                  'border-t border-neutral-700 transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-neutral-800',
                  rowClassName?.(row),
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx('px-4 py-3', col.className)}>
                    {col.render
                      ? col.render(row, index)
                      : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
      {pagination && (
        <div className="border-t border-neutral-700 px-4 py-3 flex items-center justify-between bg-neutral-900">
          {pagination}
        </div>
      )}
    </div>
  )
}
