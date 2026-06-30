import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    coverage: {
      provider: 'v8',
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 90,
        statements: 90,
      },
      include: [
        'src/lib/**',
        'src/components/ui/Badge.tsx',
        'src/components/ui/Button.tsx',
        'src/components/ui/Card.tsx',
        'src/components/ui/DataTable.tsx',
        'src/components/ui/Input.tsx',
        'src/components/ui/Modal.tsx',
        'src/components/ui/PageHeader.tsx',
        'src/components/ui/Select.tsx',
        'src/components/ui/Skeleton.tsx',
        'src/components/ui/Tabs.tsx',
        'src/components/ui/Textarea.tsx',
        'src/components/dashboard/KpiCard.tsx',
        'src/components/dashboard/AgentFeed.tsx',
        'src/components/leads/LeadTable.tsx',
        'src/components/leads/BulkActionsToolbar.tsx',
      ],
      exclude: [
        'node_modules/**',
        'src/test-setup.ts',
        'src/service-worker.ts',
        'src/main.tsx',
        '**/*.d.ts',
        '**/__tests__/**',
      ],
    },
  },
})
