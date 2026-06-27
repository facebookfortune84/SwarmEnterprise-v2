"""
locustfile.py — Load test scenarios for SwarmEnterprise v2.

Scenarios
---------
TicketUser   (weight 5)  — the most common user: authenticates, lists and
                           creates tickets, reads a ticket, updates it.
WorkflowUser (weight 2)  — creates and manages workflows.
NotifyUser   (weight 2)  — reads and marks notifications.
AdminUser    (weight 1)  — admin-level list-users and list-tickets.

Usage
-----
Headless run (CI):
    locust -f locustfile.py --headless \
        --host http://localhost:8000 \
        -u 50 -r 5 --run-time 60s \
        --html report.html

Interactive:
    locust -f locustfile.py --host http://localhost:8000
    # then open http://localhost:8089

Thresholds (enforced in performance.yml):
    P95 response time < 500 ms
    Error rate         < 1 %
    Minimum RPS        >= 50
"""

from __future__ import annotations

import random
import string
import uuid

from locust import HttpUser, between, task

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_PRIORITIES = ["low", "medium", "high", "critical"]
_STEP_TYPES = ["condition", "notification"]


def _random_email() -> str:
    """Generate a unique email address for each virtual user."""
    suffix = uuid.uuid4().hex[:10]
    return f"loadtest_{suffix}@example.com"


def _random_string(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# TicketUser — core ticket CRUD (weight 5)
# ---------------------------------------------------------------------------


class TicketUser(HttpUser):
    """
    Simulates a standard authenticated user interacting with the ticket system.

    Lifecycle:
        on_start  → register + login → store access_token
        @task(3)  → list tickets
        @task(2)  → create ticket, store ticket_id
        @task(2)  → read ticket
        @task(1)  → update ticket (priority / status)
        @task(1)  → add comment
        @task(1)  → get ticket history
    """

    weight = 5
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        """Register a new user and obtain a JWT access token."""
        self._token: str = ""
        self._ticket_ids: list[str] = []

        email = _random_email()
        password = "LoadTest1!"

        # Register
        resp = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Load Tester"},
            name="/api/auth/register",
        )
        if resp.status_code == 201:
            body = resp.json()
            self._token = body.get("access_token", "")
        elif resp.status_code == 400:
            # Already registered — fall through to login
            pass

        # Login (always attempt, handles duplicate registration)
        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="/api/auth/login",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")

    def _headers(self) -> dict[str, str]:
        return _auth_headers(self._token)

    @task(3)
    def list_tickets(self) -> None:
        """GET /api/tickets — most frequent operation."""
        priority = random.choice([None, "high", "medium"])
        params: dict[str, object] = {"limit": 20, "skip": 0}
        if priority:
            params["priority"] = priority
        self.client.get(
            "/api/tickets", params=params, headers=self._headers(), name="/api/tickets [list]"
        )

    @task(2)
    def create_ticket(self) -> None:
        """POST /api/tickets — create a new ticket and store the ID."""
        payload = {
            "title": f"Load test ticket {_random_string()}",
            "instruction": "Automated load test — please ignore.",
            "priority": random.choice(_PRIORITIES),
            "sla_hours": random.choice([12, 24, 48]),
        }
        resp = self.client.post(
            "/api/tickets",
            json=payload,
            headers=self._headers(),
            name="/api/tickets [create]",
        )
        if resp.status_code == 201:
            ticket_id = resp.json().get("id")
            if ticket_id:
                self._ticket_ids.append(ticket_id)
                # Keep list bounded
                if len(self._ticket_ids) > 20:
                    self._ticket_ids.pop(0)

    @task(2)
    def read_ticket(self) -> None:
        """GET /api/tickets/{id} — read a previously created ticket."""
        if not self._ticket_ids:
            return
        ticket_id = random.choice(self._ticket_ids)
        self.client.get(
            f"/api/tickets/{ticket_id}",
            headers=self._headers(),
            name="/api/tickets/{id} [read]",
        )

    @task(1)
    def update_ticket(self) -> None:
        """PUT /api/tickets/{id} — update priority or tags."""
        if not self._ticket_ids:
            return
        ticket_id = random.choice(self._ticket_ids)
        self.client.put(
            f"/api/tickets/{ticket_id}",
            json={"priority": random.choice(_PRIORITIES), "tags": "load-test"},
            headers=self._headers(),
            name="/api/tickets/{id} [update]",
        )

    @task(1)
    def add_comment(self) -> None:
        """POST /api/tickets/{id}/comment — add a comment."""
        if not self._ticket_ids:
            return
        ticket_id = random.choice(self._ticket_ids)
        self.client.post(
            f"/api/tickets/{ticket_id}/comment",
            json={"content": f"Load test comment {_random_string()}"},
            headers=self._headers(),
            name="/api/tickets/{id}/comment",
        )

    @task(1)
    def get_history(self) -> None:
        """GET /api/tickets/{id}/history — fetch audit trail."""
        if not self._ticket_ids:
            return
        ticket_id = random.choice(self._ticket_ids)
        self.client.get(
            f"/api/tickets/{ticket_id}/history",
            headers=self._headers(),
            name="/api/tickets/{id}/history",
        )


# ---------------------------------------------------------------------------
# WorkflowUser — workflow lifecycle (weight 2)
# ---------------------------------------------------------------------------


