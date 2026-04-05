import asyncio
from http.cookies import SimpleCookie

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from starlette.websockets import WebSocketState

from app.core.security import SECRET_KEY, ALGORITHM
from app.ws_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    # Prefer cookie-based token; fall back to query parameter
    if not token:
        cookie_header = websocket.headers.get("cookie", "")
        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            if "access_token" in cookie:
                token = cookie["access_token"].value

    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=4001)
            return
        user_id = int(user_id)
    except (JWTError, Exception):
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Use a timeout so we can send periodic pings to keep the connection alive
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send a ping to keep connection alive
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({"type": "ping"})
    except (WebSocketDisconnect, Exception):
        manager.disconnect(user_id, websocket)
