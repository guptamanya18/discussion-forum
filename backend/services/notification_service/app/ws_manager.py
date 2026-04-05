import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("User %s connected via WebSocket (%d total connections)", user_id, len(self.active_connections[user_id]))

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("User %s disconnected from WebSocket", user_id)

    async def send_to_user(self, user_id: int, data: dict):
        if user_id not in self.active_connections:
            logger.info("User %s not connected, skipping WebSocket push", user_id)
            return
        dead = []
        for ws in self.active_connections[user_id]:
            try:
                await ws.send_json(data)
                logger.info("Pushed notification to user %s via WebSocket", user_id)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections[user_id].remove(ws)
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]

    async def broadcast(self, data: dict):
        """Send a message to ALL connected clients."""
        total_clients = sum(len(ws_list) for ws_list in self.active_connections.values())
        user_ids = list(self.active_connections.keys())
        logger.info("Broadcasting to %d clients (users: %s), data type: %s", total_clients, user_ids, data.get("type"))
        dead_connections = []
        sent_count = 0
        for user_id, ws_list in self.active_connections.items():
            for ws in ws_list:
                try:
                    await ws.send_json(data)
                    sent_count += 1
                    logger.info("Broadcast sent to user %s", user_id)
                except Exception as e:
                    logger.warning("Failed to send broadcast to user %s: %s", user_id, e)
                    dead_connections.append((user_id, ws))
        for user_id, ws in dead_connections:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(ws)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info("Broadcast complete: %d/%d successful", sent_count, total_clients)


manager = ConnectionManager()
