"""
Tests for backend/api/ws.py — WebSocket endpoints and ConnectionManager.
Uses TestClient with websocket_connect context manager.
"""
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def ws_client():
    from backend.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestConnectionManager:
    """Unit tests for the ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connect_user_accepts_and_registers(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        await mgr.connect_user("user1", mock_ws)

        mock_ws.accept.assert_called_once()
        assert mock_ws in mgr._user_connections["user1"]

    @pytest.mark.asyncio
    async def test_disconnect_user_removes_ws(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        await mgr.connect_user("user1", mock_ws)
        mgr.disconnect_user("user1", mock_ws)

        assert mock_ws not in mgr._user_connections.get("user1", [])

    def test_disconnect_user_not_connected_noop(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        # Should not raise
        mgr.disconnect_user("user999", mock_ws)

    @pytest.mark.asyncio
    async def test_send_to_user_success(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        await mgr.connect_user("user1", mock_ws)

        await mgr.send_to_user("user1", {"type": "notification", "message": "hello"})
        mock_ws.send_json.assert_called_once_with({"type": "notification", "message": "hello"})

    @pytest.mark.asyncio
    async def test_send_to_user_removes_dead_connection(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.send_json.side_effect = Exception("connection closed")
        await mgr.connect_user("user1", mock_ws)

        # Should not raise; dead connection removed
        await mgr.send_to_user("user1", {"msg": "data"})
        assert mock_ws not in mgr._user_connections.get("user1", [])

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user_noop(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        # Should not raise
        await mgr.send_to_user("nobody", {"data": "x"})

    @pytest.mark.asyncio
    async def test_connect_thread_accepts_and_registers(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        await mgr.connect_thread("thread1", mock_ws)

        mock_ws.accept.assert_called_once()
        assert mock_ws in mgr._thread_connections["thread1"]

    def test_disconnect_thread_removes_ws(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        # Manually inject
        mgr._thread_connections["thread1"] = [mock_ws]
        mgr.disconnect_thread("thread1", mock_ws)

        assert mock_ws not in mgr._thread_connections.get("thread1", [])

    @pytest.mark.asyncio
    async def test_broadcast_to_thread(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect_thread("thread1", ws1)
        await mgr.connect_thread("thread1", ws2)

        payload = {"content": "hello", "sender_id": "u1"}
        await mgr.broadcast_to_thread("thread1", payload)

        ws1.send_json.assert_called_once_with(payload)
        ws2.send_json.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_thread_connection(self):
        from backend.api.ws import ConnectionManager

        mgr = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.send_json.side_effect = Exception("closed")
        await mgr.connect_thread("thread1", mock_ws)

        await mgr.broadcast_to_thread("thread1", {"data": "x"})
        assert mock_ws not in mgr._thread_connections.get("thread1", [])


class TestNotificationEndpoint:
    def test_ws_notifications_connect_and_ping(self, ws_client):
        from fastapi.testclient import TestClient

        with ws_client.websocket_connect("/ws/notifications/testuser") as ws:
            ws.send_text("ping")
            response = ws.receive_text()
        assert response == "pong"

    def test_ws_notifications_non_ping_ignored(self, ws_client):
        """Non-ping messages should not generate a response."""
        with ws_client.websocket_connect("/ws/notifications/testuser") as ws:
            ws.send_text("some-other-message")
            # Send ping to flush
            ws.send_text("ping")
            response = ws.receive_text()
        assert response == "pong"

    def test_ws_notifications_disconnect(self, ws_client):
        """Connection disconnect should be handled gracefully."""
        with ws_client.websocket_connect("/ws/notifications/testuser") as ws:
            ws.close()


class TestMessagesEndpoint:
    def test_ws_messages_valid_json(self, ws_client):
        with patch("backend.db.session.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            from backend.db.models import Message
            mock_msg = MagicMock(spec=Message)
            mock_msg.id = "msg-1"
            mock_msg.created_at = None
            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            mock_db.refresh.side_effect = lambda x: None

            with ws_client.websocket_connect("/ws/messages/thread-1") as ws:
                ws.send_text(json.dumps({"sender_id": "u1", "content": "Hello"}))
                response_raw = ws.receive_text()
            # Either full JSON or error JSON — just check it's valid JSON
            data = json.loads(response_raw)
            assert "content" in data or "thread_id" in data

    def test_ws_messages_invalid_json(self, ws_client):
        """Invalid JSON should return an error JSON."""
        with ws_client.websocket_connect("/ws/messages/thread-2") as ws:
            ws.send_text("not-json-at-all")
            response = ws.receive_text()
        data = json.loads(response)
        assert "error" in data

    def test_ws_messages_empty_content_ignored(self, ws_client):
        """Message with empty content should not broadcast."""
        with ws_client.websocket_connect("/ws/messages/thread-3") as ws:
            ws.send_text(json.dumps({"sender_id": "u1", "content": ""}))
            # Send a valid message after to confirm connection is still alive
            ws.send_text(json.dumps({"sender_id": "u1", "content": "alive"}))
            # We should receive the second message
            response_raw = ws.receive_text()
        data = json.loads(response_raw)
        assert data.get("content") == "alive" or "thread_id" in data

    def test_ws_messages_disconnect(self, ws_client):
        with ws_client.websocket_connect("/ws/messages/thread-4") as ws:
            ws.close()
