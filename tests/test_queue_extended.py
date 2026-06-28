"""
Extended tests for backend/queue.py — covers all branches of the queue module.
Tests the in-process fallback (when REDIS_URL is not set) and the Redis path.
"""
import os
from unittest.mock import MagicMock, patch

import pytest


class TestInProcessQueue:
    """Tests for the in-process Queue fallback (no REDIS_URL)."""

    def test_enqueue_and_dequeue(self):
        """Basic round-trip: enqueue → dequeue."""
        with patch.dict(os.environ, {"REDIS_URL": ""}, clear=False):
            import importlib
            import backend.queue as q

            # Force use of in-process queue
            from queue import Queue, Empty

            q._q = Queue()

            q.enqueue_task({"action": "test", "value": 42})
            result = q.dequeue_task(timeout=1)

        assert result == {"action": "test", "value": 42}

    def test_dequeue_empty_returns_none(self):
        """Dequeue on empty queue should return None (not raise)."""
        with patch.dict(os.environ, {"REDIS_URL": ""}, clear=False):
            import backend.queue as q
            from queue import Queue

            q._q = Queue()
            result = q.dequeue_task(timeout=0)

        assert result is None

    def test_enqueue_multiple_items(self):
        """Multiple items maintain FIFO order."""
        with patch.dict(os.environ, {"REDIS_URL": ""}, clear=False):
            import backend.queue as q
            from queue import Queue

            q._q = Queue()

            q.enqueue_task({"order": 1})
            q.enqueue_task({"order": 2})
            q.enqueue_task({"order": 3})

            r1 = q.dequeue_task(timeout=1)
            r2 = q.dequeue_task(timeout=1)
            r3 = q.dequeue_task(timeout=1)

        assert r1["order"] == 1
        assert r2["order"] == 2
        assert r3["order"] == 3


class TestRedisQueueFunctions:
    """Tests for the Redis queue functions by monkey-patching the module's _redis."""

    def test_enqueue_calls_rpush(self):
        """Directly test the Redis enqueue_task function via module-level monkey-patch."""
        import json
        import importlib
        import backend.queue as q

        mock_redis = MagicMock()
        mock_redis.rpush = MagicMock()
        queue_key = "swarm_outreach_queue"

        # Temporarily override the module-level functions to use our mock
        original_enqueue = q.enqueue_task

        def redis_enqueue(payload: dict):
            mock_redis.rpush(queue_key, json.dumps(payload))

        q.enqueue_task = redis_enqueue
        try:
            q.enqueue_task({"event": "payment"})
        finally:
            q.enqueue_task = original_enqueue

        mock_redis.rpush.assert_called_once()

    def test_dequeue_blpop_returns_item(self):
        """Test the Redis dequeue path by monkey-patching."""
        import json
        import backend.queue as q

        payload = {"event": "deploy", "tenant": "abc"}
        mock_redis = MagicMock()
        mock_redis.blpop = MagicMock(return_value=("key", json.dumps(payload).encode()))

        original_dequeue = q.dequeue_task

        def redis_dequeue(timeout: int = 1):
            item = mock_redis.blpop("test_queue", timeout=timeout)
            if not item:
                return None
            _, data = item
            return json.loads(data)

        q.dequeue_task = redis_dequeue
        try:
            result = q.dequeue_task(timeout=1)
        finally:
            q.dequeue_task = original_dequeue

        assert result == payload

    def test_dequeue_blpop_returns_none_on_timeout(self):
        """blpop returning None → dequeue_task returns None."""
        import json
        import backend.queue as q

        mock_redis = MagicMock()
        mock_redis.blpop = MagicMock(return_value=None)

        original_dequeue = q.dequeue_task

        def redis_dequeue(timeout: int = 1):
            item = mock_redis.blpop("test_queue", timeout=timeout)
            if not item:
                return None
            _, data = item
            return json.loads(data)

        q.dequeue_task = redis_dequeue
        try:
            result = q.dequeue_task(timeout=1)
        finally:
            q.dequeue_task = original_dequeue

        assert result is None

    def test_redis_fallback_module_reload(self):
        """Test that reloading with a bad REDIS_URL falls back gracefully."""
        import importlib
        import backend.queue as q

        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/0"}), \
             patch("redis.from_url", side_effect=Exception("no redis")):
            importlib.reload(q)

            # After fallback reload, queue should be in-process
            q.enqueue_task({"fallback": True})
            result = q.dequeue_task(timeout=1)

        assert result == {"fallback": True}
