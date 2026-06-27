"""
Workflow-related Celery tasks.
"""
import logging
from backend.celery_app import celery_app

logger = logging.getLogger("tasks.workflows")


@celery_app.task(
    name="backend.tasks.workflow_tasks.execute_workflow_step",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def execute_workflow_step(self, workflow_id: str, step_id: str):
    """
    Execute a single workflow step.

    Dispatches to the correct handler based on the step's type, then
    automatically advances the parent workflow on success.

    Args:
        workflow_id: The owning workflow.
        step_id: The WorkflowStep to execute.
    """
    from backend.db.session import SessionLocal
    from backend.db.models import WorkflowStep

    db = SessionLocal()
    try:
        step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step:
            logger.warning("execute_workflow_step: step %s not found", step_id)
            return {"error": "step_not_found"}

        logger.info(
            "Executing step %s (type=%s) for workflow %s",
            step.step_name,
            step.step_type,
            workflow_id,
        )

        _dispatch_step(step, db)

        # Advance the workflow to the next step
        advance_workflow.apply_async(args=[workflow_id], queue="default")
        return {"ok": True, "step_id": step_id}
    except Exception as exc:
        logger.exception("execute_workflow_step failed: step=%s", step_id)
        handle_step_failure.apply_async(
            args=[workflow_id, step_id, str(exc)],
            queue="default",
        )
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="backend.tasks.workflow_tasks.handle_step_failure",
    bind=True,
    max_retries=1,
)
def handle_step_failure(self, workflow_id: str, step_id: str, error: str):
    """
    Compensation logic for a failed workflow step.

    Records the failure, marks the workflow as failed, and fires the
    workflow.failed event so the event bus can notify admins.

    Args:
        workflow_id: Owning workflow.
        step_id: The step that failed.
        error: Error description.
    """
    from backend.db.session import SessionLocal
    from backend.services.workflow_service import WorkflowService

    db = SessionLocal()
    try:
        svc = WorkflowService(db)
        svc.handle_failure(workflow_id, step_id, error)
        logger.error("Workflow %s step %s failed: %s", workflow_id, step_id, error)
        return {"ok": True}
    except Exception as exc:
        logger.exception("handle_step_failure itself failed")
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="backend.tasks.workflow_tasks.advance_workflow",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def advance_workflow(self, workflow_id: str):
    """
    Move a running workflow to its next step.

    Called automatically after each step completes. If no more steps
    remain the workflow transitions to 'completed'.

    Args:
        workflow_id: The workflow to advance.
    """
    from backend.db.session import SessionLocal
    from backend.services.workflow_service import WorkflowService

    db = SessionLocal()
    try:
        svc = WorkflowService(db)
        wf = svc.advance_workflow(workflow_id)
        if wf:
            logger.info(
                "Workflow %s advanced to step %d (status=%s)",
                workflow_id,
                wf.current_step,
                wf.status,
            )
        return {"ok": True, "workflow_id": workflow_id}
    except Exception as exc:
        logger.exception("advance_workflow failed: %s", workflow_id)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Internal step dispatcher
# ─────────────────────────────────────────────────────────────────────────────


def _dispatch_step(step, db) -> None:
    """
    Route a WorkflowStep to its type-specific handler.

    Supported step types: ticket, notification, approval, condition.
    Unknown types are logged and skipped.
    """
    import json

    input_data = json.loads(step.input_json) if step.input_json else {}

    if step.step_type == "ticket":
        from backend.services.ticket_service import TicketService

        svc = TicketService(db)
        ticket = svc.create_ticket(
            title=input_data.get("title", f"Workflow step: {step.step_name}"),
            instruction=input_data.get("instruction", ""),
            priority=input_data.get("priority", "medium"),
        )
        step.output_json = json.dumps({"ticket_id": ticket.id})

    elif step.step_type == "notification":
        from backend.services.notification_service import NotificationService

        svc = NotificationService(db)
        svc.broadcast_system_event(
            event_type=input_data.get("event_type", step.step_name),
            message=input_data.get("message", f"Step {step.step_name} executed"),
        )
        step.output_json = json.dumps({"broadcast": True})

    elif step.step_type == "approval":
        # Approval steps are async by nature — mark as pending and wait
        # for an external POST to /api/workflows/{id}/resume
        step.output_json = json.dumps({"waiting_for_approval": True})

    elif step.step_type == "condition":
        condition = input_data.get("condition", True)
        step.output_json = json.dumps({"condition_result": bool(condition)})

    else:
        logger.warning("Unknown step type '%s' — skipping", step.step_type)
        step.output_json = json.dumps({"skipped": True})

    db.commit()
