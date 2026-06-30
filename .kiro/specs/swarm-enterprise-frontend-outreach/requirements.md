# Requirements Document

## Introduction

This feature replaces the current single-file static HTML dashboard with a production-grade React/TypeScript SPA, and simultaneously elevates the cold outreach and marketing automation stack from skeleton code to a fully autonomous, end-to-end pipeline. Both areas target the same quality bar as the existing backend (88/100, 92% test coverage) and are constrained to FOSS/self-hosted dependencies only.

The two major deliverable areas are:

1. **Frontend SPA** — A visually stunning, fully functional React 18 + TypeScript + Vite application covering dashboards, project management, analytics, admin, workflow builder, and lead management — each with co-located test files.
2. **Cold Outreach & Marketing Automation Stack** — Fully autonomous prospect discovery, enrichment, multi-step email sequencing, reply handling, CRM updates, and reporting agents — each with co-located test files.

---

## Glossary

- **SPA**: Single-Page Application built with React 18, TypeScript, and Vite.
- **Dashboard**: The primary authenticated view showing system KPIs, live agent activity, and quick actions.
- **Workflow_Builder**: The drag-and-drop visual editor for composing multi-step automation workflows.
- **Lead_Manager**: The CRM-style UI module for viewing, filtering, enriching, and actioning leads.
- **Outreach_Pipeline**: The end-to-end automated system for prospect discovery, email sequencing, reply detection, and CRM sync.
- **Prospect**: A company or individual identified as a high-intent sales target.
- **Sequence**: An ordered set of timed outreach touches (emails, follow-ups) associated with one Prospect.
- **Enrichment_Agent**: The agent responsible for augmenting raw Prospect records with contact details, social profiles, and intent signals.
- **Sequencer_Agent**: The agent responsible for generating, scheduling, and sending personalised emails for each Sequence step.
- **Reply_Handler_Agent**: The agent that monitors inboxes, classifies incoming replies, and routes them to the appropriate action.
- **CRM_Sync_Agent**: The agent that keeps the internal SQLAlchemy Lead and Ticket tables consistent with outreach state.
- **Reporting_Agent**: The agent that aggregates outreach metrics and delivers summaries to the Dashboard.
- **Auth_Module**: The JWT-based authentication layer already implemented in the backend.
- **API_Client**: The typed TypeScript service layer that wraps all backend REST and WebSocket endpoints.
- **Component_Library**: The shared set of accessible, design-token-driven React UI primitives used across all views.
- **Token**: A JWT access token issued by the backend Auth_Module.

---

## Requirements

### Requirement 1: React/TypeScript SPA Foundation

**User Story:** As a developer, I want a well-structured React/TypeScript SPA scaffold, so that all frontend features are built on a consistent, maintainable foundation that matches backend code quality.

#### Acceptance Criteria

1. THE SPA SHALL be bootstrapped with Vite 5+, React 18, TypeScript 5, and `react-router-dom` v6 where each route module is a co-located file under `src/pages/` with the route path derived from the file name, eliminating a separate route registry.
2. THE Component_Library SHALL provide at minimum: Button, Input, Select, Textarea, Modal, Toast, Badge, Skeleton, DataTable, Tabs, Card, and PageHeader primitives — each exported from a single barrel file at `src/components/ui/index.ts`.
3. THE SPA SHALL enforce strict TypeScript (`"strict": true`) and pass `tsc --noEmit` with zero errors and zero `@ts-ignore` suppressions in production source files.
4. THE SPA SHALL use Tailwind CSS 3 (FOSS) with a custom design token configuration defining at minimum: a `brand` colour palette (50–950 shades), `neutral` greys, `success`/`warning`/`danger` semantic colours, and typographic scale — all tokens SHALL produce WCAG AA contrast (≥4.5:1) against the dark background (`neutral-950`).
5. FOR ALL Component_Library primitives, THE SPA SHALL include co-located Vitest + React Testing Library unit test files achieving ≥90% branch coverage for each component.
6. THE SPA SHALL serve a PWA-ready `manifest.json` (with `name`, `short_name`, `icons`, `start_url`, `display: standalone`) and a `service-worker.ts` stub that registers without error and exposes a `skipWaiting` message handler, so offline capability can be added without architectural changes.
7. IF a route is accessed and `localStorage` contains no `auth_token` key or the stored Token's `exp` claim is in the past, THEN THE Auth_Module SHALL redirect the browser to `/login` and append the originally requested pathname and search as a `?redirect=` query parameter, preserving it for post-login navigation.
8. WHEN a Token's `exp` claim will expire within 60 seconds, THE Auth_Module SHALL automatically call `POST /auth/refresh` once; IF the refresh request fails or returns a non-2xx status, THEN THE Auth_Module SHALL remove `auth_token` from `localStorage` and redirect the user to `/login` within 500ms.

---

