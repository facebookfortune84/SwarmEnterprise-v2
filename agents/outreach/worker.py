import os
import time
import threading
import logging
from queue import Queue, Empty
from agents.outreach.email_engine import EmailTools

logger = logging.getLogger("OutreachWorker")

# Simple in-process queue. In production replace with Redis/RQ or Celery.
_outreach_queue = Queue()

class OutreachTask:
    def __init__(self, to_email: str, subject: str, body: str, attempts: int = 0):
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.attempts = attempts


def enqueue_outreach(to_email: str, subject: str, body: str):
    _outreach_queue.put(OutreachTask(to_email, subject, body))
    logger.info(f"Enqueued outreach to {to_email}")


def _worker_loop(stop_event: threading.Event):
    email_tool = EmailTools()
    while not stop_event.is_set():
        try:
            task = _outreach_queue.get(timeout=1)
        except Empty:
            continue
        try:
            res = email_tool.send_email(task.to_email, task.subject, task.body)
            if res.startswith('SUCCESS'):
                logger.info(f"Outreach sent to {task.to_email}")
            else:
                logger.warning(f"Outreach failed for {task.to_email}: {res}")
                # simple retry logic
                if task.attempts < int(os.getenv('OUTREACH_MAX_RETRIES', '3')):
                    task.attempts += 1
                    backoff = 2 ** task.attempts
                    time.sleep(backoff)
                    _outreach_queue.put(task)
        except Exception as e:
            logger.exception(f"Worker error: {e}")
        finally:
            _outreach_queue.task_done()

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
