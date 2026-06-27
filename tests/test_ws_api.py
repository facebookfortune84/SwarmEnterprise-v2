"""
tests/test_ws_api.py
======================
Comprehensive coverage for backend/api/ws.py

Covers:
- ConnectionManager.connect_user / disconnect_user
- ConnectionManager.send_to_user (success, broken connection)
- ConnectionManager.connect_thread / disconnect_thread
- ConnectionManager.broadcast_to_thread (success, broken connection)
- WebSocket route: /ws/notifications/{user_id} (ping/pong, disconnect)
- WebSocket route: /ws/messages/{thread_id} (valid message, invalid JSON, empty content, disconnect)
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.base import Base
from backend.db.session import get_db
from backend.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def ws_client(db_session):
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("backend.auth.jwt_handler.redis_client", mock_redis):
        yield TestClient(app, raise_server_exceptions=False)

    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Tests: ConnectionManager unit tests
# ---------------------------------------------------------------------------


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_user(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_user("user-001", ws)
        ws.accept.assert_called_once()
        assert ws in mgr._user_connections["user-001"]

    @pytest.mark.asyncio
    async def test_disconnect_user(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_user("user-002", ws)
        mgr.disconnect_user("user-002", ws)
        assert ws not in mgr._user_connections.get("user-002", [])

    @pytest.mark.asyncio
    async def test_disconnect_user_not_connected(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        # Should not raise
        mgr.disconnect_user("nonexistent-user", ws)

    @pytest.mark.asyncio
    async def test_send_to_user_success(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_user("user-003", ws)
        await mgr.send_to_user("user-003", {"msg": "hello"})
        ws.send_json.assert_called_once_with({"msg": "hello"})

    @pytest.mark.asyncio
    async def test_send_to_user_broken_connection(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("broken pipe"))
        await mgr.connect_user("user-004", ws)
        # Should not raise; broken ws is removed
        await mgr.send_to_user("user-004", {"msg": "test"})
        assert ws not in mgr._user_connections.get("user-004", [])

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        # Should not raise
        await mgr.send_to_user("nobody", {"msg": "test"})

    @pytest.mark.asyncio
    async def test_connect_thread(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_thread("thread-001", ws)
        ws.accept.assert_called_once()
        assert ws in mgr._thread_connections["thread-001"]

    @pytest.mark.asyncio
    async def test_disconnect_thread(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect_thread("thread-002", ws)
        mgr.disconnect_thread("thread-002", ws)
        assert ws not in mgr._thread_connections.get("thread-002", [])

    @pytest.mark.asyncio
    async def test_disconnect_thread_not_connected(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        # Should not raise
        mgr.disconnect_thread("no-thread", ws)

    @pytest.mark.asyncio
    async def test_broadcast_to_thread_success(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect_thread("thread-003", ws1)
        await mgr.connect_thread("thread-003", ws2)
        await mgr.broadcast_to_thread("thread-003", {"msg": "broadcast"})
        ws1.send_json.assert_called_once_with({"msg": "broadcast"})
        ws2.send_json.assert_called_once_with({"msg": "broadcast"})

    @pytest.mark.asyncio
    async def test_broadcast_to_thread_broken_connection(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("broken"))
        await mgr.connect_thread("thread-004", ws)
        # Should not raise; broken ws removed
        await mgr.broadcast_to_thread("thread-004", {"msg": "test"})
        assert ws not in mgr._thread_connections.get("thread-004", [])

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_thread(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast_to_thread("no-thread", {"msg": "test"})


# ---------------------------------------------------------------------------
# Tests: WebSocket routes via TestClient
# ---------------------------------------------------------------------------


class TestWsNotificationsRoute:
    def test_ws_notifications_ping_pong(self, ws_client):
        with ws_client.websocket_connect("/ws/notifications/user-ws-001") as ws:
            ws.send_text("ping")
            msg = ws.receive_text()
            assert msg == "pong"

    def test_ws_notifications_non_ping_message(self, ws_client):
        with ws_client.websocket_connect("/ws/notifications/user-ws-002") as ws:
            ws.send_text("hello world")
            # Should stay connected without error after non-ping message
            ws.send_text("ping")
            msg = ws.receive_text()
            assert msg == "pong"

    def test_ws_notifications_disconnect(self, ws_client):
        """Client can close the connection cleanly."""
        with ws_client.websocket_connect("/ws/notifications/user-ws-003") as ws:
            ws.close()


class TestWsMessagesRoute:
    def test_ws_messages_valid_message(self, ws_client, db_session):
        """Valid message is broadcast to thread participants."""
        with ws_client.websocket_connect("/ws/messages/thread-ws-001") as ws:
            msg = json.dumps({"sender_id": "u1", "content": "Hello there"})
            ws.send_text(msg)
            # The message is broadcast back to all participants (including self)
            received = ws.receive_json()
            assert received["content"] == "Hello there"
            assert received["sender_id"] == "u1"

    def test_ws_messages_invalid_json(self, ws_client):
        """Invalid JSON returns an error message."""
        with ws_client.websocket_connect("/ws/messages/thread-ws-002") as ws:
            ws.send_text("not valid json {{{")
            response = ws.receive_text()
            data = json.loads(response)
            assert "error" in data

    def test_ws_messages_empty_content(self, ws_client):
        """Message with empty content is silently dropped."""
        with ws_client.websocket_connect("/ws/messages/thread-ws-003") as ws:
            ws.send_text(json.dumps({"sender_id": "u2", "content": ""}))
            # Send a valid message after to confirm connection still alive
            ws.send_text(json.dumps({"sender_id": "u2", "content": "hello"}))
            received = ws.receive_json()
            assert received["content"] == "hello"

    def test_ws_messages_missing_fields(self, ws_client):
        """Message without sender_id or content uses defaults."""
        with ws_client.websocket_connect("/ws/messages/thread-ws-004") as ws:
            ws.send_text(json.dumps({"content": "anonymous message"}))
            received = ws.receive_json()
            assert received["content"] == "anonymous message"
            assert received.get("sender_id") == "unknown"
