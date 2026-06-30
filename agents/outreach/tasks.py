"""
Celery tasks for the outreach pipeline agents.

Task schedule:
  enrich_prospects            — on-demand (triggered via API or manual dispatch)
  process_due_sequence_steps  — every 5 minutes
  check_inbox_replies         — every 5 minutes
  generate_daily_outreach_report — daily at 01:00 UTC

All tasks are wrapped in a top-level try/except to prevent unhandled
exceptions from crashing the Celery worker process.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("OutreachTasks")


def _get_app():
    """Lazy import of the Celery app to avoid circular imports at module load."""
    from backend.celery_app import celery_app  # type: ignore[import]

    return celery_app


# ---------------------------------------------------------------------------
# enrich_prospects
# ---------------------------------------------------------------------------

def enrich_prospects(niche_descriptor: str) -> dict:
    """
    Discover and enrich prospects for a niche descriptor.

    Intended to be called as:
        enrich_prospects.delay("SaaS companies hiring engineers")
    """
    try:
        from agents.outreach.enrichment_agent import EnrichmentAgent

        agent = EnrichmentAgent()
        results = agent.run(niche_descriptor)
        logger.info("enrich_prospects: found %d prospects.", len(results))
        return {"status": "ok", "discovered": len(results)}
    except Exception as exc:
        logger.exception("enrich_prospects task failed: %s", exc)
        return {"status": "error", "error": str(exc)}


# Try to register as a Celery task; fall back gracefully if Celery is not
# configured (e.g. during unit tests).
try:
    app = _get_app()
    enrich_prospects = app.task(
        name="outreach.enrich_prospects",
        soft_time_limit=300,
        time_limit=360,
    )(enrich_prospects)
except Exception:
    pass  # Celery not available in test environment


# ---------------------------------------------------------------------------
# process_due_sequence_steps
# ---------------------------------------------------------------------------

def process_due_sequence_steps() -> dict:
    """Process all outreach sequence steps that are now due."""
    try:
        from agents.outreach.sequencer_agent import SequencerAgent

        agent = SequencerAgent()
        count = agent.process_due_steps()
        logger.info("process_due_sequence_steps: processed %d step(s).", count)
        return {"status": "ok", "processed": count}
    except Exception as exc:
        logger.exception("process_due_sequence_steps task failed: %s", exc)
        return {"status": "error", "error": str(exc)}


try:
    app = _get_app()
    process_due_sequence_steps = app.task(
        name="outreach.process_due_sequence_steps",
    )(process_due_sequence_steps)
except Exception:
    pass


# ---------------------------------------------------------------------------
# check_inbox_replies
# ---------------------------------------------------------------------------

def check_inbox_replies() -> dict:
    """Poll the IMAP inbox and classify/dispatch any new replies."""
    try:
        from agents.outreach.reply_handler_agent import ReplyHandlerAgent

        agent = ReplyHandlerAgent()
        count = agent.poll_inbox()
        logger.info("check_inbox_replies: processed %d message(s).", count)
        return {"status": "ok", "processed": count}
    except Exception as exc:
        logger.exception("check_inbox_replies task failed: %s", exc)
        return {"status": "error", "error": str(exc)}


try:
    app = _get_app()
    check_inbox_replies = app.task(
        name="outreach.check_inbox_replies",
    )(check_inbox_replies)
except Exception:
    pass


# ---------------------------------------------------------------------------
# generate_daily_outreach_report
# ---------------------------------------------------------------------------

def generate_daily_outreach_report() -> dict:
    """Aggregate and persist daily outreach metrics for the preceding UTC day."""
    try:
        from agents.outreach.reporting_agent import ReportingAgent

        agent = ReportingAgent()
        metrics = agent.generate_daily_report()
        logger.info("generate_daily_outreach_report: metrics=%r", metrics)
        return {"status": "ok", "metrics": metrics}
    except Exception as exc:
        logger.exception("generate_daily_outreach_report task failed: %s", exc)
        return {"status": "error", "error": str(exc)}


try:
    app = _get_app()
    generate_daily_outreach_report = app.task(
        name="outreach.generate_daily_outreach_report",
    )(generate_daily_outreach_report)
except Exception:
    pass
