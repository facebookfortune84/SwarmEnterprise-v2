# GDPR Compliance Guide

**SwarmEnterprise v2 — RWV Techsolutions LLC**
1091 Harrison Ave, Elkins, WV 26241, USA
DPO / Contact: robertdemottojr50@gmail.com

---

## Table of Contents

1. [Data Inventory](#1-data-inventory)
2. [Legal Basis per Data Category](#2-legal-basis-per-data-category)
3. [User Rights & API Endpoints](#3-user-rights--api-endpoints)
4. [Data Breach Procedure](#4-data-breach-procedure)
5. [DPO Contact](#5-dpo-contact)

---

## 1. Data Inventory

The following table lists every field in the application database that constitutes personal data or is otherwise subject to GDPR consideration.

| Field | Model (Table) | Category | Purpose | Retention |
|---|---|---|---|---|
| `email` | `User` (`users`) | Identity / contact | Login credential, transactional email | Duration of service + 30 days post-deletion |
| `full_name` | `User` (`users`) | Identity | Display name, account personalisation | Duration of service + 30 days post-deletion |
| `password_hash` | `User` (`users`) | Credential | bcrypt hash used for authentication — **plaintext never stored** | Duration of service + 30 days post-deletion |
| `role` | `User` (`users`) | Access control | RBAC enforcement | Duration of service + 30 days post-deletion |
| `subscription_tier` | `User` (`users`) | Billing metadata | Determine feature access | Duration of service + 30 days post-deletion |
| `is_active` | `User` (`users`) | Account state | Enable / disable platform access | Duration of service + 30 days post-deletion |
| `created_at`, `updated_at` | `User` (`users`) | Audit | Account lifecycle timestamps | Duration of service + 30 days post-deletion |
| `key` | `APIKey` (`api_keys`) | Credential | Programmatic API access token | Deleted with user account; expired keys purged within 30 days |
| `user_id` | `APIKey` (`api_keys`) | Linkage | Associates key to user | Deleted with user account |
| `last_used_at` | `APIKey` (`api_keys`) | Audit | Security monitoring | Deleted with user account |
| `email` | `Lead` (`leads`) | Contact | Outreach and CRM pipeline | 2 years from capture, then purged |
| `name` | `Lead` (`leads`) | Identity | CRM enrichment | 2 years from capture, then purged |
| `company` | `Lead` (`leads`) | Organisation | CRM enrichment | 2 years from capture, then purged |
| `customer_email` | `Project` (`projects`) | Billing contact | Associate Stripe session to purchaser | 7 years (US tax obligation) |
| `metadata_json` | `UsageEvent` (`usage_events`) | Telemetry | May contain IP address; used for rate-limiting and analytics | 90 days from event timestamp |
| `event_type`, `amount` | `UsageEvent` (`usage_events`) | Telemetry | Platform analytics, billing verification | 90 days from event timestamp |
| Server / access logs | Hosting infrastructure | Technical | Security, rate-limiting | 90 days via log rotation |

### Data Not Stored

- Raw credit card numbers, CVV, or full PANs — handled exclusively by Stripe.
- Plaintext passwords — only bcrypt hashes are stored.
- Persistent browser cookies or tracking pixels.

---

## 2. Legal Basis per Data Category

All processing is grounded in one or more GDPR Article 6 lawful bases.

| Data Category | Lawful Basis | GDPR Article |
|---|---|---|
| Account & identity data (`User`) | **Performance of a contract** — necessary to create and maintain user accounts | Art. 6(1)(b) |
| API credentials (`APIKey`) | **Performance of a contract** — necessary for programmatic access to the subscribed service | Art. 6(1)(b) |
| Payment & billing data (`Project`) | **Performance of a contract** and **legal obligation** (US tax record retention) | Art. 6(1)(b) and (c) |
| Usage & telemetry events (`UsageEvent`) | **Legitimate interests** — security monitoring, abuse prevention, platform performance analytics | Art. 6(1)(f) |
| Lead contact data (`Lead`) | **Legitimate interests** (B2B outreach); **consent** where required by local law (e.g., ePrivacy) | Art. 6(1)(f) / (a) |
| Server / infrastructure logs | **Legitimate interests** — fraud prevention, DDoS mitigation, audit trail | Art. 6(1)(f) |

### Legitimate Interests Assessment (LIA) Summary

For processing based on legitimate interests (Art. 6(1)(f)), we have assessed:

1. **Purpose test** — the interests are specific, real, and not trivial (security, fraud, operational analytics).
2. **Necessity test** — processing is limited to what is required; telemetry events are aggregated and purged after 90 days.
3. **Balancing test** — data subjects can reasonably expect this processing; they can object at any time (see §3).

---

## 3. User Rights & API Endpoints

GDPR grants data subjects the following rights. SwarmEnterprise v2 exposes authenticated API endpoints for self-service exercise of the most common rights.

### 3.1 Right of Access (Art. 15)

**What it means:** Users can obtain confirmation of whether we process their data and receive a copy.

**Self-service endpoint:**

```http
GET /api/user/export
Authorization: Bearer <access_token>
```

**Response (HTTP 200):**

```json
{
  "user": {
    "id": "...",
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "role": "user",
    "subscription_tier": "pro",
    "is_active": true,
    "created_at": "2026-01-15T10:00:00",
    "updated_at": "2026-05-01T08:30:00"
  },
  "api_keys": [ ... ],
  "usage_events": [ ... ]
}
```

> Note: `password_hash` is excluded from the export.

**Manual route:** Email robertdemottojr50@gmail.com — response within 30 days.

---

### 3.2 Right to Rectification (Art. 16)

**What it means:** Users can correct inaccurate personal data.

**Self-service endpoint:**

```http
PUT /api/users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "Updated Name",
  "email": "new@example.com"
}
```

**Manual route:** Email robertdemottojr50@gmail.com.

---

### 3.3 Right to Erasure / "Right to Be Forgotten" (Art. 17)

**What it means:** Users can request deletion of their personal data when processing is no longer necessary, consent is withdrawn, or they object.

**Self-service endpoint:**

```http
DELETE /api/user/account
Authorization: Bearer <access_token>
```

**Response:** HTTP 204 No Content

**What is deleted:**

| Record | Action |
|---|---|
| `User` row | Permanently deleted |
| All `APIKey` rows for this user | Permanently deleted |
| All `UsageEvent` rows for this user | Permanently deleted |
| `Project` / `Lead` rows | **Retained** per legal obligation (7 years for billing; see §2) or retention schedule (2 years for leads) — can be flagged for anonymisation on request |

> ⚠ **This action is irreversible.** There is no soft-delete or recovery window.

**Manual route:** Email robertdemottojr50@gmail.com with subject "Account Deletion Request" — completed within 30 days.

---

### 3.4 Right to Data Portability (Art. 20)

The `GET /api/user/export` endpoint (§3.1) returns data in structured, machine-readable JSON format, satisfying Art. 20 portability requirements.

---

### 3.5 Right to Object (Art. 21)

Where processing is based on legitimate interests (Art. 6(1)(f)) — specifically usage telemetry — users may object.

**How to exercise:** Email robertdemottojr50@gmail.com with subject "Objection to Processing." We will cease the specific processing within 30 days unless we can demonstrate compelling legitimate grounds.

---

### 3.6 Right to Restrict Processing (Art. 18)

Users may request restriction of processing while a rights dispute is pending.

**How to exercise:** Email robertdemottojr50@gmail.com with subject "Restriction of Processing Request."

---

### 3.7 Right to Withdraw Consent (Art. 7(3))

For any processing based on consent (e.g., marketing email to leads), consent may be withdrawn at any time without detriment.

**How to exercise:** Unsubscribe link in emails, or email robertdemottojr50@gmail.com.

---

### Response Time Commitment

| Request Type | Target Response |
|---|---|
| Acknowledgement | Within 5 business days |
| Full response / completion | Within 30 calendar days |
| Extension (complex requests) | Up to 90 days with prior notification |

---

## 4. Data Breach Procedure

### 4.1 Detection & Triage

1. Any team member who identifies a potential breach must **immediately** notify the DPO at robertdemottojr50@gmail.com and create a private incident ticket.
2. Assess within **4 hours**:
   - Nature and scope of the breach (what data, how many records, what systems).
   - Whether personal data was involved.
   - Whether the breach is ongoing.

### 4.2 Containment

1. Isolate affected systems, rotate compromised credentials, and revoke affected JWT tokens / API keys.
2. Preserve logs and evidence — do not delete or overwrite.
3. Apply patches or configuration changes to prevent recurrence.

### 4.3 GDPR Notification Obligations

| Threshold | Obligation | Deadline |
|---|---|---|
| Breach likely to result in risk to individuals | Notify supervisory authority | **Within 72 hours** of becoming aware (Art. 33) |
| Breach likely to result in **high** risk to individuals | Notify affected data subjects directly | **Without undue delay** (Art. 34) |
| Low-risk breach | Document internally only | Within 30 days |

**Supervisory authority for US-based controller (EEA users):**
Where no EU establishment exists, EEA users may direct complaints to the supervisory authority of their EU member state. The lead authority for international transfers under SCCs is the authority in the country of the EU-based data subject.

### 4.4 Supervisory Authority Notification Content (Art. 33)

The notification must include:

- Nature of the breach (categories and approximate number of records/individuals affected).
- Name and contact details of DPO.
- Likely consequences of the breach.
- Measures taken or proposed to address the breach.

### 4.5 Data-Subject Notification Content (Art. 34)

Where required, communicate in plain language:

- Description of the breach.
- Name and contact details of DPO.
- Likely consequences.
- Steps taken to address the breach and mitigate its effects.
- Recommendations for individuals to protect themselves.

### 4.6 Post-Incident Review

Within 14 days of containment:

1. Conduct a root-cause analysis.
2. Update the breach register (internal document).
3. Review and update technical or organisational measures.
4. Brief all relevant team members.

---

## 5. DPO Contact

For all data protection matters, rights requests, breach notifications, or GDPR enquiries:

```
Data Protection Officer
RWV Techsolutions LLC
1091 Harrison Ave
Elkins, WV 26241
United States of America

Email: robertdemottojr50@gmail.com
```

Response target: **5 business days** for initial acknowledgement, **30 days** for full response.

---

*Last updated: May 28, 2026*
