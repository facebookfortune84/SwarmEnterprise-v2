"""
Workflow service — create, advance, and handle failures for multi-step workflows.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.db.models import Workflow, WorkflowStep

logger = logging.getLogger("WorkflowService")


class WorkflowService:
    """Orchestrate multi-step workflows."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Creation                                                             #
    # ------------------------------------------------------------------ #

    def create_workflow(
        self,
        name: str,
        steps: list[dict],
        company_id: str = None,
    ) -> Workflow:
        """
        Persist a workflow definition and its step rows.

        Args:
            name: Human-readable workflow name.
            steps: List of step definitions, each a dict with at least
                   'step_name' and 'step_type' keys.
            company_id: Optional owning tenant.

        Returns:
            The created Workflow row.
        """
        workflow = Workflow(
            name=name,
            company_id=company_id,
            steps_json=json.dumps(steps),
            status="pending",
            current_step=0,
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)

        for step_def in steps:
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_name=step_def.get("step_name", "unnamed"),
                step_type=step_def.get("step_type", "ticket"),
                input_json=json.dumps(step_def.get("input", {})),
                status="pending",
            )
            self.db.add(step)
        self.db.commit()

        logger.info("Created workflow %s (%s) with %d steps", workflow.id, name, len(steps))
        return workflow

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Transition a pending workflow to 'running' and enqueue its first step.

        Returns:
            Updated Workflow or None if not found.
        """
        workflow = self._get(workflow_id)
        if not workflow:
            return None
        if workflow.status != "pending":
            return workflow  # idempotent

        workflow.status = "running"
        workflow.current_step = 0
        workflow.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(workflow)

        self._enqueue_step(workflow)
        return workflow

    def advance_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """
        Mark the current step completed and move to the next one.
        Completes the workflow when no further steps remain.

        Returns:
            Updated Workflow or None if not found.
        """
        workflow = self._get(workflow_id)
        if not workflow or workflow.status not in ("running",):
            return workflow

        steps = self._get_steps(workflow_id)
        current_idx = workflow.current_step

        if current_idx < len(steps):
            step = steps[current_idx]
            step.status = "completed"
            step.completed_at = datetime.utcnow()

        next_idx = current_idx + 1
        if next_idx >= len(steps):
            # All steps done
            workflow.status = "completed"
            workflow.completed_at = datetime.utcnow()
            logger.info("Workflow %s completed", workflow_id)
            try:
                from backend.services.event_bus import event_bus

                event_bus.publish("workflow.completed", {"workflow_id": workflow_id})
            except Exception:
                pass
        else:
            workflow.current_step = next_idx
            self._enqueue_step(workflow, step_index=next_idx)

        workflow.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def pause_workflow(self, workflow_id: str) -> Optional[Workflow]:
        workflow = self._get(workflow_id)
        if workflow and workflow.status == "running":
            workflow.status = "paused"
            workflow.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(workflow)
        return workflow

    def resume_workflow(self, workflow_id: str) -> Optional[Workflow]:
        workflow = self._get(workflow_id)
        if workflow and workflow.status == "paused":
            workflow.status = "running"
            workflow.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(workflow)
            self._enqueue_step(workflow)
        return workflow

    def cancel_workflow(self, workflow_id: str, user_id: str = None) -> Optional[Workflow]:
        workflow = self._get(workflow_id)
        if workflow and workflow.status not in ("completed", "failed"):
            workflow.status = "failed"
            workflow.error_message = f"Cancelled by user {user_id}"
            workflow.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(workflow)
        return workflow

    def handle_failure(self, workflow_id: str, step_id: str, error: str) -> Optional[Workflow]:
        """
        Record a step failure, update workflow status, and fire event.

        Args:
            workflow_id: Owning workflow.
            step_id: The step that failed.
            error: Error message.

        Returns:
            Updated Workflow.
        """
        workflow = self._get(workflow_id)
        if not workflow:
            return None

        step = self.db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if step:
            step.status = "failed"
            step.error_message = error
            step.retry_count = (step.retry_count or 0) + 1

        workflow.status = "failed"
        workflow.error_message = error
        workflow.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(workflow)

        try:
            from backend.services.event_bus import event_bus

            event_bus.publish("workflow.failed", {"workflow_id": workflow_id, "error": error})
        except Exception:
            pass

        logger.error("Workflow %s failed at step %s: %s", workflow_id, step_id, error)
        return workflow

    def get_status(self, workflow_id: str) -> Optional[dict]:
        """
        Return the current workflow status and all step details.

        Returns:
            Dict with workflow metadata and step list, or None if not found.
        """
        workflow = self._get(workflow_id)
        if not workflow:
            return None

        steps = self._get_steps(workflow_id)
        step_list = [
            {
                "id": s.id,
                "step_name": s.step_name,
                "step_type": s.step_type,
                "status": s.status,
                "retry_count": s.retry_count,
                "error_message": s.error_message,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in steps
        ]
        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status,
            "current_step": workflow.current_step,
            "total_steps": len(steps),
            "error_message": workflow.error_message,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "steps": step_list,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get(self, workflow_id: str) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def _get_steps(self, workflow_id: str) -> list[WorkflowStep]:
        return (
            self.db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.id)
            .all()
        )

    def _enqueue_step(self, workflow: Workflow, step_index: int = None) -> None:
        """Fire the Celery task for the given step (best-effort)."""
        if step_index is None:
            step_index = workflow.current_step
        try:
            from backend.tasks.workflow_tasks import execute_workflow_step

            steps = self._get_steps(workflow.id)
            if step_index < len(steps):
                step = steps[step_index]
                step.status = "running"
                step.started_at = datetime.utcnow()
                self.db.commit()
                execute_workflow_step.apply_async(
                    args=[workflow.id, step.id],
                    queue="default",
                )
        except Exception as exc:
            logger.warning("Could not enqueue workflow step: %s", exc)