### Requirement 2: Authentication & User Management UI

**User Story:** As a user, I want to register, log in, manage my profile and API keys, so that I can securely access the platform.

#### Acceptance Criteria

1. WHEN a user submits valid registration credentials, THE Auth_Module SHALL call `POST /auth/register`, store the returned Token in `localStorage` under key `auth_token`, and navigate to the Dashboard.
2. WHEN a user submits invalid or duplicate registration credentials, THE Auth_Module SHALL display a field-level validation error within 100ms without a full page reload.
3. WHEN a user submits valid login credentials, THE Auth_Module SHALL call `POST /auth/login`, store the returned Token, and navigate to the Dashboard or the `?redirect=` path if present.
4. WHEN a user submits incorrect login credentials, THE Auth_Module SHALL display an error message and increment a failed-attempt counter visible to the user; WHEN the counter reaches 5 failed attempts, THE Auth_Module SHALL disable the submit button for 60 seconds and display a visible countdown.
5. WHILE a user is authenticated, THE SPA SHALL provide a Profile page where the authenticated user can update their full name (1–100 characters) and password (minimum 8 characters) via `PUT /users/me`; IF the password field is left blank, THEN THE SPA SHALL omit the password field from the request body entirely.
6. THE SPA SHALL provide an API Keys section on the Profile page that lists active keys (maximum 20 per user), allows creation of named keys (1–64 characters) with scope selectable from: `read`, `write`, or `admin`, and allows revocation of existing keys.
7. WHEN an API key is revoked, THE SPA SHALL request confirmation via a Modal before calling the deletion endpoint.
8. THE SPA SHALL render an Admin panel route at `/admin` accessible only to users with `role = "admin"` that lists all users, allows toggling `is_active`, and displays subscription tier; IF a non-admin user navigates to `/admin`, THEN THE SPA SHALL redirect them to the Dashboard and display an "Access Denied" Toast.

---

### Requirement 3: Main Dashboard View

**User Story:** As an operator, I want a real-time dashboard showing system health, live agent activity, and KPIs, so that I can monitor the platform at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL display system health KPI cards for API status, Database status, Redis status, and Ollama status by polling `GET /health` every 30 seconds; IF the `GET /health` request itself fails (network error or non-2xx), THEN THE Dashboard SHALL display all four service cards in an "Unknown" state rather than retaining the previous state.
2. WHEN any monitored service (API, Database, Redis, or Ollama) health check status changes from `"ok"` to any other value, THE Dashboard SHALL display a Toast notification with the text `"<ServiceName> degraded"` that auto-dismisses after 8 seconds.
3. THE Dashboard SHALL display a live agent activity feed by subscribing to the WebSocket endpoint `/api/ws` and rendering the last 50 events in reverse-chronological order; each event SHALL display: timestamp (ISO 8601 formatted to local time), agent name, and event message.
4. WHEN the WebSocket connection is lost, THE Dashboard SHALL attempt reconnection using exponential back-off starting at 1 second, doubling on each attempt, capped at 30 seconds, for a maximum of 10 reconnection attempts; WHEN reconnecting, THE Dashboard SHALL display a "Reconnecting…" status indicator; WHEN all 10 attempts are exhausted, THE Dashboard SHALL display a "Connection lost — reload to retry" message and cease attempting.
5. THE Dashboard SHALL display KPI metric cards sourcing data from: `GET /companies` (total count), `GET /deployments?status=active` (count), `GET /api/leads?status=pipeline` (count), and `GET /api/outreach?period=week` (email count) — each card SHALL show a Skeleton while its individual request is in flight.
6. THE Dashboard SHALL render an interactive Chart.js line chart of daily outreach email counts for the trailing 30 calendar days, computed client-side from `GET /api/leads` and `GET /api/outreach` responses; the chart SHALL have labelled axes and a legend.
7. THE Dashboard SHALL provide a Quick-Action card containing a "Build Sprint" form with a project name input; WHEN the form is submitted, THE Dashboard SHALL call `POST /api/build` and, only after the request returns HTTP 200, display an in-page terminal widget that streams the server-sent-event response body line by line until an `event: done` SSE message is received or the stream closes.
8. FOR ALL Dashboard data-fetching hooks, THE SPA SHALL include Vitest unit tests that mock the API_Client and assert correct rendering for loading, success, and error states.

---

### Requirement 4: Project & Company Management UI

**User Story:** As a user, I want to create and manage generated companies and their deployments through a rich interface, so that I can efficiently operate the factory pipeline.

#### Acceptance Criteria

