from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections for real-time risk broadcasting."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Pushes a message to all connected clients (Real-time update)."""
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Handle stale connections
                continue

manager = ConnectionManager()

@router.websocket("/ws/risk-hub")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket hub for Real-Time Decision Intelligence.
    Connects the Frontend to the live Risk & EFI streams.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; 
            # In a real app, we might handle incoming client messages here
            data = await websocket.receive_text()
            # Echo for testing
            await websocket.send_text(f"ACK: Risk Hub Active for {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def push_risk_update(event_type: str, data: dict):
    """Utility function to be called from Pillar 2/5 when a crisis is detected."""
    await manager.broadcast({
        "type": event_type,
        "timestamp": "now",
        "payload": data
    })
