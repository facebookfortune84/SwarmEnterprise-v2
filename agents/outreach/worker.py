import os
import time
import threading
import logging
from agents.outreach.email_engine import EmailTools
from backend import queue as backend_queue

logger = logging.getLogger("OutreachWorker")


class OutreachTask:
    def __init__(self, to_email: str, subject: str, body: str, attempts: int = 0):
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.attempts = attempts


def enqueue_outreach(to_email: str, subject: str, body: str):
    payload = {"to_email": to_email, "subject": subject, "body": body, "attempts": 0}
    backend_queue.enqueue_task(payload)
    logger.info(f"Enqueued outreach to {to_email}")


def _worker_loop(stop_event: threading.Event):
    email_tool = EmailTools()
    while not stop_event.is_set():
        item = backend_queue.dequeue_task(timeout=1)
        if not item:
            continue
        task = OutreachTask(
            item.get("to_email"), item.get("subject"), item.get("body"), item.get("attempts", 0)
        )
        try:
            res = email_tool.send_email(task.to_email, task.subject, task.body)
            if res.startswith("SUCCESS"):
                logger.info(f"Outreach sent to {task.to_email}")
            else:
                logger.warning(f"Outreach failed for {task.to_email}: {res}")
                # simple retry logic
                if task.attempts < int(os.getenv("OUTREACH_MAX_RETRIES", "3")):
                    task.attempts += 1
                    backoff = 2**task.attempts
                    time.sleep(backoff)
                    backend_queue.enqueue_task(
                        {
                            "to_email": task.to_email,
                            "subject": task.subject,
                            "body": task.body,
                            "attempts": task.attempts,
                        }
                    )
        except Exception as e:
            logger.exception(f"Worker error: {e}")


_worker_thread = None
_stop_event = None


def start_worker():
    global _worker_thread, _stop_event
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event = threading.Event()
    _worker_thread = threading.Thread(target=_worker_loop, args=(_stop_event,), daemon=True)
    _worker_thread.start()
    logger.info("Outreach worker started")


def stop_worker():
    global _worker_thread, _stop_event
    if _stop_event:
        _stop_event.set()
    if _worker_thread:
        _worker_thread.join(timeout=5)
    logger.info("Outreach worker stopped")
