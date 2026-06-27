# SwarmEnterprise v2 — Assets Workforce Access Guide

> **Version:** 1.0 | **Maintained by:** INTEGRITY_SHIELD | **Last updated:** 2025-05-07

This document is the single entry point for every agent and developer working with the `assets/` directory. It catalogs all SOPs, prompts, and tool files, explains the consumption protocol, and provides a quick-reference matrix so you can reach the right asset in seconds.

---

## Table of Contents

1. [Folder Structure Overview](#1-folder-structure-overview)
2. [SOP Index](#2-sop-index)
   - [GOV — Governance](#gov--governance)
   - [TEC — Technical Operations](#tec--technical-operations)
   - [SEC — Security](#sec--security)
   - [MKT — Marketing](#mkt--marketing)
   - [MON — Monetization](#mon--monetization)
   - [OPS — Operations (Unlabelled Legacy)](#ops--operations-unlabelled-legacy)
3. [Prompt Index](#3-prompt-index)
4. [Tool File Index](#4-tool-file-index)
5. [Asset Consumption Protocol](#5-asset-consumption-protocol)
6. [Quick Reference — Scenario → SOP Matrix](#6-quick-reference--scenario--sop-matrix)

---

## 1. Folder Structure Overview

```
assets/
├── ASSETS_README.md          ← This file (workforce access guide)
├── registry.json             ← Machine-readable index of all assets
│
├── sops/                     ← Standard Operating Procedures (50 files)
│   ├── GOV_001 – GOV_007     ← Governance & orchestration
│   ├── TEC_001 – TEC_010     ← Technical / infrastructure
│   ├── SEC_001 – SEC_010     ← Security & compliance
│   ├── MKT_001 – MKT_010     ← Marketing & content
│   ├── MON_001 – MON_013     ← Monetization streams
│   └── (legacy unlabelled)   ← COLD_OUTREACH_SOP, LEAD_EXTRACTION,
│                                OUTREACH_EXECUTION, SELF_HEALING,
│                                TRAFFIC_DOMINANCE_v1
│
├── prompts/                  ← System & action prompts (57 files)
│   ├── Model-specific        ← gpt-5*, gpt-4*, claude-*, gemini-*
│   ├── Agent lifecycle       ← Agent Prompt*, Agent loop, Poke*
│   ├── Action handlers       ← *Action.txt
│   └── Utility               ← chat-titles, planning-mode, etc.
│
└── tools/                    ← Tool-definition JSON files (8 files)
    ├── Agent Tools.json       ← Primary swarm tool manifest
    ├── Builder Tools.json     ← Builder/deploy tool set
    ├── claude-4-sonnet-tools.json
    ├── gpt-5-tools.json
    ├── phase_mode_tools.json  ← Phase-modal tool restrictions
    ├── plan_mode_tools.json   ← Planning-only tool set
    ├── Tools.json             ← Base/fallback tool manifest
    └── Agent Tools v1.0.json  ← Archived v1 tool manifest
```

---

## 2. SOP Index

All SOPs share a common 5-step execution skeleton (see §5). Each table row links to the file and states its one-sentence purpose and the trigger condition.

### GOV — Governance

| ID | File | Description | When to Use |
|----|------|-------------|-------------|
| GOV_001 | [`sops/GOV_001_TICKET_ISSUANCE.md`](sops/GOV_001_TICKET_ISSUANCE.md) | Standard for generating verifiable work orders for all swarm tasks. | Every time a new task is created or delegated to an agent. |
| GOV_002 | [`sops/GOV_002_PERSONA_RESONANCE.md`](sops/GOV_002_PERSONA_RESONANCE.md) | How agents autonomously select the most effective Oracle persona. | Before an agent begins any execution cycle requiring a persona assignment. |
| GOV_003 | [`sops/GOV_003_REVENUE_RECONCILIATION.md`](sops/GOV_003_REVENUE_RECONCILIATION.md) | Syncing Stripe event logs with internal SQLStore records. | Daily or after any Stripe webhook is received. |
| GOV_004 | [`sops/GOV_004_AUTONOMOUS_BACKLOG.md`](sops/GOV_004_AUTONOMOUS_BACKLOG.md) | Algorithm for filling idle time with high-priority maintenance. | Whenever an agent has no active ticket and is awaiting new assignments. |
| GOV_005 | [`sops/GOV_005_TASK_PRIORITIZATION.md`](sops/GOV_005_TASK_PRIORITIZATION.md) | Logic for assigning Critical/High priority tags based on ROI. | When the backlog contains more tasks than available agent slots. |
| GOV_006 | [`sops/GOV_006_AGENT_ONBOARDING.md`](sops/GOV_006_AGENT_ONBOARDING.md) | Steps for tax ID issuance and wage tier assignment. | When a new agent persona is being registered for the first time. |
| GOV_007 | [`sops/GOV_007_LINEAGE_SIGNATURE.md`](sops/GOV_007_LINEAGE_SIGNATURE.md) | Cryptographic signing of all agent-generated artifacts. | After every artifact (file, email, report) is produced by any agent. |

### TEC — Technical Operations

| ID | File | Description | When to Use |
|----|------|-------------|-------------|
| TEC_001 | [`sops/TEC_001_DB_SCHEMA_MIGRATION.md`](sops/TEC_001_DB_SCHEMA_MIGRATION.md) | Safely applying SQL patches via the Self-Healing service. | Before executing any ALTER TABLE or schema change on production databases. |
| TEC_002 | [`sops/TEC_002_DEPENDENCY_AUDIT.md`](sops/TEC_002_DEPENDENCY_AUDIT.md) | Weekly scan of `requirements.txt` for vulnerabilities and updates. | Every Monday morning or after any new Python package is added. |
| TEC_003 | [`sops/TEC_003_LOG_ROTATION.md`](sops/TEC_003_LOG_ROTATION.md) | Pruning `swarm_activity.log` once it exceeds 100 MB threshold. | Triggered automatically when log file size breaches 100 MB. |
| TEC_004 | [`sops/TEC_004_RAG_MEMORY_INDEXING.md`](sops/TEC_004_RAG_MEMORY_INDEXING.md) | Cleaning and re-embedding `sovereign_memory.json` every 24 hours. | Every 24-hour maintenance cycle or after memory corruption is detected. |
| TEC_005 | [`sops/TEC_005_DOCKER_CONTAINER_UPKEEP.md`](sops/TEC_005_DOCKER_CONTAINER_UPKEEP.md) | Pruning orphaned Docker images and volumes to maintain disk health. | Weekly or when disk utilization exceeds 80 %. |
| TEC_006 | [`sops/TEC_006_API_KEY_ROTATION.md`](sops/TEC_006_API_KEY_ROTATION.md) | Safety protocol for rotating Stripe and Groq keys without downtime. | Every 90 days or immediately after any suspected key exposure. |
| TEC_007 | [`sops/TEC_007_ERROR_HANDLING_HARDENING.md`](sops/TEC_007_ERROR_HANDLING_HARDENING.md) | Wrapping tool calls in Pydantic-validated try/except blocks. | During any code review or when new tool integrations are being written. |
| TEC_008 | [`sops/TEC_008_CODE_COMPILATION_TEST.md`](sops/TEC_008_CODE_COMPILATION_TEST.md) | Running `compileall` before every Vanguard deployment. | Mandatory gate before every production deploy. |
| TEC_009 | [`sops/TEC_009_SUBMODULE_SYNC.md`](sops/TEC_009_SUBMODULE_SYNC.md) | Aligning primary core with `core_secondary` assets. | After any `git submodule update` or cross-repo merge. |
| TEC_010 | [`sops/TEC_010_TELEMETRY_DASHBOARD.md`](sops/TEC_010_TELEMETRY_DASHBOARD.md) | Aggregating latency and wage metrics for the weekly audit. | Every Sunday for the weekly performance review cycle. |

### SEC — Security

| ID | File | Description | When to Use |
|----|------|-------------|-------------|
| SEC_001 | [`sops/SEC_001_SECRET_PROTECTION.md`](sops/SEC_001_SECRET_PROTECTION.md) | Ban on logging or committing `.env` variables or API keys. | Always active; enforced as a pre-commit hook and before every log write. |
| SEC_002 | [`sops/SEC_002_SANDBOX_ENFORCEMENT.md`](sops/SEC_002_SANDBOX_ENFORCEMENT.md) | Mandatory use of Docker for untested agent-generated code. | Before running any LLM-generated script outside a verified module. |
| SEC_003 | [`sops/SEC_003_PHISHING_DEFENSE.md`](sops/SEC_003_PHISHING_DEFENSE.md) | Verifying sender reputation before processing incoming webhook payloads. | On every inbound webhook or email-triggered automation event. |
| SEC_004 | [`sops/SEC_004_IP_REPUTATION_MANAGEMENT.md`](sops/SEC_004_IP_REPUTATION_MANAGEMENT.md) | Monitoring SMTP relay health to prevent blacklisting. | Daily SMTP health check and after any deliverability complaint. |
| SEC_005 | [`sops/SEC_005_DATA_PRIVACY_GDPR.md`](sops/SEC_005_DATA_PRIVACY_GDPR.md) | Handling PII (emails/names) according to global standards. | Whenever PII is collected, stored, transferred, or deleted. |
| SEC_006 | [`sops/SEC_006_INJECTION_PREVENTION.md`](sops/SEC_006_INJECTION_PREVENTION.md) | Sanitizing LLM outputs before passing them to shell or DB tools. | Before any LLM-produced string is executed as a command or SQL query. |
| SEC_007 | [`sops/SEC_007_RATE_LIMITING_SMTP.md`](sops/SEC_007_RATE_LIMITING_SMTP.md) | Strict 50-email-per-hour limit to maintain Gmail standing. | During all outbound email campaigns and cold outreach loops. |
| SEC_008 | [`sops/SEC_008_STASIS_BRANCH_LOCK.md`](sops/SEC_008_STASIS_BRANCH_LOCK.md) | No-manual-edit policy for the archival stasis branch. | When any change to the `stasis` Git branch is attempted. |
| SEC_009 | [`sops/SEC_009_VIRTUAL_ENV_ISOLATION.md`](sops/SEC_009_VIRTUAL_ENV_ISOLATION.md) | Ensuring all swarm nodes run in dedicated virtual environments. | During agent provisioning and before any dependency installation. |
| SEC_010 | [`sops/SEC_010_AUDIT_TRAIL_INTEGRITY.md`](sops/SEC_010_AUDIT_TRAIL_INTEGRITY.md) | Protecting activity logs from unauthorized modification. | Continuously; verified after each write and during weekly audits. |

### MKT — Marketing

| ID | File | Description | When to Use |
|----|------|-------------|-------------|
| MKT_001 | [`sops/MKT_001_TIKTOK_VIRALITY.md`](sops/MKT_001_TIKTOK_VIRALITY.md) | Hook-Value-CTA framework for sub-60-second short-form video scripts. | When generating TikTok or Reels scripts for any campaign. |
| MKT_002 | [`sops/MKT_002_LINKEDIN_AUTHORITY.md`](sops/MKT_002_LINKEDIN_AUTHORITY.md) | Structure for technical long-form posts to drive enterprise leads. | When publishing LinkedIn thought-leadership content. |
| MKT_003 | [`sops/MKT_003_EMAIL_COPYWRITING.md`](sops/MKT_003_EMAIL_COPYWRITING.md) | Principles of the Jarvis 3.5 conversion-sharding email template. | When writing cold or nurture email sequences. |
| MKT_004 | [`sops/MKT_004_AD_COPY_PPC.md`](sops/MKT_004_AD_COPY_PPC.md) | A/B testing guidelines for high-CTR Facebook and Google ad headlines. | Before launching any paid ad campaign or split test. |
| MKT_005 | [`sops/MKT_005_SEO_KEYWORD_RESEARCH.md`](sops/MKT_005_SEO_KEYWORD_RESEARCH.md) | Identifying low-difficulty, high-intent keywords for immediate ranking. | At the start of any SEO content sprint or niche-site launch. |
| MKT_006 | [`prompts/MKT_006_IMAGE_GEN_PROMPTING.md`](prompts/MKT_006_IMAGE_GEN_PROMPTING.md) | Guidelines for crafting high-fidelity image-generation prompts for campaigns. | When producing visual assets via AI image models. |
| MKT_007 | [`sops/MKT_007_VIDEO_EDITING_DIRECTION.md`](sops/MKT_007_VIDEO_EDITING_DIRECTION.md) | Scene-by-scene instructions for autonomous video assembly. | When directing an AI video-editing pipeline. |
| MKT_008 | [`sops/MKT_008_SOCIAL_MEDIA_BROADCAST.md`](sops/MKT_008_SOCIAL_MEDIA_BROADCAST.md) | Multiplexer schedule for omni-channel presence (FB, X, LinkedIn). | When scheduling or dispatching cross-platform social posts. |
| MKT_009 | [`sops/MKT_009_LEAD_NURTURE_SEQUENCE.md`](sops/MKT_009_LEAD_NURTURE_SEQUENCE.md) | 7-day auto-responder logic for email subscribers. | When setting up or reviewing a drip/nurture email sequence. |
| MKT_010 | [`sops/MKT_010_BRAND_VOICE_ALIGNMENT.md`](sops/MKT_010_BRAND_VOICE_ALIGNMENT.md) | Ensuring all content sounds like the Sovereign Architect persona. | Before publishing any written asset to verify brand consistency. |

### MON — Monetization

| ID | File | Description | When to Use |
|----|------|-------------|-------------|
| MON_001 | [`sops/MON_001_AFFILIATE_ARBITRAGE.md`](sops/MON_001_AFFILIATE_ARBITRAGE.md) | Procedure for scraping TikTok Shop and ClickFunnels links and generating viral bridge pages. | When running affiliate arbitrage campaigns. |
| MON_002 | [`sops/MON_002_API_SAAS_BILLING.md`](sops/MON_002_API_SAAS_BILLING.md) | Standard for provisioning API keys and setting up Stripe metered billing. | When onboarding a new SaaS API customer or plan tier. |
| MON_003 | [`sops/MON_003_LEAD_GEN_BROKER.md`](sops/MON_003_LEAD_GEN_BROKER.md) | Workflow for extracting B2B leads and selling them to verified high-ticket partners. | When executing a lead-gen brokerage cycle. |
| MON_004 | [`sops/MON_004_DIGITAL_PRODUCT_STORE.md`](sops/MON_004_DIGITAL_PRODUCT_STORE.md) | Protocol for generating and listing Brand Kits and Strategy Guides on the Sovereign Store. | When creating or updating digital products for sale. |
| MON_005 | [`sops/MON_005_NEWSLETTER_SPONSORSHIP.md`](sops/MON_005_NEWSLETTER_SPONSORSHIP.md) | Guidelines for pitching newsletter ad slots to AI vendors and SaaS founders. | When monetizing the newsletter through paid sponsorships. |
| MON_006 | [`sops/MON_006_PRINT_ON_DEMAND.md`](sops/MON_006_PRINT_ON_DEMAND.md) | Workflow for generating AI art and listing it on integrated POD platforms. | When producing and publishing print-on-demand products. |
| MON_007 | [`sops/MON_007_PROGRAMMATIC_ADS.md`](sops/MON_007_PROGRAMMATIC_ADS.md) | Standard for ad-injection into auto-generated SEO blog posts. | When monetizing content sites with programmatic advertising. |
| MON_008 | [`sops/MON_008_CRYPTO_YIELD_FARMING.md`](sops/MON_008_CRYPTO_YIELD_FARMING.md) | Safety protocol for analyzing DeFi rates and posting risk-adjusted alerts. | When the treasury agent evaluates DeFi yield opportunities. |
| MON_009 | [`sops/MON_009_PAID_COMMUNITY.md`](sops/MON_009_PAID_COMMUNITY.md) | Onboarding flow for Discord/Telegram premium community members. | When a new paid-community subscriber activates their membership. |
| MON_010 | [`sops/MON_010_DATA_LICENSING.md`](sops/MON_010_DATA_LICENSING.md) | Drafting enterprise agreements for RAG-memory datasets. | When negotiating or renewing data-licensing contracts. |
| MON_011 | [`sops/MON_011_SEO_TRAFFIC.md`](sops/MON_011_SEO_TRAFFIC.md) | Daily generation of 5 high-intent blog posts with ad-conversion hooks. | During the daily SEO content generation cycle. |
| MON_012 | [`sops/MON_012_COLD_OUTREACH.md`](sops/MON_012_COLD_OUTREACH.md) | Execution of high-deliverability SMTP sequences using Oracle personas. | When launching an outbound cold-email monetization sequence. |
| MON_013 | [`sops/MON_013_FAST_DEPLOY.md`](sops/MON_013_FAST_DEPLOY.md) | Protocol for spinning up new niche monetization sites in under 5 minutes. | When a new niche-site opportunity needs rapid deployment. |

### OPS — Operations (Unlabelled Legacy)

These SOPs pre-date the formal ID scheme but remain authoritative references.

| File | Description | When to Use |
|------|-------------|-------------|
| [`sops/COLD_OUTREACH_SOP.md`](sops/COLD_OUTREACH_SOP.md) | Perpetual autonomous B2B cold-outreach engine — multi-agent signal-driven engagement protocol (v2.0). | Legacy outreach campaigns or when MON_012 needs detailed scaffolding. |
| [`sops/LEAD_EXTRACTION.md`](sops/LEAD_EXTRACTION.md) | High-value B2B lead extraction and targeting (Stream 12 sub-process). | When performing targeted list building and lead scoring. |
| [`sops/OUTREACH_EXECUTION.md`](sops/OUTREACH_EXECUTION.md) | Cold outreach execution playbook — Stream 12 operations (v1.0). | When operationalizing an outreach stream end-to-end. |
| [`sops/SELF_HEALING.md`](sops/SELF_HEALING.md) | Autonomous self-healing and upkeep orchestration owned by INTEGRITY_SHIELD (v1.0). | When a node failure, error loop, or schema inconsistency is detected. |
| [`sops/TRAFFIC_DOMINANCE_v1.md`](sops/TRAFFIC_DOMINANCE_v1.md) | Programmatic SEO and traffic capture protocol targeting immediate sales conversion (v1.0). | When launching a new content-driven traffic acquisition campaign. |

---

## 3. Prompt Index

Prompts are the system instructions injected at runtime for each model and task mode.

### Model-Specific Prompts

| File | Model / Target | Purpose |
|------|---------------|---------|
| [`prompts/gpt-5.txt`](prompts/gpt-5.txt) | GPT-5 | Primary GPT-5 system prompt (text format). |
| [`prompts/gpt-5.yaml`](prompts/gpt-5.yaml) | GPT-5 | GPT-5 system prompt in YAML deployment format. |
| [`prompts/gpt-5-mini.txt`](prompts/gpt-5-mini.txt) | GPT-5 Mini | Lightweight variant for fast / low-cost GPT-5 tasks. |
| [`prompts/gpt-5-agent-prompts.txt`](prompts/gpt-5-agent-prompts.txt) | GPT-5 Agents | Multi-agent role definitions for GPT-5 swarm nodes. |
| [`prompts/gpt-4.1.txt`](prompts/gpt-4.1.txt) | GPT-4.1 | System prompt for GPT-4.1 reasoning tasks. |
| [`prompts/gpt-4o.txt`](prompts/gpt-4o.txt) | GPT-4o | Optimized instruction set for GPT-4o multimodal use. |
| [`prompts/claude-4-sonnet.yaml`](prompts/claude-4-sonnet.yaml) | Claude 4 Sonnet | YAML-format system prompt for Claude 4 Sonnet. |
| [`prompts/claude-4-sonnet-agent-prompts.txt`](prompts/claude-4-sonnet-agent-prompts.txt) | Claude 4 Sonnet Agents | Multi-agent role definitions for Claude Sonnet nodes. |
| [`prompts/claude-sonnet-4.txt`](prompts/claude-sonnet-4.txt) | Claude Sonnet 4 | Alternate text-format prompt for Claude Sonnet 4. |
| [`prompts/Claude Code 2.0.txt`](prompts/Claude%20Code%202.0.txt) | Claude Code | Engineering-mode prompt for Claude coding sessions. |
| [`prompts/Sonnet 4.5 Prompt.txt`](prompts/Sonnet%204.5%20Prompt.txt) | Claude Sonnet 4.5 | System prompt for Sonnet 4.5 preview builds. |
| [`prompts/gemini-2.5-pro.txt`](prompts/gemini-2.5-pro.txt) | Gemini 2.5 Pro | System prompt for Gemini 2.5 Pro tasks. |
| [`prompts/gemini-cli-system-prompt.txt`](prompts/gemini-cli-system-prompt.txt) | Gemini CLI | CLI-mode system prompt for Gemini. |
| [`prompts/google-gemini-cli-system-prompt.txt`](prompts/google-gemini-cli-system-prompt.txt) | Gemini CLI (Google) | Google-branded Gemini CLI system prompt variant. |
| [`prompts/openai-codex-cli-system-prompt-20250820.txt`](prompts/openai-codex-cli-system-prompt-20250820.txt) | OpenAI Codex CLI | CLI system prompt for OpenAI Codex (Aug 2025 build). |
| [`prompts/AI Studio vibe-coder.txt`](prompts/AI%20Studio%20vibe-coder.txt) | AI Studio | Vibe-coder mode for Google AI Studio sessions. |

### Agent Lifecycle Prompts

| File | Purpose |
|------|---------|
| [`prompts/Agent Prompt.txt`](prompts/Agent%20Prompt.txt) | Base agent system prompt (baseline swarm identity). |
| [`prompts/Agent Prompt v1.0.txt`](prompts/Agent%20Prompt%20v1.0.txt) | v1.0 archived agent prompt. |
| [`prompts/Agent Prompt v1.2.txt`](prompts/Agent%20Prompt%20v1.2.txt) | v1.2 agent prompt with minor refinements. |
| [`prompts/Agent Prompt 2.0.txt`](prompts/Agent%20Prompt%202.0.txt) | v2.0 major revision of the core agent prompt. |
| [`prompts/Agent Prompt 2025-09-03.txt`](prompts/Agent%20Prompt%202025-09-03.txt) | Dated snapshot of the agent prompt (Sep 3 2025). |
| [`prompts/Agent CLI Prompt 2025-08-07.txt`](prompts/Agent%20CLI%20Prompt%202025-08-07.txt) | CLI-specific agent prompt snapshot (Aug 7 2025). |
| [`prompts/Agent loop.txt`](prompts/Agent%20loop.txt) | Defines the agent's autonomous task-loop behaviour. |
| [`prompts/Enterprise Prompt.txt`](prompts/Enterprise%20Prompt.txt) | Enterprise-tier agent prompt with expanded tooling. |
| [`prompts/Builder Prompt.txt`](prompts/Builder%20Prompt.txt) | Prompt for the Builder persona (code & deploy focus). |
| [`prompts/Poke agent.txt`](prompts/Poke%20agent.txt) | Wake/nudge prompt to re-activate a stalled agent. |
| [`prompts/Poke_p1.txt`](prompts/Poke_p1.txt) – [`prompts/Poke_p6.txt`](prompts/Poke_p6.txt) | Sequential poke-phase prompts (p1–p6) for multi-step agent reactivation. |

### Action Handler Prompts

| File | Handler |
|------|---------|
| [`prompts/DocumentAction.txt`](prompts/DocumentAction.txt) | Drives the DocumentAction agent module. |
| [`prompts/ExplainAction.txt`](prompts/ExplainAction.txt) | Drives the ExplainAction agent module. |
| [`prompts/MessageAction.txt`](prompts/MessageAction.txt) | Drives the MessageAction agent module. |
| [`prompts/PlaygroundAction.txt`](prompts/PlaygroundAction.txt) | Drives the PlaygroundAction sandbox module. |
| [`prompts/PreviewAction.txt`](prompts/PreviewAction.txt) | Drives the PreviewAction render module. |
| [`prompts/Quest Action.txt`](prompts/Quest%20Action.txt) | Drives the Quest execution action module. |
| [`prompts/Quest Design.txt`](prompts/Quest%20Design.txt) | System prompt for designing Quest structures. |

### Mode & Utility Prompts

| File | Purpose |
|------|---------|
| [`prompts/planning-mode.txt`](prompts/planning-mode.txt) | Restricts agent to planning-only (no execution). |
| [`prompts/phase_mode_prompts.txt`](prompts/phase_mode_prompts.txt) | Phase-modal prompt switching definitions. |
| [`prompts/Mode_Clasifier_Prompt.txt`](prompts/Mode_Clasifier_Prompt.txt) | Classifies incoming task intent to select the correct mode. |
| [`prompts/Chat Prompt.txt`](prompts/Chat%20Prompt.txt) | Lightweight conversational/chat mode prompt. |
| [`prompts/Fast Prompt.txt`](prompts/Fast%20Prompt.txt) | Speed-optimized prompt for latency-sensitive tasks. |
| [`prompts/Default Prompt.txt`](prompts/Default%20Prompt.txt) | Fallback prompt when no specific mode is matched. |
| [`prompts/System Prompt.txt`](prompts/System%20Prompt.txt) | Master system-level prompt (global context). |
| [`prompts/System.txt`](prompts/System.txt) | Alternate system prompt variant. |
| [`prompts/Prompt.txt`](prompts/Prompt.txt) | Generic single-task prompt template. |
| [`prompts/Prompts.txt`](prompts/Prompts.txt) | Collection of reusable prompt snippets. |
| [`prompts/Modules.txt`](prompts/Modules.txt) | Module definitions injected into agent context. |
| [`prompts/Spec_Prompt.txt`](prompts/Spec_Prompt.txt) | Spec-writing mode prompt for structured deliverables. |
| [`prompts/Vibe_Prompt.txt`](prompts/Vibe_Prompt.txt) | Creative/vibe-coder mode system prompt. |
| [`prompts/Craft Prompt.txt`](prompts/Craft%20Prompt.txt) | High-craft writing and content creation prompt. |
| [`prompts/DeepWiki Prompt.txt`](prompts/DeepWiki%20Prompt.txt) | Deep research and wiki-style documentation prompt. |
| [`prompts/chat-titles.txt`](prompts/chat-titles.txt) | Generates short titles for chat sessions. |
| [`prompts/nes-tab-completion.txt`](prompts/nes-tab-completion.txt) | Tab-completion hint generation for NES interface. |
| [`prompts/Prompt Wave 11.txt`](prompts/Prompt%20Wave%2011.txt) | Wave 11 batch prompt upgrade package. |
| [`prompts/Tools Wave 11.txt`](prompts/Tools%20Wave%2011.txt) | Wave 11 tool-calling instructions appended to prompts. |
| [`prompts/MKT_006_IMAGE_GEN_PROMPTING.md`](prompts/MKT_006_IMAGE_GEN_PROMPTING.md) | Image-generation prompting SOP (MKT_006, lives in prompts/). |

---

## 4. Tool File Index

Tool files define the function-calling schemas available to each model or mode.

| File | Target Model / Mode | Description |
|------|-------------------|-------------|
| [`tools/Agent Tools.json`](tools/Agent%20Tools.json) | All swarm agents (current) | Primary and most complete tool manifest for the swarm. |
| [`tools/Agent Tools v1.0.json`](tools/Agent%20Tools%20v1.0.json) | Legacy / archival | v1.0 archived tool manifest; retained for rollback reference. |
| [`tools/Builder Tools.json`](tools/Builder%20Tools.json) | Builder persona | Tool set scoped to build, compile, and deploy operations. |
| [`tools/claude-4-sonnet-tools.json`](tools/claude-4-sonnet-tools.json) | Claude 4 Sonnet | Model-specific tool definitions formatted for Claude API. |
| [`tools/gpt-5-tools.json`](tools/gpt-5-tools.json) | GPT-5 | Model-specific tool definitions formatted for OpenAI API. |
| [`tools/phase_mode_tools.json`](tools/phase_mode_tools.json) | Phase mode | Restricted tool set active during phase-modal execution. |
| [`tools/plan_mode_tools.json`](tools/plan_mode_tools.json) | Plan mode | Read-only tool set active during planning-only mode. |
| [`tools/Tools.json`](tools/Tools.json) | Generic / fallback | Base tool manifest used when no model-specific file is matched. |

---

## 5. Asset Consumption Protocol

Every agent **must** follow this 5-step pattern when consuming any asset from this directory. The pattern is directly derived from the Mandatory Procedures section common to all numbered SOPs.

```
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1 — Initialize Persona                                        │
│  Load the appropriate Oracle persona from GOV_002_PERSONA_RESONANCE │
│  before any execution. The persona determines tone, authority level, │
│  and tool-access scope.                                              │
├─────────────────────────────────────────────────────────────────────┤
│  STEP 2 — RAG Fetch                                                  │
│  Query sovereign_memory.json (or the active RAG store) for relevant │
│  context: prior ticket history, domain data, customer records.       │
│  Never act on stale context; re-index per TEC_004 if memory is >24h. │
├─────────────────────────────────────────────────────────────────────┤
│  STEP 3 — Execute                                                    │
│  Run the task using the matching SOP and tool file. Apply SEC_006    │
│  sanitization on any LLM-generated shell/SQL strings. Enforce        │
│  SEC_007 rate limits for outbound SMTP. Wrap all tool calls in       │
│  Pydantic-validated try/except blocks per TEC_007.                   │
├─────────────────────────────────────────────────────────────────────┤
│  STEP 4 — Log Artifacts                                              │
│  Write all produced artifacts (files, emails, reports, DB changes)   │
│  to the Lineage Registry per GOV_007_LINEAGE_SIGNATURE.              │
│  Cryptographically sign each artifact. Never skip this step.         │
├─────────────────────────────────────────────────────────────────────┤
│  STEP 5 — Mark RESOLVED                                              │
│  Update the originating ticket status to RESOLVED (or ESCALATE if   │
│  a blocker was hit). Reconcile revenue events per GOV_003 if any     │
│  Stripe webhook was triggered during execution.                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Choosing the Right Assets for Each Step

| Step | Primary Asset(s) |
|------|-----------------|
| 1 – Initialize Persona | `GOV_002_PERSONA_RESONANCE.md`, `Agent Prompt.txt` / model-specific prompt |
| 2 – RAG Fetch | `TEC_004_RAG_MEMORY_INDEXING.md`, `Agent Tools.json` (memory tools) |
| 3 – Execute | Relevant domain SOP (TEC/SEC/MKT/MON), matching `tools/*.json` |
| 4 – Log Artifacts | `GOV_007_LINEAGE_SIGNATURE.md`, `SEC_010_AUDIT_TRAIL_INTEGRITY.md` |
| 5 – Mark RESOLVED | `GOV_001_TICKET_ISSUANCE.md`, `GOV_003_REVENUE_RECONCILIATION.md` |

---

## 6. Quick Reference — Scenario → SOP Matrix

Use this matrix to immediately identify which SOP to open for a given situation.

| Scenario | Primary SOP | Supporting SOP |
|----------|------------|---------------|
| Creating a new task or work order | GOV_001 | GOV_005 |
| Agent has no active tasks | GOV_004 | GOV_005 |
| New agent being added to the swarm | GOV_006 | GOV_002 |
| Stripe payment event received | GOV_003 | MON_002 |
| Database schema needs to change | TEC_001 | SEC_006 |
| Python dependency may be vulnerable | TEC_002 | SEC_009 |
| Log file growing too large | TEC_003 | TEC_010 |
| RAG memory is stale or corrupted | TEC_004 | TEC_009 |
| Docker disk usage is high | TEC_005 | — |
| API key needs rotating | TEC_006 | SEC_001 |
| New tool integration being written | TEC_007 | SEC_006 |
| Pre-deploy compilation gate | TEC_008 | TEC_007 |
| Submodule or cross-repo merge | TEC_009 | — |
| Weekly performance audit | TEC_010 | GOV_003 |
| `.env` or secret may have leaked | SEC_001 | TEC_006 |
| LLM-generated code needs sandboxing | SEC_002 | SEC_006 |
| Suspicious inbound webhook | SEC_003 | SEC_006 |
| SMTP deliverability complaint | SEC_004 | SEC_007 |
| PII collection or deletion request | SEC_005 | GOV_003 |
| LLM output going to shell/DB | SEC_006 | TEC_007 |
| Email campaign hitting send limits | SEC_007 | MON_012 |
| Attempted edit to stasis branch | SEC_008 | GOV_007 |
| Node provisioning or setup | SEC_009 | GOV_006 |
| Weekly audit trail verification | SEC_010 | GOV_007 |
| Writing a TikTok video script | MKT_001 | MKT_010 |
| Publishing a LinkedIn post | MKT_002 | MKT_010 |
| Writing a cold or nurture email | MKT_003 | MON_012 |
| Launching a paid ad campaign | MKT_004 | MKT_005 |
| Starting an SEO content sprint | MKT_005 | MON_011 |
| Generating visual campaign assets | MKT_006 | MKT_010 |
| Directing an AI video edit | MKT_007 | MKT_001 |
| Scheduling omni-channel posts | MKT_008 | MKT_010 |
| Setting up a drip email sequence | MKT_009 | MKT_003 |
| Brand voice consistency review | MKT_010 | GOV_002 |
| Running affiliate bridge pages | MON_001 | MKT_001 |
| Onboarding API/SaaS customer | MON_002 | GOV_003 |
| Extracting leads for brokerage | MON_003 | LEAD_EXTRACTION |
| Listing a digital product | MON_004 | MKT_010 |
| Selling newsletter sponsorships | MON_005 | MKT_002 |
| Creating print-on-demand products | MON_006 | MKT_006 |
| Monetizing a blog with programmatic ads | MON_007 | MON_011 |
| Evaluating DeFi yield opportunity | MON_008 | SEC_001 |
| New paid community member joins | MON_009 | MON_002 |
| Drafting data licensing agreement | MON_010 | SEC_005 |
| Daily SEO blog post generation | MON_011 | MKT_005 |
| Cold email monetization campaign | MON_012 | SEC_007, MKT_003 |
| Spinning up a new niche site | MON_013 | TEC_008, MKT_005 |
| Self-healing or error recovery | SELF_HEALING | TEC_001, TEC_007 |
| Multi-agent outreach at scale | COLD_OUTREACH_SOP | MON_012, SEC_007 |
| Traffic acquisition campaign | TRAFFIC_DOMINANCE_v1 | MON_011, MKT_005 |

---

*This file is auto-indexed in [`registry.json`](registry.json). Any new asset added to `assets/` must be registered there and documented in the relevant section above.*
