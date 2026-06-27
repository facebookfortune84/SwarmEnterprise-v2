"""
WebSocket endpoints for real-time notification and message delivery.

Connections are tracked per user (notifications) or per thread (messages).
The ConnectionManager is imported by the notification service for push delivery.
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("WebSocket")

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    In-process WebSocket connection registry.

    Two independent namespaces:
      • user connections  — keyed by user_id  (notification channel)
      • thread connections — keyed by thread_id (messaging channel)
    """

    def __init__(self):
        # user_id -> list[WebSocket]
        self._user_connections: dict[str, list[WebSocket]] = {}
        # thread_id -> list[WebSocket]
        self._thread_connections: dict[str, list[WebSocket]] = {}

    # ------------------------------------------------------------------ #
    # User / notification channel                                          #
    # ------------------------------------------------------------------ #

    async def connect_user(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._user_connections.setdefault(user_id, []).append(ws)
        logger.info(
            "WS user connected: %s (total=%d)", user_id, len(self._user_connections[user_id])
        )

    def disconnect_user(self, user_id: str, ws: WebSocket) -> None:
        conns = self._user_connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        logger.info("WS user disconnected: %s", user_id)

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        """Push a JSON payload to all active connections for user_id."""
        for ws in list(self._user_connections.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect_user(user_id, ws)

    # ------------------------------------------------------------------ #
    # Thread / messaging channel                                           #
    # ------------------------------------------------------------------ #

    async def connect_thread(self, thread_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._thread_connections.setdefault(thread_id, []).append(ws)
        logger.info("WS thread connected: %s", thread_id)

    def disconnect_thread(self, thread_id: str, ws: WebSocket) -> None:
        conns = self._thread_connections.get(thread_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast_to_thread(self, thread_id: str, payload: dict) -> None:
        """Broadcast a JSON payload to all participants of a thread."""
        for ws in list(self._thread_connections.get(thread_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect_thread(thread_id, ws)


# Singleton — imported by notification_service._ws_push
manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket routes
# ─────────────────────────────────────────────────────────────────────────────


@router.websocket("/ws/notifications/{user_id}")
async def ws_notifications(user_id: str, websocket: WebSocket):
    """
    Real-time notification channel for a single user.

    The client connects and keeps the socket open.
    The server pushes JSON payloads whenever a notification is created.
    Clients may send a ping message; the server echoes a pong.
    """
    await manager.connect_user(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo pong so the client can detect a live connection
            if data.strip() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_user(user_id, websocket)


@router.websocket("/ws/messages/{thread_id}")
async def ws_messages(thread_id: str, websocket: WebSocket):
    """
    Real-time messaging channel for a message thread.

    Clients send JSON: {"content": "...", "sender_id": "..."}
    The server broadcasts to all thread participants and persists the message.
    """
    await manager.connect_thread(thread_id, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text('{"error": "invalid JSON"}')
                continue

            sender_id = msg.get("sender_id", "unknown")
            content = msg.get("content", "")

            if not content:
                continue

            # Persist message
            try:
                from backend.db.session import SessionLocal
                from backend.db.models import Message

                db = SessionLocal()
                try:
                    m = Message(
                        thread_id=thread_id,
                        sender_id=sender_id,
                        content=content,
                    )
                    db.add(m)
                    db.commit()
                    db.refresh(m)
                    payload = {
                        "id": m.id,
                        "thread_id": thread_id,
                        "sender_id": sender_id,
                        "content": content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                finally:
                    db.close()
            except Exception:
                logger.exception("Failed to persist WS message")
                payload = {
                    "thread_id": thread_id,
                    "sender_id": sender_id,
                    "content": content,
                }

            await manager.broadcast_to_thread(thread_id, payload)
    except WebSocketDisconnect:
        manager.disconnect_thread(thread_id, websocket)
