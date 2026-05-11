# SOP: Lead Extraction & High-Value Targeting
**Status:** ACTIVE (v1.0)
**Owner:** GLOBAL_MARKET_FORCE

## Overview
Automated extraction of high-intent targets for the Sovereign Outreach engine.

## Procedures
1. **Identify Source:** Utilize the `BrowserAgentTool` to navigate to verified directories (Y-Combinator, TechCrunch, LinkedIn).
2. **Selector Validation:** Identify name, description, and contact metadata.
3. **Extraction:**
   - Scroll to trigger lazy-loading.
   - Extract up to 100 targets per cycle.
   - Sanitize company names (remove location suffixes).
4. **Storage:** Save to `data/customers/yc_targets.json`.
5. **Deduplication:** Check `SQLStore` for existing tax IDs or email signatures before adding.

## Quality Standards
- No "placeholder" names allowed.
- Descriptions must contain at least one value-prop keyword.
- Success rate must be > 95%.
