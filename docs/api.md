# API Reference — SwarmEnterprise v2

**Base URL** (local development): `http://localhost:8000`  
**API Version**: 2.0.0  
**OpenAPI Docs**: `GET /docs` (Swagger UI) · `GET /redoc` (ReDoc)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Error Format](#error-format)
3. [Rate Limiting](#rate-limiting)
4. [Auth Endpoints](#auth-endpoints)
5. [User Endpoints](#user-endpoints)
6. [Ticket Endpoints](#ticket-endpoints)
7. [Notification Endpoints](#notification-endpoints)
8. [Workflow Endpoints](#workflow-endpoints)
9. [Health & Metrics](#health--metrics)

---

## Authentication

All protected endpoints require a Bearer token obtained from `POST /api/auth/login`.

```http
Authorization: Bearer <access_token>
```

Tokens are **JWT HS256**, signed with `JWT_SECRET_KEY`. Access tokens expire
after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 15 minutes). Use
`POST /api/auth/refresh` with a valid refresh token to obtain a new access
token without re-authenticating.

---

## Error Format

All errors return a JSON body with a `detail` field:

```json
{
  "detail": "Human-readable error description"
}
```

Validation errors (422) include a structured `detail` array from Pydantic:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "title"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

| Status Code | Meaning |
|------------|---------|
| `200` | OK |
| `201` | Created |
| `204` | No Content |
| `400` | Bad Request (duplicate, invalid state) |
| `401` | Unauthorized (missing or invalid token) |
| `403` | Forbidden (insufficient role) |
| `404` | Not Found |
| `422` | Unprocessable Entity (validation error) |
| `429` | Too Many Requests (rate limit) |
| `500` | Internal Server Error |

---

## Rate Limiting

Default: **120 requests / minute per IP address**. Configurable via the
`RATE_LIMIT_RPM` environment variable. When exceeded the response is:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{"detail": "Rate limit exceeded. Please try again later."}
```

Every response includes `X-Request-ID` for correlation.

---

## Auth Endpoints

### POST `/api/auth/register`

Register a new user account.

**Request body**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `email` | string (email) | ✅ | valid email format |
| `password` | string | ✅ | ≥ 8 characters |
| `full_name` | string | ✅ | non-empty |

```json
{
  "email": "alice@example.com",
  "password": "S3cur3Pass!",
  "full_name": "Alice Example"
}
```

**Response** `201 Created`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "a1b2c3d4",
    "email": "alice@example.com",
    "full_name": "Alice Example",
    "role": "user",
    "subscription_tier": "free",
    "is_active": true,
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00"
  }
}
```

---

### POST `/api/auth/login`

Authenticate with email and password.

**Request body**

| Field | Type | Required |
|-------|------|----------|
| `email` | string (email) | ✅ |
| `password` | string | ✅ |

```json
{
  "email": "alice@example.com",
  "password": "S3cur3Pass!"
}
```

**Response** `200 OK` — same schema as `/api/auth/register`.

---

### POST `/api/auth/logout`

Revoke the current access token. Requires `Authorization: Bearer <token>`.

**Response** `200 OK`

```json
{"message": "Successfully logged out"}
```

---

### POST `/api/auth/refresh`

Exchange a refresh token for a new access token.

**Request body**

```json
{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
```

**Response** `200 OK`

```json
{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
```

---

### GET `/api/auth/verify` 🔐

Verify the current token is valid.

**Response** `200 OK`

```json
{"valid": true, "user": {"id": "...", "email": "...", "role": "user"}}
```

---

### GET `/api/auth/me` 🔐

Return the full profile of the currently authenticated user.

**Response** `200 OK` — `UserResponse` schema (same as register response `user` field).

---

## User Endpoints

All user endpoints require authentication (`Authorization: Bearer <token>`).
Admin-only endpoints additionally require `role: admin` or `role: superadmin`.

### GET `/api/users/me` 🔐

Return the current user's profile.

**Response** `200 OK` — `UserResponse` object.

---

### PUT `/api/users/me` 🔐

Update the current user's profile.

**Request body** (all fields optional)

| Field | Type |
|-------|------|
| `full_name` | string |
| `email` | string (email) |

```json
{"full_name": "Alice Updated"}
```

**Response** `200 OK` — updated `UserResponse`.

---

### DELETE `/api/users/me` 🔐

Soft-delete the current user's account (`is_active = false`).

**Response** `200 OK`

```json
{"message": "Account deleted successfully"}
```

---

### GET `/api/users/{user_id}` 🔐

Get a user by ID. Admin users may retrieve any user; standard users may only
retrieve their own profile.

**Path params**: `user_id` (string)

**Response** `200 OK` — `UserResponse` or `403 Forbidden`.

---

### GET `/api/users/` 🔐 (admin)

List all users (paginated).

**Query params**

| Param | Type | Default |
|-------|------|---------|
| `skip` | int | 0 |
| `limit` | int | 100 |

**Response** `200 OK` — array of `UserResponse`.

---

### PUT `/api/users/{user_id}` 🔐 (admin)

Update any user's profile fields. Admin only.

---

### DELETE `/api/users/{user_id}` 🔐 (admin)

Soft-delete a user. Admin only.

**Response** `200 OK` — `{"message": "User deleted successfully"}`.

---

### POST `/api/users/{user_id}/suspend` 🔐 (admin)

Deactivate a user account. Admin only.

**Response** `200 OK` — `{"message": "User suspended successfully"}`.

---

### POST `/api/users/{user_id}/activate` 🔐 (admin)

Re-activate a suspended user. Admin only.

**Response** `200 OK` — `{"message": "User activated successfully"}`.

---

## Ticket Endpoints

All ticket endpoints require authentication.

### GET `/api/tickets` 🔐

List tickets with optional filters (paginated).

**Query params**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status: `OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED` |
| `priority` | string | Filter by priority: `low`, `medium`, `high`, `critical` |
| `assignee_id` | string | Filter by assigned user ID |
| `date_from` | datetime (ISO 8601) | Created-at lower bound |
| `date_to` | datetime (ISO 8601) | Created-at upper bound |
| `skip` | int | Pagination offset (default: 0) |
| `limit` | int | Page size 1–200 (default: 50) |

**Response** `200 OK`

```json
{
  "items": [
    {
      "id": "A1B2C3D4",
      "title": "Fix login bug",
      "instruction": "Debug the OAuth2 flow",
      "status": "OPEN",
      "priority": "high",
      "assignee_id": null,
      "reporter_id": "user-uuid",
      "project_id": null,
      "department": null,
      "due_date": null,
      "resolved_at": null,
      "sla_hours": 24,
      "tags": null,
      "parent_ticket_id": null,
      "estimated_hours": null,
      "actual_hours": null,
      "created_at": "2025-01-01T12:00:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

---

### POST `/api/tickets` 🔐

Create a new ticket.

**Request body**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `title` | string | ✅ | — |
| `instruction` | string | ✅ | — |
| `project_id` | string | — | null |
| `department` | string | — | null |
| `priority` | string | — | `"medium"` |
| `assignee_id` | string | — | null |
| `due_date` | datetime | — | null |
| `sla_hours` | int | — | 24 |
| `tags` | string | — | null |
| `parent_ticket_id` | string | — | null |
| `estimated_hours` | float | — | null |

```json
{
  "title": "Add rate-limit headers",
  "instruction": "Expose X-RateLimit-Remaining on every response",
  "priority": "medium",
  "sla_hours": 48
}
```

**Response** `201 Created` — Ticket object (same schema as items array above).

---

### GET `/api/tickets/{ticket_id}` 🔐

Retrieve a single ticket by ID.

**Response** `200 OK` — Ticket object, or `404` if not found.

---

### PUT `/api/tickets/{ticket_id}` 🔐

Update ticket fields. Only supplied fields are updated.

**Request body** — any subset of `TicketUpdate` fields:
`title`, `instruction`, `priority`, `assignee_id`, `due_date`, `sla_hours`,
`tags`, `estimated_hours`, `actual_hours`, `status`.

**Response** `200 OK` — updated Ticket object.

---

### DELETE `/api/tickets/{ticket_id}` 🔐 (admin)

Permanently delete a ticket. Admin only.

**Response** `200 OK` — `{"ok": true}`.

---

### POST `/api/tickets/{ticket_id}/assign` 🔐

Assign the ticket to a user.

```json
{"assignee_id": "user-uuid"}
```

**Response** `200 OK` — updated Ticket object.

---

### POST `/api/tickets/{ticket_id}/escalate` 🔐

Escalate ticket priority one level (low→medium→high→critical).

**Response** `200 OK` — updated Ticket object.

---

### POST `/api/tickets/{ticket_id}/resolve` 🔐

Mark the ticket as `RESOLVED`.

```json
{"actual_hours": 2.5}
```

**Response** `200 OK` — updated Ticket object with `status: "RESOLVED"`.

---

### POST `/api/tickets/{ticket_id}/close` 🔐

Close a resolved ticket (`status: "CLOSED"`).

**Response** `200 OK` — updated Ticket object.

---

### POST `/api/tickets/{ticket_id}/comment` 🔐

Add a comment to a ticket.

```json
{"content": "Confirmed the bug — fix is in review."}
```

**Response** `201 Created`

```json
{
  "id": "comment-uuid",
  "ticket_id": "A1B2C3D4",
  "user_id": "user-uuid",
  "content": "Confirmed the bug — fix is in review.",
  "created_at": "2025-01-01T13:00:00"
}
```

---

### GET `/api/tickets/{ticket_id}/history` 🔐

Return the full audit trail of changes for a ticket.

**Response** `200 OK` — array of history records:

```json
[
  {
    "id": "hist-uuid",
    "ticket_id": "A1B2C3D4",
    "user_id": "user-uuid",
    "action": "created",
    "old_value": null,
    "new_value": "Add rate-limit headers",
    "created_at": "2025-01-01T12:00:00"
  }
]
```

---

## Notification Endpoints

All notification endpoints return only notifications belonging to the
authenticated user — cross-user access is not permitted.

### GET `/api/notifications` 🔐

List notifications for the current user.

**Query params**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | int | 0 | Pagination offset |
| `limit` | int | 50 | Page size 1–200 |
| `unread_only` | bool | false | Only return unread |

**Response** `200 OK`

```json
{
  "total": 2,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "notif-uuid",
      "user_id": "user-uuid",
      "type": "info",
      "title": "Ticket assigned",
      "message": "Ticket A1B2C3D4 has been assigned to you.",
      "is_read": false,
      "metadata": null,
      "created_at": "2025-01-01T12:00:00"
    }
  ]
}
```

---

### POST `/api/notifications/read/{notification_id}` 🔐

Mark a single notification as read.

**Response** `200 OK` — `{"ok": true}` or `404`.

---

### POST `/api/notifications/read-all` 🔐

Mark all of the current user's notifications as read.

**Response** `200 OK` — `{"ok": true}`.

---

### DELETE `/api/notifications/{notification_id}` 🔐

Delete a notification.

**Response** `200 OK` — `{"ok": true}` or `404`.

---

## Workflow Endpoints

### POST `/api/workflows` 🔐

Create a new workflow definition.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Human-readable workflow name |
| `steps` | array | ✅ | Ordered list of step definitions |
| `company_id` | string | — | Associated tenant (optional) |

Each step in `steps`:

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `step_name` | string | ✅ | Unique name within workflow |
| `step_type` | string | ✅ | `ticket`, `notification`, `approval`, `condition` |
| `input` | object | — | Step-type-specific configuration |

```json
{
  "name": "Onboarding Workflow",
  "steps": [
    {"step_name": "create-ticket", "step_type": "ticket", "input": {"title": "Setup env"}},
    {"step_name": "notify-team",   "step_type": "notification", "input": {"message": "Started"}}
  ]
}
```

**Response** `201 Created` — Workflow status object (see GET `/api/workflows/{id}`).

---

### GET `/api/workflows` 🔐

List all workflows (paginated, most recent first).

**Query params**: `skip` (int, default 0), `limit` (int, default 50, max 200).

**Response** `200 OK`

```json
{"skip": 0, "limit": 50, "items": [...]}
```

---

### GET `/api/workflows/{workflow_id}` 🔐

Get the current status and step details of a workflow.

**Response** `200 OK`

```json
{
  "id": "wf-uuid",
  "name": "Onboarding Workflow",
  "status": "pending",
  "current_step": 0,
  "total_steps": 2,
  "error_message": null,
  "created_at": "2025-01-01T12:00:00",
  "updated_at": "2025-01-01T12:00:00",
  "completed_at": null,
  "steps": [
    {
      "id": "step-uuid",
      "step_name": "create-ticket",
      "step_type": "ticket",
      "status": "pending",
      "input_json": "{\"title\": \"Setup env\"}",
      "output_json": null
    }
  ]
}
```

---

### POST `/api/workflows/{workflow_id}/start` 🔐

Start a pending workflow. Transitions to `running` and enqueues the first step.

**Response** `200 OK` — updated Workflow status object.

---

### POST `/api/workflows/{workflow_id}/pause` 🔐

Pause a running workflow (`status: "paused"`).

**Response** `200 OK` — updated Workflow status object.

---

### POST `/api/workflows/{workflow_id}/resume` 🔐

Resume a paused workflow (`status: "running"`).

**Response** `200 OK` — updated Workflow status object.

---

### POST `/api/workflows/{workflow_id}/cancel` 🔐

Cancel a workflow (`status: "failed"`). The cancelling user ID is recorded in
`error_message`.

**Response** `200 OK` — updated Workflow status object.

---

## Health & Metrics

### GET `/health`

Check the health of the application and its dependencies. No authentication
required.

**Response** `200 OK`

```json
{
  "status": "ONLINE",
  "version": "2.0.0",
  "engine": "SwarmOS",
  "deploy_profile": "local",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "ollama": "unreachable"
  }
}
```

`checks` values: `"ok"` | `"unreachable"`.

---

### GET `/metrics`

Prometheus metrics in text exposition format. No authentication required.

---

*Made with IBM Bob*