class WorkflowUser(HttpUser):
    """
    Simulates a user that creates and manages multi-step workflows.

    Lifecycle:
        on_start  → register + login
        @task(2)  → create workflow
        @task(2)  → list workflows
        @task(1)  → get workflow status
        @task(1)  → start workflow
    """

    weight = 2
    wait_time = between(1.0, 3.0)

    def on_start(self) -> None:
        self._token: str = ""
        self._workflow_ids: list[str] = []

        email = _random_email()
        password = "LoadTest1!"

        self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "WF Load Tester"},
            name="/api/auth/register",
        )
        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="/api/auth/login",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")

    def _headers(self) -> dict[str, str]:
        return _auth_headers(self._token)

    @task(2)
    def create_workflow(self) -> None:
        """POST /api/workflows — create a 2-step workflow."""
        payload = {
            "name": f"LT Workflow {_random_string()}",
            "steps": [
                {
                    "step_name": "step-one",
                    "step_type": random.choice(_STEP_TYPES),
                    "input": {"condition": True},
                },
                {
                    "step_name": "step-two",
                    "step_type": random.choice(_STEP_TYPES),
                    "input": {"message": "load test step"},
                },
            ],
        }
        resp = self.client.post(
            "/api/workflows",
            json=payload,
            headers=self._headers(),
            name="/api/workflows [create]",
        )
        if resp.status_code == 201:
            wf_id = resp.json().get("id")
            if wf_id:
                self._workflow_ids.append(wf_id)
                if len(self._workflow_ids) > 10:
                    self._workflow_ids.pop(0)

    @task(2)
    def list_workflows(self) -> None:
        """GET /api/workflows — paginated list."""
        self.client.get(
            "/api/workflows",
            params={"limit": 10, "skip": 0},
            headers=self._headers(),
            name="/api/workflows [list]",
        )

    @task(1)
    def get_workflow(self) -> None:
        """GET /api/workflows/{id} — status check."""
        if not self._workflow_ids:
            return
        wf_id = random.choice(self._workflow_ids)
        self.client.get(
            f"/api/workflows/{wf_id}",
            headers=self._headers(),
            name="/api/workflows/{id} [get]",
        )

    @task(1)
    def start_workflow(self) -> None:
        """POST /api/workflows/{id}/start — start a pending workflow."""
        if not self._workflow_ids:
            return
        wf_id = random.choice(self._workflow_ids)
        self.client.post(
            f"/api/workflows/{wf_id}/start",
            headers=self._headers(),
            name="/api/workflows/{id}/start",
        )


# ---------------------------------------------------------------------------
# NotifyUser — notification inbox (weight 2)
# ---------------------------------------------------------------------------


class NotifyUser(HttpUser):
    """
    Simulates a user polling and reading their notification inbox.

    Lifecycle:
        on_start  → register + login
        @task(3)  → list notifications (with unread_only toggle)
        @task(1)  → mark all read
    """

    weight = 2
    wait_time = between(1.5, 4.0)

    def on_start(self) -> None:
        self._token: str = ""

        email = _random_email()
        password = "LoadTest1!"

        self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Notify LT"},
            name="/api/auth/register",
        )
        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="/api/auth/login",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")

    def _headers(self) -> dict[str, str]:
        return _auth_headers(self._token)

    @task(3)
    def list_notifications(self) -> None:
        """GET /api/notifications — poll inbox."""
        unread_only = random.choice([True, False])
        self.client.get(
            "/api/notifications",
            params={"limit": 20, "unread_only": str(unread_only).lower()},
            headers=self._headers(),
            name="/api/notifications [list]",
        )

    @task(1)
    def mark_all_read(self) -> None:
        """POST /api/notifications/read-all — clear unread count."""
        self.client.post(
            "/api/notifications/read-all",
            headers=self._headers(),
            name="/api/notifications/read-all",
        )


# ---------------------------------------------------------------------------
# AdminUser — admin operations (weight 1)
# ---------------------------------------------------------------------------


class AdminUser(HttpUser):
    """
    Simulates an admin user performing management operations.

    Uses credentials from environment variables (or defaults).
    Set LOCUST_ADMIN_EMAIL and LOCUST_ADMIN_PASSWORD before running.

    Lifecycle:
        on_start  → login as admin
        @task(2)  → list all tickets (all statuses)
        @task(1)  → health check
    """

    weight = 1
    wait_time = between(2.0, 5.0)

    def on_start(self) -> None:
        import os

        self._token: str = ""

        email = os.getenv("LOCUST_ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("LOCUST_ADMIN_PASSWORD", "AdminPass1!")

        # Attempt registration first (idempotent — 400 if already exists)
        self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": "Admin LT"},
            name="/api/auth/register [admin]",
        )

        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            name="/api/auth/login [admin]",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")

    def _headers(self) -> dict[str, str]:
        return _auth_headers(self._token)

    @task(2)
    def list_all_tickets(self) -> None:
        """GET /api/tickets — admin view across all statuses."""
        self.client.get(
            "/api/tickets",
            params={"limit": 50, "skip": 0},
            headers=self._headers(),
            name="/api/tickets [admin list]",
        )

    @task(1)
    def health_check(self) -> None:
        """GET /health — verify service is up."""
        with self.client.get("/health", catch_response=True, name="/health") as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") != "ONLINE":
                    resp.failure(f"Unexpected health status: {data.get('status')}")
            else:
                resp.failure(f"Health check returned {resp.status_code}")


# ---------------------------------------------------------------------------
# Entry point — allows running directly with `python locustfile.py`
# for quick syntax checking (does not start the Locust server).
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("SwarmEnterprise v2 — Locust load test file")
    print("Run with: locust -f locustfile.py --host http://localhost:8000")
    print("Users: TicketUser(5) WorkflowUser(2) NotifyUser(2) AdminUser(1)")
