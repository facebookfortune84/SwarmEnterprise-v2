# Implementation Plan: swarm-enterprise-frontend-outreach

## Overview

This plan implements two major deliverable areas in parallel:

1. **Frontend SPA** — React 18 + TypeScript + Vite replacing the static HTML dashboard, covering authentication, dashboard, project/company/tenant management, Kanban, workflow builder, analytics, CRM lead manager, and Outreach Hub.
2. **Cold Outreach & Marketing Automation Stack** — Five new Python agents (Enrichment, Sequencer, Reply Handler, CRM Sync, Reporting), five new SQLAlchemy models with Alembic migrations, and new FastAPI endpoints.

Both areas target ≥90% test coverage, and property-based tests (fast-check + Hypothesis) cover all 23 correctness properties from the design document.

---

## Tasks

- [ ] 1. Frontend scaffold and tooling
  - [ ] 1.1 Bootstrap Vite 5 + React 18 + TypeScript 5 project
    - Run `npm create vite@5 frontend -- --template react-ts` under the repo root
    - Configure `tsconfig.json` with `"strict": true`, path aliases (`@/` → `src/`), and `"noEmit": true` target
    - Add `react-router-dom@6`, `@tanstack/react-query@5`, `zustand`, `react-hot-toast` to `dependencies`
    - Add `vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `fast-check` to `devDependencies`
    - Create `vite.config.ts` with `react()` plugin, path aliases, and `test` block: `environment: 'jsdom'`, `coverage.provider: 'v8'`, `coverage.thresholds` at 90% for statements/branches/functions/lines
    - _Requirements: 1.1, 14.1_

  - [ ] 1.2 Configure Tailwind CSS 3 with design tokens
    - Install `tailwindcss@3`, `postcss`, `autoprefixer`; run `npx tailwindcss init -p`
    - Extend `tailwind.config.ts` with `brand` palette (50–950), `neutral` greys, `success`/`warning`/`danger` semantic colours, and typographic scale
    - Verify all token pairs achieve WCAG AA contrast ≥ 4.5:1 against `neutral-950` (document verified pairs in config comments)
    - Create `src/index.css` with Tailwind directives
    - _Requirements: 1.4_

  - [ ] 1.3 Configure ESLint, Prettier, and pre-commit hooks
    - Install `eslint`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `@typescript-eslint/eslint-plugin`, `prettier`, `lint-staged`
    - Create `.eslintrc.cjs` with strict TypeScript rules and `no-ts-ignore` rule enabled
    - Create `.prettierrc` and add `"format"` and `"lint"` scripts to `package.json`
    - Add `lint-staged` config to run ESLint and Prettier on staged `.ts`/`.tsx` files
    - _Requirements: 1.3_

  - [ ] 1.4 Create PWA manifest and service worker stub
    - Add `public/manifest.json` with `name`, `short_name`, `icons` (192×192, 512×512 placeholders), `start_url: "/"`, `display: "standalone"`
    - Create `src/service-worker.ts` with a `skipWaiting` message handler and empty `install`/`activate` event listeners
    - Register the service worker in `src/main.tsx` on `window.load`
    - _Requirements: 1.6_

  - [ ] 1.5 Set up App shell: router, React Query provider, Toast provider
    - Create `src/App.tsx` with `BrowserRouter`, `QueryClientProvider`, `Toaster` (react-hot-toast), and top-level `Routes`
    - Create `src/main.tsx` entry point
    - Create `src/types/api.ts` with all TypeScript interfaces from the design: `Lead`, `Sequence`, `SequenceStep`, `InboxReply`, `DailyMetric`, `AgentEvent`, `TimelineEntry`, `Company`, `Deployment`, `Ticket`, `Workflow`, `AuthResponse`, `PaginatedResponse<T>`, and all request payload types
    - _Requirements: 1.1, 1.3_


- [ ] 2. Component Library — UI primitives
  - [ ] 2.1 Implement Button, Badge, and Skeleton primitives
    - Write `src/components/ui/Button.tsx`: variants (primary, secondary, ghost, danger), sizes (sm, md, lg), disabled state, loading spinner slot; fully typed props
    - Write `src/components/ui/Badge.tsx`: colour variants mapped to design tokens (success, warning, danger, neutral); `size` prop
    - Write `src/components/ui/Skeleton.tsx`: accepts `className` for dimensions; renders an animated pulse placeholder
    - Export all three from `src/components/ui/index.ts` barrel
    - _Requirements: 1.2_

  - [ ]* 2.2 Write unit tests for Button, Badge, and Skeleton
    - Test all variants, sizes, disabled state, onClick invocation, ARIA attributes for Button
    - Test all colour variants and size prop for Badge
    - Test className passthrough and animated class presence for Skeleton
    - Achieve ≥90% branch coverage for each; co-locate at `src/components/ui/__tests__/`
    - _Requirements: 1.5, 14.6_

  - [ ] 2.3 Implement Input, Select, and Textarea primitives
    - Write `src/components/ui/Input.tsx`: controlled, `label`, `error`, `helperText`, `type`, `disabled` props; forwards ref
    - Write `src/components/ui/Select.tsx`: controlled, `options: {value, label}[]`, `label`, `error`, `disabled`; accessible `<select>` wrapper
    - Write `src/components/ui/Textarea.tsx`: controlled, `label`, `error`, `rows`, `maxLength` with visible character counter
    - Export from barrel
    - _Requirements: 1.2_

  - [ ]* 2.4 Write unit tests for Input, Select, and Textarea
    - Test controlled value changes, error display, disabled state, label association, ARIA attributes
    - Achieve ≥90% branch coverage each
    - _Requirements: 1.5, 14.6_

  - [ ] 2.5 Implement Modal and Toast primitives
    - Write `src/components/ui/Modal.tsx`: focus-trap, `isOpen`/`onClose` props, title slot, body slot, footer slot, ESC key handler, backdrop click dismiss; accessible `role="dialog"` and `aria-modal`
    - Write `src/components/ui/Toast.tsx`: wraps `react-hot-toast`; exposes `toast.success`, `toast.error`, `toast.info` helpers; default 8-second auto-dismiss; manually dismissable via × button
    - Export from barrel
    - _Requirements: 1.2_

  - [ ]* 2.6 Write unit tests for Modal and Toast
    - Test open/close, focus trap, ESC dismiss, backdrop dismiss, slot rendering for Modal
    - Test auto-dismiss timing (vi.useFakeTimers), manual dismiss, message rendering for Toast
    - Achieve ≥90% branch coverage each
    - _Requirements: 1.5, 14.6_


  - [ ] 2.7 Implement DataTable, Tabs, Card, and PageHeader primitives
    - Write `src/components/ui/DataTable.tsx`: generic `columns: ColumnDef<T>[]` + `data: T[]`; sortable column headers with asc/desc state; optional pagination slot; accessible `<table>` with `scope` headers
    - Write `src/components/ui/Tabs.tsx`: controlled `activeTab`/`onChange` API; renders `<role="tablist">` and `<role="tab">` / `<role="tabpanel">` ARIA structure
    - Write `src/components/ui/Card.tsx`: composable card with `header`, `body`, `footer` slots; optional `onClick` for interactive cards
    - Write `src/components/ui/PageHeader.tsx`: `title`, `subtitle`, `actions` slot; renders `<h1>` with correct typographic token
    - Export all from barrel; barrel file is now complete
    - _Requirements: 1.2_

  - [ ]* 2.8 Write unit tests for DataTable, Tabs, Card, and PageHeader
    - Test sort state toggling, pagination slot rendering, ARIA row count for DataTable
    - Test tab switching, keyboard navigation (arrow keys), aria-selected for Tabs
    - Test slot rendering and onClick for Card; test title/subtitle/actions slot for PageHeader
    - Achieve ≥90% branch coverage each
    - _Requirements: 1.5, 14.6_

- [ ] 3. Auth store, ApiClient, and ProtectedRoute
  - [ ] 3.1 Implement Zustand authStore and JWT utilities
    - Create `src/store/authStore.ts` with Zustand slice: `token`, `setToken(token)`, `clearToken()`, `getDecodedToken()` (uses `jwt-decode`), `isExpired()`, `isNearExpiry()` (true when exp < now+60s)
    - Add `jwt-decode` to dependencies
    - _Requirements: 1.7, 1.8_

  - [ ] 3.2 Implement ApiClient with typed methods and 429 back-off
    - Create `src/services/ApiClient.ts` implementing all methods from the design interface
    - Add `Authorization: Bearer <token>` header injection from `authStore`
    - Implement `fetch` retry loop: on HTTP 429, wait `min(1 * 2^retryCount, 30_000) + random(0,1000)ms`; max 5 retries; throw after exhaustion
    - Implement HTTP 401 interceptor: clear token and redirect to `/login?redirect=<current path>` within 500ms
    - Implement HTTP 403 interceptor: fire error Toast
    - Add `subscribeAgentFeed(onMessage)` that opens a native `WebSocket` and returns a cleanup function
    - _Requirements: 1.7, 1.8, 15.6, 15.7_

  - [ ]* 3.3 Write property test for ApiClient 429 back-off (Property 23)
    - **Property 23: API client 429 back-off stays within bounds**
    - **Validates: Requirements 15.7**
    - Use `fc.integer({min:1, max:5})` for retry count n; assert delay satisfies `1 * 2^n + jitter ≤ 30_000ms` and no more than 5 retries occur
    - Co-locate at `src/services/__tests__/ApiClient.test.ts`


  - [ ] 3.4 Implement ProtectedRoute, useAuth hook, and token refresh logic
    - Create `src/hooks/useAuth.ts`: exposes `login(payload)`, `register(payload)`, `logout()`, `refreshIfNeeded()` — the last calls `ApiClient.refresh()` when `authStore.isNearExpiry()` is true; on refresh failure calls `authStore.clearToken()` and redirects within 500ms
    - Create a `ProtectedRoute` wrapper component in `src/components/ProtectedRoute.tsx`: reads `authStore`, calls `refreshIfNeeded()`, redirects to `/login?redirect=<pathname+search>` when unauthenticated/expired
    - _Requirements: 1.7, 1.8_

  - [ ]* 3.5 Write property tests for auth redirect and token refresh (Properties 1 and 2)
    - **Property 1: Auth redirect preserves original path**
    - **Validates: Requirements 1.7**
    - Use `fc.webPath()` generator; assert redirect URL contains `?redirect=<encoded path>` exactly
    - **Property 2: Token refresh triggers within the 60-second window**
    - **Validates: Requirements 1.8**
    - Use `fc.integer({min:1, max:59})` for seconds-to-expiry; assert refresh called; use `fc.integer({min:60, max:3600})` and assert no refresh called
    - Co-locate at `src/hooks/__tests__/useAuth.test.ts`

- [ ] 4. Authentication pages
  - [ ] 4.1 Implement Login and Register pages
    - Create `src/pages/login.tsx`: form with email + password fields using Input primitive; calls `useAuth.login()`; on success navigates to `?redirect=` path or `/`; on failure increments attempt counter; disables button for 60s with countdown after 5 failures
    - Create `src/pages/register.tsx`: form with full name, email, password fields; calls `useAuth.register()`; field-level validation errors within 100ms; on success navigates to `/`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 4.2 Implement Profile page and Admin panel
    - Create `src/pages/profile.tsx`: name (1–100 chars) and password (min 8 chars, blank = omit) form via `PUT /users/me`; API Keys section listing up to 20 keys with scope badges, creation form (name 1–64 chars, scope select), and revoke button that opens confirmation Modal before deletion
    - Create `src/pages/admin.tsx`: admin-only route (redirects to dashboard + "Access Denied" Toast for non-admin); DataTable of all users with `is_active` toggle and subscription tier column
    - _Requirements: 2.5, 2.6, 2.7, 2.8_


- [ ] 5. Main Dashboard
  - [ ] 5.1 Implement health polling KPI cards and service degradation Toasts
    - Create `src/components/dashboard/KpiCard.tsx`: shows service name, status badge, and Skeleton while loading; accepts `status: 'ok'|'degraded'|'unknown'` prop
    - In `src/pages/dashboard.tsx`: poll `GET /health` every 30 seconds via React Query `refetchInterval`; on fetch failure set all four cards to "Unknown"; track previous statuses in a ref and fire `"<ServiceName> degraded"` Toast (8s auto-dismiss) when any service transitions from `"ok"` to non-`"ok"`
    - _Requirements: 3.1, 3.2_

  - [ ] 5.2 Implement WebSocket agent feed with exponential back-off reconnect
    - Create `src/hooks/useAgentFeed.ts`: opens WebSocket at `/api/ws`; maintains event buffer capped at 50 items in reverse-chronological order; on disconnect, implements back-off: delay = `min(1 * 2^n, 30)` seconds, max 10 attempts; exposes `status: 'connected'|'reconnecting'|'lost'` state
    - Create `src/components/dashboard/AgentFeed.tsx`: renders the event list with timestamp (ISO → local time), agent name, and message; shows "Reconnecting…" banner during reconnect; shows "Connection lost — reload to retry" after 10 failed attempts
    - _Requirements: 3.3, 3.4_

  - [ ]* 5.3 Write property tests for agent feed (Properties 3 and 4)
    - **Property 3: WebSocket event feed is capped at 50 and reverse-sorted**
    - **Validates: Requirements 3.3**
    - Use `fc.array(fc.record({timestamp: fc.date(), ...}), {minLength:1, maxLength:500})`; assert output length ≤ 50 and timestamps are descending
    - **Property 4: WebSocket reconnect delay follows exponential back-off**
    - **Validates: Requirements 3.4**
    - Use `fc.integer({min:0, max:9})` for attempt n; assert delay = `min(1 * 2^n, 30)` (within 10% jitter)
    - Co-locate at `src/hooks/__tests__/useAgentFeed.test.ts`

  - [ ] 5.4 Implement Dashboard KPI metric cards, Chart.js outreach chart, and Build Terminal
    - Add four KPI cards sourcing `GET /companies` (total), `GET /deployments?status=active`, `GET /api/leads?status=pipeline`, `GET /api/outreach?period=week`; each shows Skeleton while in-flight
    - Create `src/components/dashboard/OutreachChart.tsx`: Chart.js line chart of daily email counts for trailing 30 days, computed client-side from `GET /api/leads` + `GET /api/outreach` responses; labelled axes and legend
    - Create `src/components/dashboard/BuildTerminal.tsx`: "Build Sprint" form; on `POST /api/build` HTTP 200, opens SSE stream via `src/hooks/useBuildStream.ts` and renders lines until `event: done` or stream close; on premature close show "Stream ended unexpectedly"
    - Create `src/hooks/useBuildStream.ts`: manages `EventSource` lifecycle; returns `{lines, status}`
    - _Requirements: 3.5, 3.6, 3.7_

  - [ ]* 5.5 Write Vitest unit tests for Dashboard data-fetching hooks
    - Mock ApiClient; assert loading (Skeleton visible), success (data rendered), and error (error card with Retry) states for each hook
    - _Requirements: 3.8_


- [ ] 6. Checkpoint — core scaffold complete
  - Ensure `tsc --noEmit` passes with zero errors; `vitest --run --coverage` meets 90% thresholds on implemented files; no `@ts-ignore` in production source. Ask the user if questions arise.

- [ ] 7. Company, Deployment, and Tenant management pages
  - [ ] 7.1 Implement Companies list and creation form
    - Create `src/pages/companies/index.tsx`: DataTable with server-side pagination (page size 25), status badge filter using Badge primitive, 300ms debounced search input; creation form requiring `name` (1–200), `domain` (hostname regex), `status` select — field-level validation before API call
    - On `POST /companies` 409 response: show field-level "Domain already registered" error on domain field; on other non-2xx: show Toast with server message leaving form intact; on empty list: render accessible empty-state with CTA
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.11, 4.12_

  - [ ] 7.2 Implement Company Detail, Deployments list, and Tenant list pages
    - Create `src/pages/companies/[id].tsx`: displays name, domain, status badge, created date, tickets list, deployment history, workflow status; on 404 renders "Not Found" with back-navigation
    - Create `src/pages/deployments.tsx`: sortable DataTable (name, status, created); status filter; slide-over panel showing up to 200 lines of deployment logs; optimistic action buttons (start/stop/restart set badge immediately, revert on error within 2s timeout); error state with Retry; empty state; Skeleton on load
    - Create `src/pages/tenants.tsx`: DataTable of tenants; inline registration form; on `POST /tenants` failure show inline error without clearing inputs; error state with Retry; empty state; Skeleton on load
    - _Requirements: 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12_

  - [ ]* 7.3 Write property test for optimistic deployment action revert (Property 6)
    - **Property 6: Optimistic deployment action reverts on error**
    - **Validates: Requirements 4.8**
    - Use `fc.record()` for deployment + `fc.constantFrom('start','stop','restart')` for action; mock API error; assert badge reverts to pre-action value and error Toast fires
    - Co-locate at `src/pages/__tests__/deployments.test.tsx`


- [ ] 8. Ticket Kanban board and Workflow Builder
  - [ ] 8.1 Implement Ticket Kanban board
    - Create `src/pages/tickets.tsx`: fetch `GET /tickets`; render four-column Kanban (OPEN, IN_PROGRESS, RESOLVED, CLOSED) using HTML5 drag-and-drop or a lightweight DnD lib; optimistic column move + `PUT /tickets/:id`; revert with error Toast on API error within 5 seconds
    - Create Ticket Detail Modal: title, description, priority Badge, assignee, due date, SLA countdown (warn style when ≤24h), comment thread, history log
    - Error state with Retry when `GET /tickets` fails
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 8.2 Write integration tests for Kanban drag interactions
    - Use `@testing-library/user-event` pointer events to simulate drag; assert optimistic update, API call payload, and revert-on-error behaviour
    - _Requirements: 5.8_

  - [ ] 8.3 Implement Workflow Builder canvas and list page
    - Install `reactflow` (MIT); create `src/components/workflows/WorkflowCanvas.tsx`: drag agent node types onto canvas, directed edge connections, side panel `NodeConfigPanel.tsx` for parameter editing
    - Validate on save: zero nodes → show validation error and block; valid → serialise to `steps_json` and call `POST /workflows`
    - Highlight executing step node with pulsing border within ≤2s of WS event; poll `GET /workflows/:id` every 10s when WS disconnects during active run; "Live updates paused" indicator when WS drops
    - Create `src/pages/workflows/index.tsx`: list with status badges, timestamps, Launch button; error Toast on trigger failure
    - Create `src/pages/workflows/builder.tsx`: embeds WorkflowCanvas
    - _Requirements: 5.4, 5.5, 5.6, 5.7, 5.9_

  - [ ]* 8.4 Write property test for workflow graph serialisation round-trip (Property 7)
    - **Property 7: Workflow graph serialisation round-trip**
    - **Validates: Requirements 5.5**
    - Use `fc.array(fc.record({id: fc.uuid(), ...}), {minLength:1, maxLength:50})` for nodes + edges; serialise to `steps_json`, deserialise, assert structural equivalence (same IDs, edges, params)
    - Co-locate at `src/components/workflows/__tests__/WorkflowCanvas.test.ts`

  - [ ]* 8.5 Write integration tests for Workflow Builder node operations
    - Use `@testing-library/user-event`; assert node add, edge connect, param edit, save blocked on empty canvas, successful serialisation
    - _Requirements: 5.8_


- [ ] 9. Analytics page and shared lib utilities
  - [ ] 9.1 Implement date-range and CSV export utilities
    - Create `src/lib/dateRange.ts`: `filterByDateRange(data, start, end)` and `buildDailyPoints(data, start, end)` — one data point per calendar day, values summed per day across all source records
    - Create `src/lib/csvExport.ts`: `exportCsv(rows, filename)` — generates a `Blob` download of `analytics_export_YYYY-MM-DD.csv` with headers derived from object keys; no server call
    - _Requirements: 6.1, 6.5_

  - [ ]* 9.2 Write property tests for CSV export and chart dataset computation (Properties 8 and 9)
    - **Property 8: CSV export rows match date-filtered data exactly**
    - **Validates: Requirements 6.5**
    - Use `fc.array()` of dated records + `fc.date()` range pairs; assert bijection between CSV rows and `filterByDateRange` output
    - **Property 9: Chart datasets are correctly computed from API responses**
    - **Validates: Requirements 6.7, 6.1, 6.2**
    - Use `fc.array()` of usage/leads/outreach records; assert one data point per calendar day, values equal sum of that day's records
    - Co-locate at `src/lib/__tests__/csvExport.test.ts` and `src/lib/__tests__/dateRange.test.ts`

  - [ ] 9.3 Implement Analytics page
    - Create `src/pages/analytics.tsx`: date-range picker (default trailing 30 days, max 365 days); sources `GET /api/usage`, `GET /api/leads`, `GET /api/outreach`; combine into Chart.js charts for builds, deployments, leads, emails, open rate, reply rate
    - Per-source error states with Retry (other charts unaffected); refetch all charts within 500ms on date range change
    - Sortable DataTable beneath each chart (ascending by date default; click header to toggle asc/desc)
    - CSV export button triggering `exportCsv` with date-filtered data (no server call)
    - Admin-only panels from `GET /admin/stats` with isolated error state
    - Snapshot tests for chart dataset computation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 9.4 Write Vitest snapshot tests for chart rendering functions
    - Snapshot-test `OutreachChart`, `FunnelChart`, and Analytics chart datasets against mock API responses
    - _Requirements: 6.7_


- [ ] 10. Lead Manager CRM
  - [ ] 10.1 Implement merge-field interpolation and lead dedup utilities
    - Create `src/lib/mergeFields.ts`: `renderTemplate(template, prospect)` — substitutes `{{first_name}}`, `{{last_name}}`, `{{company}}`, `{{website}}` from prospect record; null/empty fields become empty strings; no raw `{{token}}` survives
    - Create `src/lib/leadDedup.ts`: `deduplicateLeads(leads)` — for display purposes, collapses leads sharing non-null email to single entry; null-email leads are always retained as distinct rows
    - _Requirements: 10.3_

  - [ ]* 10.2 Write property tests for merge-field substitution and lead dedup (Properties 14 and 16)
    - **Property 16: Merge-field substitution leaves no raw tokens**
    - **Validates: Requirements 10.3**
    - Use `fc.record()` with nullable string fields + arbitrary template; assert output matches `/\{\{[a-z_]+\}\}/` → 0 matches
    - **Property 14 (frontend dedup display logic)**
    - Use `fc.array()` of leads with nullable email; assert unique non-null email → one display row; null emails all retained
    - Co-locate at `src/lib/__tests__/mergeFields.test.ts` and `src/lib/__tests__/leadDedup.test.ts`

  - [ ] 10.3 Implement Lead list, Lead Detail slide-over, and Bulk Actions toolbar
    - Create `src/components/leads/LeadTable.tsx`: paginated DataTable (page size 25, columns: Company, Name, Email, Status badge, Created, Actions); multi-column sort; 300ms debounced global search sending `GET /api/leads?q=...&sort=...&page=...`; checkbox selection for bulk actions
    - Create `src/components/leads/LeadDetail.tsx`: slide-over panel with all metadata, outreach sequence history, "Enrich Lead" button (spinner until response; always refresh lead via `GET /api/leads/:id` after enrichment; error Toast if enrichment fails but refresh still runs)
    - Create `src/components/leads/BulkActionsToolbar.tsx`: appears when ≥1 checkbox selected; Add to Sequence (opens Sequence Modal), Export CSV, Change Status, Delete (confirmation Modal before API call)
    - Create `src/pages/leads.tsx`: mounts LeadTable + BulkActionsToolbar; route handles `?view=pipeline`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ] 10.4 Implement Lead Pipeline Kanban view
    - Create `src/components/leads/PipelineBoard.tsx`: Kanban grouped by lead status; same DnD pattern as Tickets; optimistic column move + `PUT /api/leads/:id`; revert with error Toast on failure
    - Toggle between list and pipeline views at `/leads?view=pipeline`
    - _Requirements: 7.7_

  - [ ]* 10.5 Write Vitest tests for Lead Manager (happy path, empty, error, bulk)
    - Cover: lead list loading/success/error/empty states, enrich button loading + refresh, bulk delete confirmation, Add to Sequence modal with empty sequences state, pipeline board optimistic move + revert
    - _Requirements: 7.8_


- [ ] 11. Outreach Hub UI
  - [ ] 11.1 Implement Campaign Composer and Campaigns list
    - Create `src/components/outreach/CampaignComposer.tsx`: subject (1–998 chars), recipients (multiline/CSV paste → parse to ≤500 valid emails), Tiptap rich-text body (non-empty), scheduled datetime (must be future) — field-level validation before any API call
    - On `POST /api/outreach/campaign` 2xx: queued confirmation Toast (8s), prepend campaign to list with status "queued"; on non-2xx: error Toast, preserve form data, do NOT add to list
    - Install `@tiptap/react` and `@tiptap/starter-kit` (MIT)
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 11.2 Write property test for campaign validation (Property 10)
    - **Property 10: Campaign validation blocks invalid input combinations**
    - **Validates: Requirements 8.2**
    - Use `fc.record()` with generators for subject length, recipient count/validity, body presence, datetime (past/future); assert `validateCampaignForm` returns `valid=true` iff all constraints satisfied
    - Co-locate at `src/components/outreach/__tests__/CampaignComposer.test.ts`

  - [ ] 11.3 Implement Sequence Builder
    - Create `src/components/outreach/SequenceBuilder.tsx`: add/edit/remove 1–10 steps; each step requires `delay_days` (int 0–365), `subject_template` (1–998 chars), `body_template` (1–100,000 chars) with `{{first_name}}`, `{{company}}` merge field previews; block save on any validation failure with field-level errors
    - _Requirements: 8.5, 8.6_

  - [ ]* 11.4 Write property test for sequence step validation (Property 12)
    - **Property 12: Sequence step validation rejects out-of-bounds values**
    - **Validates: Requirements 8.6**
    - Use `fc.record()` with `fc.integer()` for delay_days (including out-of-range), `fc.string()` of varying length for templates; assert `validateStep` returns `valid=false` iff delay_days ∉ [0,365] or subject empty/> 998 or body empty/> 100,000 chars

  - [ ] 11.5 Implement Inbox list and browser Notification hook
    - Create `src/components/outreach/InboxList.tsx`: fetch `GET /api/outreach/inbox`; colour-coded classification badges (green/Interested, red/Not Interested, grey/Auto-Reply, orange/Bounce); Interested replies sorted to top, then by `received_at` desc within each group; error state with Retry
    - Create `src/hooks/useNotifications.ts`: requests Notifications API permission; on `interested` reply received via WebSocket fires `new Notification("New interested reply", {body: senderEmail})`
    - _Requirements: 8.7, 8.8, 8.9_

  - [ ]* 11.6 Write property test for inbox reply sort (Property 11)
    - **Property 11: Inbox reply sort — interested replies always at top**
    - **Validates: Requirements 8.8**
    - Use `fc.array()` of reply records with random `fc.constantFrom('interested','not_interested','auto_reply','bounce')` classifications; assert after sort, all `interested` precede any other classification, and within each group descending by `received_at`
    - Co-locate at `src/components/outreach/__tests__/InboxList.test.ts`

  - [ ] 11.7 Implement Outreach Reports funnel chart and wire Outreach Hub routing
    - Create `src/components/outreach/FunnelChart.tsx`: horizontal Chart.js bar/funnel chart with stages Prospects → Contacted → Opened → Replied → Interested; empty-state message when data is empty array; error state with Retry
    - Create `src/pages/outreach/index.tsx`: sub-navigation Tabs for Campaigns / Sequences / Inbox / Reports; default to Campaigns; lazy-load each sub-view
    - _Requirements: 8.10_

  - [ ]* 11.8 Write Vitest tests for all Outreach Hub components (≥90% branch coverage)
    - Campaign: submit success, submit error, form preservation; Sequence: step validation, 1-step and 10-step limits; Inbox: classification badge colours, Interested-first ordering; Funnel: data computation, empty state, error state
    - _Requirements: 8.11_


- [ ] 12. Checkpoint — frontend feature-complete
  - `vitest --run --coverage` green; `tsc --noEmit` clean; all route modules exist under `src/pages/`; all Component Library primitives exported from barrel. Ask the user if questions arise.

- [ ] 13. Backend: SQLAlchemy models and Alembic migration
  - [ ] 13.1 Create new SQLAlchemy models for outreach pipeline
    - Create `backend/db/models_outreach.py` with five models: `Sequence`, `SequenceEnrollment`, `SequenceStepLog`, `OutreachDailyMetrics`, `LeadTimeline` — using exact schema from design document including UniqueConstraints and ForeignKeys
    - Add new columns to existing `Lead` model in `backend/db/models.py` via migration: `website`, `linkedin_url`, `intent_score`, `needs_review`, `email_invalid`
    - Import `models_outreach` in `alembic/env.py` so Alembic detects the new tables
    - _Requirements: 9.1, 9.5, 10.1, 11.1, 12.6, 13.2_

  - [ ] 13.2 Generate and validate Alembic migration
    - Run `alembic revision --autogenerate -m "outreach_pipeline_models"` and review the generated script
    - Ensure migration is reversible (downgrade removes new tables and columns without data loss on existing tables)
    - Add migration to `alembic/versions/`
    - _Requirements: 9.5, 10.1_


- [ ] 14. Enrichment_Agent
  - [ ] 14.1 Implement EnrichmentAgent class
    - Create `agents/outreach/enrichment_agent.py` with `EnrichmentAgent` class per design interface
    - `run(niche_descriptor)`: validate input — at least 1 non-whitespace char, at most 500 non-whitespace chars; raise descriptive `ValueError` outside bounds before any I/O
    - `_crawl_prospect(url)`: HTTP crawl with `requests` + `BeautifulSoup4`, cap at 5 pages per prospect; 10-second timeout per request
    - `_extract_with_ollama(html, niche)`: call local Ollama with 10-second timeout; on `TimeoutError` or `ConnectionRefusedError` log WARNING and raise to trigger fallback
    - `_extract_with_regex(html)`: fallback regex extraction; if no usable fields found return empty result (caller skips record)
    - `_compute_intent_score(signals)`: additive scoring (job_posting_match +30, email_resolved +20, homepage_200 +20, name_in_results +30); cap at 100
    - _Requirements: 9.1, 9.3, 9.4, 9.7_

  - [ ] 14.2 Implement prospect persistence and deduplication in EnrichmentAgent
    - In `EnrichmentAgent.run()`: for each discovered Prospect call `db.create_lead()` with dedup logic — if non-null email already exists in `leads`, UPDATE company name, contact name, website, linkedin_url, intent_score; if email is null, always INSERT as new record
    - Set `needs_review = True` when email is null
    - Publish `prospect_discovered` event to `EventBus` after successful persist
    - _Requirements: 9.2, 9.5, 9.6_

  - [ ] 14.3 Register EnrichmentAgent as Celery task
    - Create `agents/outreach/tasks.py`: define `@app.task(soft_time_limit=300, time_limit=360) def enrich_prospects(niche_descriptor: str)`; instantiate `EnrichmentAgent` and call `run()`; wrap top-level in `try/except` logging unhandled exceptions without re-raising
    - Register task in Celery Beat schedule for on-demand triggering
    - _Requirements: 9.8_

  - [ ]* 14.4 Write Pytest unit tests for EnrichmentAgent (≥90% branch coverage)
    - Mock Ollama client, `requests.get`, SQLAlchemy session
    - Cover: valid input, too-short input, too-long input (all whitespace), Ollama happy path, Ollama timeout → regex fallback, regex yielding no fields → record skipped, dedup update vs insert, null-email always-insert, intent score boundary (all signals on = 100, each signal individually)
    - _Requirements: 9.9_

  - [ ]* 14.5 Write Hypothesis property tests for EnrichmentAgent (Properties 13, 14, 15)
    - **Property 13: Enrichment_Agent input validation**
    - **Validates: Requirements 9.1**
    - Use `st.text()` with varying non-whitespace char counts; assert `ValueError` iff < 1 or > 500 non-whitespace chars
    - **Property 14: Prospect deduplication by email**
    - **Validates: Requirements 9.5, 9.6**
    - Use `st.lists(st.builds(Prospect, ...))` with shared emails; assert one row per unique non-null email, null emails each create new row
    - **Property 15: Intent score is additive and capped at 100**
    - **Validates: Requirements 9.7**
    - Use `st.frozensets(st.sampled_from(['job_post','email','homepage','name']))`; assert score = `min(sum_bonuses, 100)`
    - Co-locate at `tests/agents/test_enrichment_agent.py`


- [ ] 15. Sequencer_Agent
  - [ ] 15.1 Implement SequencerAgent class
    - Create `agents/outreach/sequencer_agent.py` with `SequencerAgent` class per design interface
    - `create_sequence(payload)`: validate `name` (1–255 chars), `steps` (1–10 entries, each `delay_days` 0–365, non-empty `subject_template`/`body_template`), `status` in allowed values; persist `Sequence` to DB
    - `enroll_prospect(lead_id, sequence_id)`: check for existing active enrollment (same lead+sequence); if exists raise descriptive error leaving existing enrollment unchanged; else create `SequenceEnrollment` with `current_step=0`
    - `render_template(template, prospect)`: substitute `{{first_name}}`, `{{last_name}}`, `{{company}}`, `{{website}}`; null/empty → empty string; ensure no raw `{{token}}` in output
    - `process_due_steps()`: query `SequenceEnrollment` rows where scheduled send time ≤ now; compute scheduled time as `enrolled_at + sum(delay_days for steps 0..current_step)`; call `EmailTools.send_email()`; on success log to `SequenceStepLog(outcome='sent')` and advance `current_step`; on all-retries-exhausted failure log `outcome='failed'`, set enrollment `status='paused'`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 15.2 Implement Sequencer reply-halt and Celery Beat task
    - Subscribe `SequencerAgent` to `reply_received` event bus signal; on receipt set matching enrollment `status='replied'` and halt remaining steps
    - Register `@app.task def process_due_sequence_steps()` in `agents/outreach/tasks.py` with Celery Beat schedule every 5 minutes
    - _Requirements: 10.6, 10.7_

  - [ ]* 15.3 Write Pytest unit tests for SequencerAgent (≥90% branch coverage)
    - Mock `EmailTools.send_email`, SQLAlchemy session, EventBus
    - Cover: create sequence, duplicate enrollment rejection, render_template with all null fields, step scheduling arithmetic, email send success, email send failure → paused enrollment, reply-halt stops further steps
    - _Requirements: 10.8_

  - [ ]* 15.4 Write Hypothesis property tests for SequencerAgent (Properties 16 and 17)
    - **Property 16: Merge-field substitution leaves no raw tokens (backend)**
    - **Validates: Requirements 10.3**
    - Use `st.text()` templates with arbitrary merge-field subsets + `st.builds(Prospect)` with nullable fields; assert output contains no `/\{\{[a-z_]+\}\}/`
    - **Property 17: Sequence step scheduled time arithmetic**
    - **Validates: Requirements 10.4**
    - Use `st.datetimes()` for enrolled_at + `st.lists(st.integers(0, 365))` for delay_days; assert step k scheduled at `enrolled_at + timedelta(days=sum(d₀..dₖ))`
    - Co-locate at `tests/agents/test_sequencer_agent.py`


- [ ] 16. Reply_Handler_Agent
  - [ ] 16.1 Implement ReplyHandlerAgent class
    - Create `agents/outreach/reply_handler_agent.py` with `ReplyHandlerAgent` class per design interface
    - `poll_inbox()`: connect to IMAP via `imaplib.IMAP4_SSL` using env vars `IMAP_SERVER`, `IMAP_USER`, `IMAP_PASS`; fetch UNSEEN messages; for each: extract sender, subject, up to 10,000 chars of body; check `processed_events` to skip already-seen UIDs; call `classify_reply()`; dispatch downstream actions; only store UID in `processed_events` AFTER all actions succeed; if any action fails do not store UID; catch `imaplib.IMAP4.error`, `socket.timeout`, `OSError` at top level — log ERROR and return gracefully
    - `classify_reply(email)`: try `_classify_with_ollama()` with 10-second timeout; on Ollama unavailability fall back to `_classify_with_heuristics()`; always return one of `{'interested','not_interested','auto_reply','bounce'}`; never raise unhandled exception
    - `_classify_with_heuristics(email)`: implement normative rules in order — bounce (Return-Path `<>` or subject regex), auto_reply (body keywords), not_interested (body keywords), default interested
    - Handle reply outcomes: `interested` → update enrollment to `replied_interested`, create high-priority Ticket, publish WS `reply_classified` event; `not_interested` → enrollment `replied_uninterested`, publish `reply_received` to event bus; `auto_reply` → enrollment `paused`; `bounce` → mark email invalid, enrollment `failed`, write `processed_events(event_type='bounce_logged')`
    - On unmatched sender: store UID, log INFO with sender, continue
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9_

  - [ ] 16.2 Register Reply_Handler_Agent Celery Beat task
    - Register `@app.task def check_inbox_replies()` in `agents/outreach/tasks.py` with Celery Beat schedule every 5 minutes
    - _Requirements: 11.1_

  - [ ]* 16.3 Write Pytest unit tests for ReplyHandlerAgent (≥90% branch coverage)
    - Mock `imaplib.IMAP4_SSL`, Ollama client, SQLAlchemy session, EventBus
    - Cover: IMAP connection failure (graceful exit), Ollama unavailable → heuristic fallback, each heuristic rule, each classification downstream action, UID stored only after full success, UID not stored on partial failure, unmatched sender handling
    - _Requirements: 11.10_

  - [ ]* 16.4 Write Hypothesis property tests for ReplyHandlerAgent (Properties 18 and 19)
    - **Property 18: Reply classification output is always a valid label**
    - **Validates: Requirements 11.2**
    - Use `st.builds(EmailMessage, ...)` with arbitrary sender/subject/body; assert `classify_reply()` returns one of the four valid labels and never raises
    - **Property 19: IMAP UID stored only after all downstream actions succeed**
    - **Validates: Requirements 11.7**
    - Use `st.booleans()` for each downstream action (enrollment update, ticket creation, event bus publish) success/fail; assert UID in `processed_events` iff all three succeed
    - Co-locate at `tests/agents/test_reply_handler_agent.py`


- [ ] 17. CRM_Sync_Agent
  - [ ] 17.1 Implement CRMSyncAgent state machine and event handlers
    - Create `agents/outreach/crm_sync_agent.py` with `CRMSyncAgent` class per design interface
    - `handle_prospect_discovered(payload)`: upsert lead with status `NEW`; if later-stage events arrive first, buffer up to 50 events per lead and replay after `prospect_discovered` is processed
    - `handle_sequence_enrolled(payload)`: update Lead status to `CONTACTED`; if Lead not found log WARNING and discard; write `LeadTimeline` entry
    - `handle_reply_received(payload)` (classification=`interested`): atomically update Lead to `QUALIFIED` + create high-priority Ticket in single `Session.begin()` context; on transaction failure rollback, log ERROR, discard event without partial side effects
    - `handle_sequence_completed(payload)` (has_reply=false): update Lead to `COLD`; if Lead not found log WARNING and discard
    - For all handlers: if `sequence_enrolled`/`email_sent`/`sequence_completed` references unknown Lead ID with no buffered `prospect_discovered`, log WARNING with lead ID and discard
    - Subscribe all handlers to `backend.services.event_bus` on agent startup
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.7, 12.8_

  - [ ] 17.2 Implement lead timeline endpoint
    - Add `GET /api/leads/:id/timeline` FastAPI route in `backend/api/crm_sync.py`; query `LeadTimeline` by `lead_id` ordered by `occurred_at` ascending; return JSON array of `{from_status, to_status, triggered_by, occurred_at}`; return HTTP 404 if lead not found
    - _Requirements: 12.6_

  - [ ]* 17.3 Write Pytest unit tests for CRMSyncAgent (≥90% branch coverage)
    - Mock SQLAlchemy session, EventBus; assert correct state transitions for each event type; assert rollback on transaction failure; assert buffering of out-of-order events; assert 50-event buffer cap
    - _Requirements: 12.7_

  - [ ]* 17.4 Write Hypothesis property tests for CRM state machine (Property 20)
    - **Property 20: CRM state machine transitions are deterministic**
    - **Validates: Requirements 12.2, 12.3, 12.4, 12.5**
    - Use `st.sampled_from(LeadStatus)` for current status + `st.sampled_from(EventType)` for event; assert output status matches transition table exactly
    - Co-locate at `tests/agents/test_crm_sync_agent.py`


- [ ] 18. Reporting_Agent
  - [ ] 18.1 Implement ReportingAgent class and daily metrics endpoint
    - Create `agents/outreach/reporting_agent.py` with `ReportingAgent` class per design interface
    - `generate_daily_report(date)`: aggregate for the preceding UTC calendar day — `prospects_discovered` (count of leads inserted that day), `emails_sent` (SequenceStepLog with outcome=`sent`), `open_rate` (opens/sent where opens_tracked=true; null if no trackable sends), `reply_rate` (replied enrollments/sent; null if sent=0), `interested_count`, `bounce_rate`
    - `_compute_metrics(day)`: isolated computation function for unit testing
    - Upsert each metric to `OutreachDailyMetrics` by (date, metric_name) — ensures idempotency on repeated runs
    - Register `@app.task def generate_daily_outreach_report()` scheduled at 01:00 UTC daily
    - Add `GET /api/outreach/reports/daily` FastAPI route accepting `start_date` / `end_date` ISO 8601 params; return HTTP 400 with `{"error": "..."}` if params missing, malformed, or start > end; return HTTP 200 empty array when no data
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [ ]* 18.2 Write Pytest unit tests for ReportingAgent (≥90% branch coverage)
    - Mock SQLAlchemy session; cover: all six metric computations, null cases (no trackable sends, sent=0), upsert idempotency (run twice, assert no duplicate rows)
    - _Requirements: 13.7_

  - [ ]* 18.3 Write Hypothesis property tests for ReportingAgent (Properties 21 and 22)
    - **Property 21: Reporting metrics arithmetic correctness**
    - **Validates: Requirements 13.1**
    - Use `st.integers(min_value=0)` for sent/opens/replies/bounces; assert `open_rate = opens/sent` (null when no trackable sends), `reply_rate = replies/sent` (null when sent=0)
    - **Property 22: Reporting task idempotency (upsert)**
    - **Validates: Requirements 13.6**
    - Use `st.dates()` + random metric data; run `generate_daily_report(date)` twice; assert identical row set, no count increase
    - Co-locate at `tests/agents/test_reporting_agent.py`


- [ ] 19. New FastAPI endpoints for outreach pipeline
  - [ ] 19.1 Implement Sequence and Enrollment API endpoints
    - Create `backend/api/sequencer.py` FastAPI router:
      - `POST /api/outreach/sequence`: create sequence; validate payload; return 201 with created Sequence JSON
      - `GET /api/outreach/sequences`: list all sequences with step count and enrolled prospect count; return 200
      - `POST /api/outreach/sequence/enroll`: enroll lead IDs in sequence ID; reject duplicate active enrollments with 409; return 200 with enrollment summary
    - Register router in `backend/main.py`
    - _Requirements: 10.1, 10.2_

  - [ ] 19.2 Implement Inbox, Reports, and extended Outreach/Leads endpoints
    - Create `backend/api/reply_handler.py` router: `GET /api/outreach/inbox` — list classified replies with all InboxReply fields; return 200 JSON array
    - Create `backend/api/reporting.py` router: `GET /api/outreach/reports/daily` — already covered in task 18.1; mount here
    - Extend `backend/api/outreach.py`: add `GET /api/outreach?period=week` handler returning weekly email count for Dashboard KPI
    - Extend `backend/api/leads.py`: ensure `GET /api/leads/:id/timeline` is registered (implemented in task 17.2)
    - _Requirements: 8.5, 8.7, 3.5, 12.6, 13.4_

  - [ ] 19.3 Wire all outreach agents into application startup
    - In `backend/main.py` or the Celery app entry point: register CRMSyncAgent event bus subscriptions on startup; configure Celery Beat schedule entries for `enrich_prospects` (on-demand), `process_due_sequence_steps` (every 5 min), `check_inbox_replies` (every 5 min), `generate_daily_outreach_report` (01:00 UTC daily)
    - _Requirements: 9.8, 10.7, 11.1, 13.3_

  - [ ]* 19.4 Write integration smoke test for outreach pipeline
    - Create `tests/agents/test_outreach_integration.py`: use in-memory SQLite via `SessionLocal` override; run full happy-path flow: enrich → enroll → process step → classify reply → CRM sync → report; assert final DB state without mocking ORM layer
    - _Requirements: 14.8_


- [ ] 20. Checkpoint — backend feature-complete
  - `pytest --cov --cov-fail-under=90` green; Alembic migration applies and reverses cleanly; all new FastAPI endpoints return correct status codes against in-memory DB. Ask the user if questions arise.

- [ ] 21. Hypothesis email normalisation property test
  - [ ] 21.1 Write Hypothesis property test for email normalisation
    - Create `tests/services/test_email_normaliser.py`
    - Use `hypothesis.strategies.emails()` to verify `normalise(normalise(x)) == normalise(x)` (idempotency: lowercase + strip whitespace)
    - Minimum 100 examples
    - _Requirements: 14.8_

- [ ] 22. CI pipeline updates
  - [ ] 22.1 Add frontend-test job to GitHub Actions CI workflow
    - In `.github/workflows/ci.yml`, add `frontend-test` job: `npm ci`, `vitest --run --coverage`; fail if coverage thresholds not met; upload `coverage/` directory as artifact with 30-day retention; add step that fails if any `.tsx` under `src/components/` lacks a co-located `__tests__/<ComponentName>.test.tsx`
    - _Requirements: 14.3, 14.6_

  - [ ] 22.2 Update backend-test job in GitHub Actions CI workflow
    - Ensure `backend-test` job runs `pytest --cov --cov-fail-under=90`; uploads coverage report artifact with 30-day retention; add a check step that fails if any new `.py` under `agents/` or `backend/services/` lacks a corresponding `tests/agents/test_<filename>.py` or `tests/services/test_<filename>.py`
    - _Requirements: 14.4, 14.5_

  - [ ] 22.3 Add bundle size check CI step
    - After `vite build` step in `frontend-test` job, add a step that measures gzip size of all synchronously loaded entry and shared vendor chunks for the Dashboard route and fails with a descriptive message if total exceeds 400 KB
    - Add `rollupOptions.output.manualChunks` to `vite.config.ts` to enforce code-splitting: each page under `src/pages/` loaded via `React.lazy()` + `Suspense` in `App.tsx`
    - _Requirements: 15.4, 15.5_

  - [ ] 22.4 Add Lighthouse CI job
    - Add `lighthouse-ci` job to `.github/workflows/performance.yml` (or extend `ci.yml`): start built frontend with a static server, run Lighthouse against Dashboard route in simulated Moto G4 / Fast 3G; assert Performance category ≥ 85; upload Lighthouse report as artifact
    - _Requirements: 15.3_

- [ ] 23. Final checkpoint — all quality gates green
  - `tsc --noEmit` zero errors; `vitest --run --coverage` all thresholds ≥ 90%; `pytest --cov --cov-fail-under=90` passes; bundle size ≤ 400 KB gzip; Lighthouse Performance ≥ 85; all 23 correctness properties tested. Ask the user if questions arise.


---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP, but property-based tests are strongly recommended before shipping given the 23 correctness properties in the design.
- Every task references specific requirements for full traceability.
- The three checkpoints (tasks 6, 12, 20) provide natural pause points to verify incremental progress.
- Backend agents (tasks 14–18) are independent of each other and can be implemented in any order after the SQLAlchemy models (task 13) are in place.
- Frontend feature pages (tasks 7–11) are independent of each other after the scaffold (tasks 1–5) is complete.
- All fast-check property tests are tagged with `// Feature: swarm-enterprise-frontend-outreach, Property N: <text>` per the design spec.
- All Hypothesis property tests are tagged with `# Feature: swarm-enterprise-frontend-outreach, Property N: <text>` per the design spec.
- `React.lazy()` + `Suspense` must wrap all page components in `App.tsx` to satisfy the code-splitting requirement (Requirement 15.5) before the bundle size CI check is added.
- The Tiptap rich-text editor (`@tiptap/react`, `@tiptap/starter-kit`) is MIT-licensed and satisfies the FOSS-only constraint.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "13.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "1.5", "13.2"] },
    { "id": 2, "tasks": ["2.1", "2.3", "2.5", "2.7", "3.1"] },
    { "id": 3, "tasks": ["2.2", "2.4", "2.6", "2.8", "3.2"] },
    { "id": 4, "tasks": ["3.3", "3.4", "14.1", "15.1", "16.1", "17.1", "18.1"] },
    { "id": 5, "tasks": ["3.5", "4.1", "4.2", "14.2", "15.2", "16.2", "17.2", "18.2"] },
    { "id": 6, "tasks": ["5.1", "5.2", "9.1", "10.1", "11.1", "14.3", "14.4", "15.3", "16.3", "17.3", "18.3", "19.1", "19.2"] },
    { "id": 7, "tasks": ["5.3", "5.4", "7.1", "8.1", "8.3", "9.2", "10.2", "11.2", "11.3", "14.5", "15.4", "16.4", "17.4", "19.3"] },
    { "id": 8, "tasks": ["5.5", "7.2", "7.3", "8.2", "8.4", "8.5", "9.3", "10.3", "11.4", "11.5", "19.4", "21.1"] },
    { "id": 9, "tasks": ["9.4", "10.4", "10.5", "11.6", "11.7"] },
    { "id": 10, "tasks": ["11.8", "22.1", "22.2"] },
    { "id": 11, "tasks": ["22.3", "22.4"] }
  ]
}
```