1. THE SPA SHALL provide a Companies page that lists companies from `GET /companies` with server-side pagination (page size 25), status badge filtering, and a search input that debounces at 300ms.
2. THE Companies page creation form SHALL require: `name` (1–200 characters), `domain` (valid hostname format), and `status` (one of: `active`, `inactive`, `pending`) — client-side validation SHALL surface field-level errors before any API call.
3. IF client-side validation passes, THE SPA SHALL call `POST /companies`; IF the server returns HTTP 409, THE SPA SHALL display a field-level error on the `domain` field reading "Domain already registered".
4. IF `POST /companies` fails with any non-409 server error, THE SPA SHALL display a Toast with the server error message and leave the form data intact for retry.
5. THE SPA SHALL provide a Company Detail page at `/companies/:id` showing: company name, domain, status badge, created date, associated tickets list, deployment history, and current workflow status; IF `GET /companies/:id` returns HTTP 404, THE SPA SHALL render a "Not Found" error state with a back-navigation button.
6. THE SPA SHALL provide a Deployments page listing deployments from `GET /deployments` with status filtering, sortable columns (name, status, created date), and a detail slide-over panel showing up to 200 lines of deployment logs.
7. IF `GET /deployments` returns an error, THE SPA SHALL display an error state with a "Retry" button that re-fetches the list.
8. WHEN a deployment action (start, stop, restart) is triggered from the UI, THE SPA SHALL immediately set the deployment row's status badge to "starting", "stopping", or "restarting" optimistically; WHEN the server response arrives within 2 seconds, THE SPA SHALL reconcile with the returned status; IF the request times out or returns an error, THE SPA SHALL revert the badge to its pre-action value and display an error Toast.
9. THE SPA SHALL provide a Tenants page listing tenant boxes from `GET /tenants` with the ability to register a new tenant via an inline form; IF `POST /tenants` fails, THE SPA SHALL display an inline error beneath the form without clearing input values.
10. IF the Tenants list fetch returns an error, THE SPA SHALL display an error state with a "Retry" button.
11. IF any list view (Companies, Deployments, Tenants) returns an empty array, THE SPA SHALL render an accessible empty-state illustration with descriptive alt text and a primary call-to-action button.
12. WHEN any list data is loading, THE SPA SHALL render Skeleton components that match the dimensions of the expected list items, maintaining layout stability with a Cumulative Layout Shift score ≤ 0.1.

---

### Requirement 5: Ticket & Workflow Management UI

**User Story:** As a project manager, I want to view, create, and manage tickets and automation workflows visually, so that I can track work and orchestrate agent pipelines.

#### Acceptance Criteria

1. THE SPA SHALL provide a Tickets page at `/tickets` that fetches tickets from `GET /tickets` and renders them in a Kanban board with four columns: OPEN, IN_PROGRESS, RESOLVED, and CLOSED; IF `GET /tickets` returns an error, THE SPA SHALL display an error state card with a "Retry" button.
2. WHEN a ticket card is dragged to a new column, THE SPA SHALL optimistically update the card's column immediately and call `PUT /tickets/:id` with the new status; IF the API call returns an error within 5 seconds, THE SPA SHALL revert the card to its original column and display an error Toast.
3. WHEN a user clicks a ticket card, THE SPA SHALL open a Ticket Detail modal displaying: title, description, priority badge (low/medium/high/critical), assignee, due date, SLA countdown (warns when ≤24 hours remain), comment thread, and history log.
4. THE Workflow_Builder SHALL render a canvas using `reactflow` (FOSS MIT licence) at `/workflows/builder` where users can drag agent node types onto the canvas, connect them with directed edges, and configure each node's parameters via a side panel.
5. WHEN a user attempts to save a workflow definition and the canvas contains zero nodes, THE Workflow_Builder SHALL display a validation error and block the save; WHEN the canvas is valid, THE Workflow_Builder SHALL serialise the graph to the `steps_json` format expected by `POST /workflows` and submit it.
6. WHEN a workflow is running, THE Workflow_Builder SHALL highlight the currently executing step node with a pulsing border within ≤2 seconds of receiving the corresponding WebSocket event; IF the WebSocket connection is lost while a workflow is running, THE Workflow_Builder SHALL display a "Live updates paused" indicator.
7. THE SPA SHALL provide a Workflow list page at `/workflows` with status badges, creation timestamps, and a Launch button that calls `POST /workflows/:id/trigger`; IF the trigger returns an error, THE SPA SHALL display an error Toast with the server message.
8. FOR ALL Kanban drag interactions and Workflow_Builder node operations, THE SPA SHALL include Vitest integration tests using `@testing-library/user-event`.
9. WHEN the WebSocket connection drops while the Workflow_Builder canvas has an active running workflow, THE Workflow_Builder SHALL poll `GET /workflows/:id` every 10 seconds as a fallback and update node highlight state from the polled response.

---

### Requirement 6: Analytics & Reporting UI

**User Story:** As an executive, I want an analytics dashboard with charts and exportable data, so that I can measure platform performance and outreach effectiveness.

#### Acceptance Criteria

