import { useState } from 'react'

export interface BulkActionsToolbarProps {
  selectedCount: number
  onEnrich: () => void
  onExport: () => void
  onDelete: () => void
  disabled?: boolean
}

export function BulkActionsToolbar({
  selectedCount,
  onEnrich,
  onExport,
  onDelete,
  disabled = false,
}: BulkActionsToolbarProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  if (selectedCount === 0) return null

  return (
    <div className="flex items-center gap-3 rounded-lg border border-blue-700 bg-blue-950 px-4 py-2 text-sm">
      <span className="text-blue-300 font-medium">
        {selectedCount} selected
      </span>
      <div className="flex gap-2 ml-2">
        <button
          onClick={onEnrich}
          disabled={disabled}
          className="px-3 py-1.5 text-xs bg-neutral-700 text-neutral-200 rounded hover:bg-neutral-600 disabled:opacity-50"
          aria-label="Enrich selected leads"
        >
          Enrich
        </button>
        <button
          onClick={onExport}
          disabled={disabled}
          className="px-3 py-1.5 text-xs bg-neutral-700 text-neutral-200 rounded hover:bg-neutral-600 disabled:opacity-50"
          aria-label="Export selected leads"
        >
          Export
        </button>
        {showDeleteConfirm ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-red-300">Are you sure?</span>
            <button
              onClick={() => { setShowDeleteConfirm(false); onDelete() }}
              className="px-3 py-1.5 text-xs bg-red-700 text-white rounded hover:bg-red-600"
              aria-label="Confirm delete"
            >
              Confirm
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="px-3 py-1.5 text-xs bg-neutral-700 text-neutral-200 rounded hover:bg-neutral-600"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            disabled={disabled}
            className="px-3 py-1.5 text-xs bg-red-800 text-red-200 rounded hover:bg-red-700 disabled:opacity-50"
            aria-label="Delete selected leads"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  )
}
