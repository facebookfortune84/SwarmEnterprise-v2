# SOP: Cold Outreach Execution (Stream 12)
**Status:** ACTIVE (v1.0)
**Owner:** GLOBAL_MARKET_FORCE

## Overview
High-deliverability SMTP/Gmail outreach utilizing the Jarvis 3.5 Oracle copy.

## Procedures
1. **Target Loading:** Fetch targets from `data/customers/yc_targets.json`.
2. **Persona Adoption:** Randomly select an Oracle Persona (e.g., Perplexity Journalist, GPT-5 Master).
3. **Copy Generation:** 
   - Inject the target name and description into the Jarvis 3.5 HTML template.
   - Tone must align with the adopted persona.
4. **Dispatch:**
   - Use `SMTPOutreachTool` (SSL Port 465).
   - Log message IDs to Telemetry.
5. **Rate Limiting:** Do not exceed 50 dispatches per hour per node.

## Verification
- Monitor `verify_first_payment.py` for conversion signals.
- Success = Verified Stripe checkout session.