1. THE SPA SHALL provide an Analytics page at `/analytics` with a date-range picker defaulting to the trailing 30 calendar days (maximum selectable range: 365 days) and Chart.js charts for: builds initiated, deployments completed, leads discovered, emails sent, email open rate, and reply rate.
2. THE Analytics page SHALL source data from `GET /api/usage`, `GET /api/leads`, and `GET /api/outreach` and combine them into unified chart datasets client-side; IF any one of the three source requests fails, THE Analytics page SHALL render that source's charts in an error state with a "Retry" button while still displaying charts from the successful sources.
3. WHEN the selected date range changes, THE Analytics page SHALL refetch and re-render all charts within 500ms.
4. THE Analytics page SHALL render a data table beneath each chart showing the same data in tabular form, sortable by all columns; the default sort SHALL be ascending by date; clicking a column header once SHALL sort ascending, clicking again SHALL sort descending.
5. THE SPA SHALL provide a CSV export button on the Analytics page that generates and downloads a `analytics_export_YYYY-MM-DD.csv` file whose rows contain only the date-range-filtered, daily-aggregated data currently displayed on screen — no server call is required.
6. WHERE the user has `role = "admin"`, THE Analytics page SHALL additionally display per-user activity breakdowns and system resource usage panels sourced from `GET /admin/stats`; IF `GET /admin/stats` returns an error, THE SPA SHALL display an error state for the admin panels only, leaving the standard charts unaffected.
7. FOR ALL chart rendering functions, THE SPA SHALL include Vitest snapshot tests that assert chart datasets are correctly computed from mock API responses.

---

### Requirement 7: Lead Management UI (CRM Module)

**User Story:** As a sales operator, I want a full CRM-style lead management interface, so that I can track, enrich, and action every prospect efficiently.

#### Acceptance Criteria

1. THE Lead_Manager SHALL provide a paginated lead list at `/leads` (page size 25) with columns: Company, Name, Email, Status badge, Created date, and a row-level Actions menu.
2. THE Lead_Manager SHALL support multi-column sorting and a global search input that filters by company, name, or email with 300ms debounce, sending `GET /api/leads?q=...&sort=...&page=...`.
3. WHEN a user opens a lead detail slide-over, THE Lead_Manager SHALL display all stored metadata (company, name, email, website, LinkedIn URL, intent_score, status, created date), outreach sequence history, and an "Enrich Lead" button.
4. WHEN the user clicks "Enrich Lead", THE Lead_Manager SHALL call the enrichment endpoint and display a loading spinner on the button until the response arrives; AFTER the enrichment response is received (regardless of success or failure), THE Lead_Manager SHALL independently call `GET /api/leads/:id` to refresh the lead detail view; IF the enrichment endpoint returns an error, THE SPA SHALL display an error Toast but still perform the refresh.
5. THE Lead_Manager SHALL provide a Bulk Actions toolbar that appears when one or more leads are selected via checkboxes, offering: Add to Sequence, Export CSV, Change Status, and Delete; WHEN "Delete" is selected, THE SPA SHALL request confirmation via a Modal before calling the deletion endpoint.
6. WHEN the user selects "Add to Sequence", THE Lead_Manager SHALL open a Modal listing available Sequences with descriptions; IF no Sequences exist, THE Modal SHALL display an empty state with a link to create one; WHEN the user selects a Sequence and confirms, THE Lead_Manager SHALL call `POST /api/outreach/sequence/enroll` with the selected lead IDs and sequence ID.
7. THE Lead_Manager SHALL display a Kanban-style Pipeline view toggle at `/leads?view=pipeline` that groups leads by status column; WHEN a lead card is dragged to a new status column, THE SPA SHALL optimistically update the card's column and call `PUT /api/leads/:id` with the new status; IF the API call returns an error, THE SPA SHALL revert the card and display an error Toast.
8. FOR ALL Lead_Manager interactions, THE SPA SHALL include Vitest + React Testing Library tests covering happy path, empty state, error state, and bulk action flows.

---

### Requirement 8: Outreach Hub UI

**User Story:** As a marketing operator, I want a dedicated Outreach Hub to compose, schedule, monitor, and analyse outreach campaigns, so that I can manage the full cold-outreach lifecycle from the UI.

#### Acceptance Criteria

