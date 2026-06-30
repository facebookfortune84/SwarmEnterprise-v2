import { useEffect, useRef } from 'react'
import { useBuildStream } from '@/hooks/useBuildStream'

interface BuildTerminalProps {
  maxLines?: number
  lines?: string[]
  isStreaming?: boolean
  error?: string | null
  onClear?: () => void
  className?: string
}

export function BuildTerminal({
  maxLines = 200,
  lines: externalLines,
  isStreaming: externalStreaming,
  error: externalError,
  onClear,
  className = '',
}: BuildTerminalProps) {
  const { lines: internalLines, status } = useBuildStream()
  const lines = externalLines ?? internalLines
  const isStreaming = externalStreaming ?? status === 'streaming'
  const error = externalError ?? null

  const displayed = lines.slice(-maxLines)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className={`flex flex-col rounded-xl border border-neutral-700 bg-neutral-950 ${className}`}>
      <div className="flex items-center justify-between border-b border-neutral-700 px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full bg-red-500" />
            <span className="h-3 w-3 rounded-full bg-yellow-500" />
            <span className="h-3 w-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs text-neutral-500 font-mono ml-2">build terminal</span>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-xs text-green-400">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              Streaming
            </span>
          )}
          {onClear && (
            <button
              onClick={onClear}
              className="text-xs text-neutral-500 hover:text-neutral-300 px-2 py-1 rounded"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div
        className="flex-1 overflow-y-auto p-4 font-mono text-xs min-h-48 max-h-96"
        role="log"
        aria-live="polite"
        aria-label="Build output"
      >
        {error && <p className="text-red-400 mb-2">Error: {error}</p>}
        {displayed.length === 0 && !isStreaming && !error && (
          <p className="text-neutral-600">Waiting for build events...</p>
        )}
        {displayed.map((line, i) => (
          <div
            key={i}
            className={`leading-relaxed whitespace-pre-wrap break-all ${
              line.startsWith('ERROR') || line.toLowerCase().startsWith('error')
                ? 'text-red-400'
                : line.startsWith('WARN') || line.toLowerCase().startsWith('warn')
                  ? 'text-yellow-400'
                  : line.startsWith('✓') || line.startsWith('SUCCESS')
                    ? 'text-green-400'
                    : 'text-neutral-300'
            }`}
          >
            <span className="text-neutral-700 mr-2 select-none">{String(i + 1).padStart(3, ' ')}</span>
            {line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
