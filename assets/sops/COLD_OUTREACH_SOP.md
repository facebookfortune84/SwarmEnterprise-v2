# Sovereign Swarm Outreach Protocol (v2.0)

## Objective
Establish a perpetual, autonomous revenue generation engine by deploying a multi-agent swarm for high-precision B2B cold outreach. Transition from "batch-and-blast" to "signal-driven engagement."

## The Swarm Architecture (Signal Stacking)
Based on successful case studies (ElevateSells, Snov.io), our outreach swarm operates as a coordinated unit:

1.  **The Scout (OSINT Agent)**
    *   **Role:** Identifies high-value targets and *trigger events* (funding, hiring, new tech stack).
    *   **Tools:** `osint_recon` (crt.sh, WHOIS), `lead_scraper`.
    *   **Output:** Enriched Lead Profile (Name, Email, Tech Stack, Recent News).

2.  **The Ghostwriter (Copywriting Agent)**
    *   **Role:** Crafts hyper-personalized emails using NLP to bypass spam filters and engage the "Crocodile Brain" (survival/greed).
    *   **Tools:** `email_gen` (LLM), `marketing_tools`.
    *   **Strategy:** "Challenger Sale" - disruptive insight -> problem agitation -> Sovereign solution.
    *   **Metric:** Reply Rate > 12%.

3.  **The Courier (Delivery Agent)**
    *   **Role:** Manages SMTP infrastructure (`robertdemottojr83@gmail.com`) to ensure deliverability.
    *   **Tools:** `smtp_outreach`.
    *   **Rules:**
        *   Max 50 emails/day per inbox (warm-up phase).
        *   Randomized sleep intervals (3-15 mins).
        *   Text-only first touch (no links) to boost inbox placement.

4.  **The Closer (Sentiment Agent)**
    *   **Role:** Monitors inbox for replies.
    *   **Logic:**
        *   *Positive:* Auto-book meeting or send Stripe Payment Link.
        *   *Negative:* Remove from list.
        *   *OOO:* Reschedule follow-up.

## Operational Workflow (Continuous Daemon)

The `continuous_outreach_daemon.py` implements this protocol:

1.  **Ingest:** Load fresh leads from `data/customers/leads.json`.
2.  **Enrich:** (Future) Use OSINT tools to verify domain and find tech stack.
3.  **Synthesize:** Generate email content targeting the specific founder/role.
4.  **Dispatch:** Send via SMTP.
5.  **Log:** Record interaction in `data/marketing/outreach_log.json`.

## Success Benchmarks
| Metric | Target | Verified Swarm Average |
| :--- | :--- | :--- |
| **Open Rate** | > 60% | 40-70% |
| **Reply Rate** | > 15% | 12-18% |
| **Conversion** | > 3% | 3-5% |

## Next Steps
- Implement "The Closer" logic (Inbox Monitoring).
- Integrate `osint_recon` into the enrichment phase of the daemon.
- Scale volume by adding secondary SMTP accounts.