1. THE SPA SHALL provide an Outreach Hub at `/outreach` with sub-navigation for: Campaigns, Sequences, Inbox, and Reports; THE default sub-view SHALL be Campaigns.
2. THE Outreach Hub Campaign Composer SHALL validate client-side before submission: subject (1–998 characters), recipients (1–500 individual email addresses parsed from multiline or CSV paste), message body (non-empty Tiptap rich-text content), and scheduled-send datetime (must be in the future); IF any validation fails, THE SPA SHALL display field-level errors and block form submission.
3. WHEN a campaign passes validation and is submitted, THE Outreach Hub SHALL call `POST /api/outreach/campaign`; IF the server returns HTTP 2xx, THE SPA SHALL display a queued confirmation Toast (auto-dismissing after 8 seconds) and prepend the campaign to the Campaigns list with status "queued".
4. IF `POST /api/outreach/campaign` returns a non-2xx response, THE SPA SHALL display an error Toast with the server error message and preserve the form data intact for retry without adding any entry to the Campaigns list.
5. WHEN the Sequences sub-view is opened, THE SPA SHALL fetch and display all active Sequences including: name, step count, enrolled prospect count, and step-level open/reply statistics; IF the fetch fails, THE SPA SHALL display an error state with a "Retry" button.
6. WHEN a user creates a new Sequence, THE Outreach Hub SHALL allow adding 1–10 steps; each step SHALL require: delay_days (integer 0–365), subject_template (1–998 characters), and body_template (1–100,000 characters) using `{{first_name}}` and `{{company}}` merge fields; IF validation of any field fails on save, THE SPA SHALL block submission and display field-level errors.
7. WHEN the Inbox sub-view is opened, THE SPA SHALL fetch and display inbound replies from `GET /api/outreach/inbox` with colour-coded classification badges: green for Interested, red for Not Interested, grey for Auto-Reply, orange for Bounce; IF the fetch fails, THE SPA SHALL display an error state with a "Retry" button.
8. WHEN the Inbox list is rendered, Interested replies SHALL appear at the top of the list above all other classification types, sorted by received date descending within that group.
9. IF a reply classified as "Interested" is received via WebSocket and the Notifications API permission is `"granted"`, THEN THE SPA SHALL fire a browser Notification with the title "New interested reply" and the sender email as the body.
10. WHEN the Reports sub-view is opened, THE SPA SHALL fetch data from `GET /api/outreach/reports/daily` and render a horizontal funnel chart (Chart.js) with stages: Prospects → Contacted → Opened → Replied → Interested; IF the fetch returns an empty array, THE SPA SHALL display an empty-state message; IF the fetch fails, THE SPA SHALL display an error state with a "Retry" button.
11. FOR ALL Outreach Hub components, THE SPA SHALL include Vitest unit and integration tests achieving ≥90% branch coverage, covering: campaign submission success and error paths, sequence step validation, inbox classification badge rendering, and funnel chart data computation.

---

### Requirement 9: Prospect Discovery Agent

**User Story:** As a growth operator, I want an automated prospect discovery system, so that the platform continuously identifies and qualifies new high-intent sales targets without manual list building.

#### Acceptance Criteria

1. THE Enrichment_Agent SHALL accept a niche descriptor string (1–500 non-whitespace characters; reject with a descriptive error if outside bounds) and return a structured list of up to 100 Prospect records each containing: company name, contact name, email (or `null`), website, LinkedIn URL, and intent_score (0–100).
2. WHEN the Enrichment_Agent cannot resolve a valid email for a Prospect, THE Enrichment_Agent SHALL set the email field to `null` and flag the Prospect with `needs_review = true` rather than generating a synthetic address.
3. THE Enrichment_Agent SHALL use only FOSS and self-hosted data sources: the existing `web_search` tool, `requests`-based HTTP crawling with `BeautifulSoup4` (capped at 5 pages per Prospect), and the local Ollama LLM as the primary entity extraction method.
4. WHEN Ollama is unavailable (no response within 10 seconds or connection refused), THE Enrichment_Agent SHALL fall back to regex-based extraction from crawled HTML and log a WARNING; IF regex extraction yields no usable fields for a Prospect, THEN THE Enrichment_Agent SHALL skip that record and continue processing remaining records without raising an exception.
5. THE Enrichment_Agent SHALL persist each discovered Prospect to the `leads` table via `backend.db.linear_engine.get_swarm_db().create_lead()`, deduplicating by email before insert; Prospects with `email = null` SHALL always be inserted as new records regardless of other field values.
6. WHEN a Prospect with the same email already exists in the database, THE Enrichment_Agent SHALL update the existing record's company name, contact name, website, LinkedIn URL, and intent_score with the newly discovered values.
7. THE Enrichment_Agent SHALL compute intent_score using these observable signals (additive, capped at 100): +30 if the company's website has a job posting for a role matching the niche descriptor; +20 if a valid contact email was resolved; +20 if the company homepage returns HTTP 200; +30 if the company name appears in the niche-targeted search results.
8. THE Enrichment_Agent SHALL expose a Celery task `enrich_prospects` with `soft_time_limit=300` and `time_limit=360` that can be triggered on demand or scheduled via Celery Beat.
9. FOR ALL Enrichment_Agent logic, the codebase SHALL include Pytest unit tests achieving ≥90% branch coverage, with Ollama LLM calls and HTTP requests mocked.

---

### Requirement 10: Email Sequencing & Personalisation Agent

**User Story:** As a sales operator, I want an automated sequencer that sends personalised multi-step email sequences to prospects, so that outreach happens without manual intervention.

