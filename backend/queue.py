import os
import json
import logging
from typing import Optional

logger = logging.getLogger("BackendQueue")
REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL:
    try:
        import redis

        _redis = redis.from_url(REDIS_URL)
        QUEUE_KEY = os.getenv("REDIS_QUEUE_KEY", "swarm_outreach_queue")
        logger.info("Using Redis queue at %s", REDIS_URL)

        def enqueue_task(payload: dict):
            _redis.rpush(QUEUE_KEY, json.dumps(payload))

        def dequeue_task(timeout: int = 1) -> Optional[dict]:
            item = _redis.blpop(QUEUE_KEY, timeout=timeout)
            if not item:
                return None
            _, data = item
            return json.loads(data)

    except Exception as e:
        logger.warning(f"Redis not available, falling back to in-process queue: {e}")
        REDIS_URL = None

if not REDIS_URL:
    # In-process fallback
    from queue import Queue

    _q = Queue()