#### Acceptance Criteria

1. THE Sequencer_Agent SHALL maintain a Sequence definition data model with fields: id (UUID), name (1–255 characters), steps (ordered list of 1–10 entries, each with delay_days (0–365 integer), subject_template (string), body_template (string)), and status (one of: `active`, `paused`, `archived`).
2. WHEN a Prospect is enrolled in a Sequence, THE Sequencer_Agent SHALL create a SequenceEnrollment record linking the Prospect to the Sequence and initialise current_step to 0; IF an active enrollment for the same Prospect+Sequence combination already exists, THE Sequencer_Agent SHALL reject the duplicate enrollment with a descriptive error and leave the existing enrollment unchanged.
3. THE Sequencer_Agent SHALL render personalised emails by substituting `{{first_name}}`, `{{last_name}}`, `{{company}}`, and `{{website}}` merge fields from the Prospect record into step templates; IF a Prospect field is null or empty, THE Sequencer_Agent SHALL substitute an empty string so that no raw `{{token}}` appears in the rendered output.
4. WHEN a Sequence step's scheduled send time is reached, THE Sequencer_Agent SHALL call the existing `EmailTools.send_email()` method and record the outcome (sent, failed) in a SequenceStepLog table; each step's scheduled send time SHALL be computed as enrollment_created_at + sum(delay_days for steps 0 through current_step).
5. IF an email send fails after all `EmailTools` retries are exhausted, THEN THE Sequencer_Agent SHALL mark the step as `failed` in SequenceStepLog and set the enrollment status to `paused` rather than skipping to the next step.
6. WHEN the Sequencer_Agent receives a `reply_received` internal event bus signal for a Prospect, THE Sequencer_Agent SHALL set the enrollment status to `replied` and halt all remaining steps for that enrollment to prevent follow-up emails being sent to a responder.
7. THE Sequencer_Agent SHALL be driven by a Celery Beat periodic task `process_due_sequence_steps` that runs every 5 minutes.
8. FOR ALL Sequencer_Agent logic, the codebase SHALL include Pytest unit tests achieving ≥90% branch coverage, with the `EmailTools` and database layer mocked.

---

### Requirement 11: Inbox Monitoring & Reply Classification Agent

**User Story:** As a sales operator, I want all inbound replies automatically classified and routed, so that interested prospects are never missed and wasted follow-ups are suppressed.

#### Acceptance Criteria

1. THE Reply_Handler_Agent SHALL be driven by a Celery Beat periodic task `check_inbox_replies` that runs every 5 minutes and connects to an IMAP mailbox configured via `IMAP_SERVER`, `IMAP_USER`, and `IMAP_PASS` environment variables using the `imaplib` standard library.
2. WHEN a new email is fetched from the IMAP inbox, THE Reply_Handler_Agent SHALL extract the sender address, subject, and up to 10,000 characters of body text, and use the local Ollama LLM to classify the email as exactly one of: `interested`, `not_interested`, `auto_reply`, or `bounce`.
3. WHEN Ollama is unavailable during classification, THE Reply_Handler_Agent SHALL apply the following normative heuristic rules (in order): (a) IF the SMTP `Return-Path` header equals `<>` OR the subject matches `/^(Mail Delivery|Undeliverable|Delivery (Status Notification|Failed))/i`, THEN classify as `bounce`; (b) IF the body contains any of: "out of office", "on vacation", "auto-reply", "automatic reply" (case-insensitive), THEN classify as `auto_reply`; (c) IF the body contains "unsubscribe" or "remove me" (case-insensitive), THEN classify as `not_interested`; (d) OTHERWISE classify as `interested`; THE Reply_Handler_Agent SHALL log a WARNING with the reason Ollama was unavailable.
4. WHEN a reply is classified as `interested`, THE Reply_Handler_Agent SHALL: update the SequenceEnrollment status to `replied_interested`; create a Ticket via `db.create_ticket()` with `priority = "high"` and title `"Interested reply from <sender_email>"`; and publish a WebSocket event with type `reply_classified` and payload `{"lead_id": "...", "classification": "interested"}` for real-time Dashboard notification.
5. WHEN a reply is classified as `not_interested`, THE Reply_Handler_Agent SHALL update the enrollment status to `replied_uninterested` and cause the Sequencer_Agent to halt further steps by publishing a `reply_received` event to the internal event bus; WHEN classified as `auto_reply`, THE Reply_Handler_Agent SHALL set the enrollment status to `paused`.
6. WHEN a reply is classified as `bounce`, THE Reply_Handler_Agent SHALL mark the Prospect's email field as `invalid`, set the enrollment status to `failed`, and write a `processed_events` record with event_type `bounce_logged` for the Reporting_Agent to consume.
7. THE Reply_Handler_Agent SHALL avoid re-processing already-seen emails by storing the IMAP message UID in the `processed_events` table AFTER all classification and downstream actions have completed successfully; IF any downstream action fails, THE UID SHALL NOT be stored so that the email is retried on the next poll.
8. IF the IMAP connection cannot be established (e.g., wrong credentials, network timeout), THE Reply_Handler_Agent SHALL log an ERROR and exit the Celery task gracefully without raising an unhandled exception.
9. IF a fetched email's sender address does not match any Prospect record in the database, THE Reply_Handler_Agent SHALL store the UID as processed, log an INFO message with the unmatched sender address, and continue processing remaining emails.
10. FOR ALL Reply_Handler_Agent logic, the codebase SHALL include Pytest unit tests achieving ≥90% branch coverage, with IMAP, Ollama, and database dependencies mocked.

---

### Requirement 12: CRM Sync & State Machine Agent

**User Story:** As an operator, I want all outreach state changes automatically reflected in the CRM lead records and ticket system, so that the sales team always sees accurate pipeline state.

#### Acceptance Criteria

1. THE CRM_Sync_Agent SHALL listen to an internal event bus (`backend.services.event_bus`) for events of type: `prospect_discovered`, `sequence_enrolled`, `email_sent`, `reply_received`, `sequence_completed`.
2. WHEN the CRM_Sync_Agent receives a `prospect_discovered` event, THE CRM_Sync_Agent SHALL upsert the Prospect into the `leads` table with status `NEW`; IF a `sequence_enrolled` or later-stage event arrives before `prospect_discovered`, THE CRM_Sync_Agent SHALL buffer the later event (up to 50 buffered events per lead) and replay it after the `prospect_discovered` event is processed.
3. WHEN the CRM_Sync_Agent receives a `sequence_enrolled` event, THE CRM_Sync_Agent SHALL update the Lead status to `CONTACTED`; IF the Lead record does not exist, THE CRM_Sync_Agent SHALL log a WARNING and discard the event.
4. WHEN the CRM_Sync_Agent receives a `reply_received` event with classification `interested`, THE CRM_Sync_Agent SHALL atomically update the Lead status to `QUALIFIED` and create a Ticket with `priority = "high"` and title `"Qualified lead: <lead_company>"` within a single database transaction; IF the transaction fails, THE CRM_Sync_Agent SHALL roll back, log an ERROR, and discard the event without partial side effects.
5. WHEN the CRM_Sync_Agent receives a `sequence_completed` event with `has_reply: false`, THE CRM_Sync_Agent SHALL update the Lead status to `COLD`; IF the Lead record does not exist, THE CRM_Sync_Agent SHALL log a WARNING and discard the event.
6. THE CRM_Sync_Agent SHALL expose a `GET /api/leads/:id/timeline` endpoint that returns a chronological JSON array of state transitions, each containing: `from_status`, `to_status`, `triggered_by` (event type), and `occurred_at` (ISO 8601); IF no Lead with the given id exists, THE endpoint SHALL return HTTP 404.
7. FOR ALL CRM_Sync_Agent event handlers, the codebase SHALL include Pytest unit tests achieving ≥90% branch coverage, asserting correct state transitions for each event type.
8. IF a `sequence_enrolled`, `email_sent`, or `sequence_completed` event references a Lead ID not present in the database and no `prospect_discovered` event is buffered for that ID, THE CRM_Sync_Agent SHALL log a WARNING with the lead ID and discard the event.

---

### Requirement 13: Outreach Reporting Agent

**User Story:** As a growth operator, I want automated reporting on outreach performance, so that I can make data-driven decisions without manually querying the database.

#### Acceptance Criteria

1. WHEN the `generate_daily_outreach_report` Celery task executes, THE Reporting_Agent SHALL aggregate metrics for the preceding UTC calendar day from the following sources: `prospects_discovered` (count of leads inserted that day), `emails_sent` (count of `SequenceStepLog` rows with outcome `sent`), `open_rate` (float 0.0–1.0 = opens/sent where `opens_tracked = true`; `null` if no trackable sends), `reply_rate` (float 0.0–1.0 = replied enrollments / sent emails; `null` if sent = 0), `interested_count` (integer ≥ 0 count of enrollments with `replied_interested`), `bounce_rate` (float 0.0–1.0 = bounced enrollments / sent emails; `null` if sent = 0).
2. THE Reporting_Agent SHALL persist daily metric snapshots to an `outreach_daily_metrics` SQLAlchemy table with columns: `id` (UUID PK), `date` (Date, not null), `metric_name` (String, not null), `metric_value` (Float, nullable).
3. THE Reporting_Agent SHALL be driven by a Celery Beat task `generate_daily_outreach_report` that runs at 01:00 UTC daily.
4. THE Reporting_Agent SHALL expose a `GET /api/outreach/reports/daily` endpoint accepting `start_date` and `end_date` query parameters (ISO 8601 date strings); IF either parameter is missing, malformed, or `start_date > end_date`, THE endpoint SHALL return HTTP 400 with a JSON body `{"error": "<descriptive message>"}`.
5. WHEN no data exists for a requested date range, THE endpoint SHALL return HTTP 200 with an empty JSON array.
6. WHEN the Celery task runs for a date that already has metric rows in `outreach_daily_metrics`, THE Reporting_Agent SHALL upsert (update existing rows) rather than inserting duplicates, ensuring the task is idempotent.
7. FOR ALL Reporting_Agent aggregation functions, the codebase SHALL include Pytest unit tests achieving ≥90% branch coverage, with database queries mocked.

---

### Requirement 14: Testing Parity & CI Integration

**User Story:** As a lead developer, I want every new file to have a corresponding test file and CI gates to enforce coverage, so that the codebase maintains ≥90% test coverage as it grows.

#### Acceptance Criteria

1. THE SPA SHALL include a `vitest.config.ts` configured with `@vitest/coverage-v8`, enforcing a minimum statement, branch, function, and line coverage threshold of 90% — the Vitest process SHALL exit with a non-zero code if any threshold is not met.
2. THE backend test suite SHALL include `pytest-cov` configured in `pyproject.toml` with `--cov-fail-under=90` so the CI pipeline fails if backend coverage drops below 90%.
3. THE GitHub Actions CI workflow SHALL include a `frontend-test` job that runs `vitest --run --coverage`, fails the workflow if coverage thresholds are not met, and uploads the coverage report as an artifact with a 30-day retention period.
4. THE GitHub Actions CI workflow SHALL include a `backend-test` job that runs `pytest --cov --cov-fail-under=90`, fails the workflow if coverage drops below 90%, and uploads the coverage report as an artifact with a 30-day retention period.
5. FOR ALL Python agent or service files that are added or renamed in a pull request, the pull request SHALL include a corresponding `tests/agents/test_<filename>.py` or `tests/services/test_<filename>.py` file; the CI `backend-test` job SHALL fail if a new `.py` file under `agents/` or `backend/services/` lacks a corresponding test file.
6. FOR ALL TypeScript React component files that are added or renamed in a pull request, the pull request SHALL include a corresponding `__tests__/<ComponentName>.test.tsx` file; the CI `frontend-test` job SHALL fail if a new `.tsx` file under `src/components/` lacks a corresponding test file.
7. THE SPA SHALL include property-based tests using `fast-check` (FOSS MIT) with at minimum 100 example trials each for: merge-field interpolation, date-range computation for charts, CSV export row generation, and lead deduplication logic.
8. THE backend SHALL include `hypothesis`-based property tests with at minimum 100 examples each for: email address normalisation, Prospect deduplication, sequence step scheduling arithmetic, and outreach metric aggregation.

---

### Requirement 15: FOSS Dependency & Performance Constraints

**User Story:** As a FOSS project maintainer, I want all dependencies to be open-source with no paid APIs or services required, and I want the frontend to meet core web vital thresholds, so that the platform remains zero-cost to operate and delivers a premium user experience.

#### Acceptance Criteria

1. THE SPA SHALL list zero paid or proprietary npm dependencies — all packages in `package.json` SHALL have an OSI-approved open-source licence.
2. THE Outreach_Pipeline SHALL use only self-hosted or open-source services: Ollama for LLM inference, the existing SMTP configuration for email delivery, and `imaplib` for inbox polling.
3. WHEN the CI `lighthouse-ci` job measures the Dashboard route in a simulated Moto G4 / Fast 3G environment, THE SPA SHALL achieve a Lighthouse Performance category score ≥ 85.
4. WHEN the SPA bundle is built with `vite build`, THE SPA SHALL produce a gzip-compressed JavaScript payload of no more than 400 KB total for all synchronously loaded entry and shared vendor chunks required for the Dashboard route's initial navigation.
5. WHEN a user's browser loads any non-Dashboard route for the first time, THE SPA SHALL request only the route-specific chunk for that route via `React.lazy()` and `Suspense`; shared vendor chunks (React, React Query, etc.) are permitted to load on initial navigation and do not count against this criterion.
6. THE SPA SHALL implement React Query (`@tanstack/react-query` FOSS MIT) for all server-state management; WHEN any API call returns a failed HTTP status code OR a 2xx response whose JSON body contains an `error` key with a non-null value, THE SPA SHALL display a dismissable Toast notification (auto-dismissing after 8 seconds, also manually dismissable) describing the error.
7. WHEN a REST API call returns HTTP 429 (Too Many Requests), THE API_Client SHALL apply exponential back-off retry with jitter (base 1s, max 30s, max 5 retries) before surfacing the error to the UI; IF the retry logic throws a synchronous exception before the first retry attempt is issued, THEN THE API_Client SHALL surface the original error immediately without attempting retries.
