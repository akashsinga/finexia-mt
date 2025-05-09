# backend/app/websockets/connection_manager.py
from fastapi import WebSocket, status
from typing import Dict, List, Optional, Set
import logging
import json
import asyncio
from datetime import datetime

logger = logging.getLogger("finexia-api")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.tenant_connections: Dict[int, Set[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str, topic: str, tenant_id: Optional[int] = None, user_id: Optional[int] = None):
        """Connect a client to a specific topic"""
        await websocket.accept()

        # Initialize topic if doesn't exist
        if topic not in self.active_connections:
            self.active_connections[topic] = []

        # Store connection with metadata
        self.active_connections[topic].append(websocket)
        self.connection_info[websocket] = {"client_id": client_id, "topic": topic, "tenant_id": tenant_id, "user_id": user_id, "connected_at": datetime.now()}

        # Track by tenant for tenant-specific broadcasts
        if tenant_id:
            if tenant_id not in self.tenant_connections:
                self.tenant_connections[tenant_id] = set()
            self.tenant_connections[tenant_id].add(websocket)

        logger.info(f"Client {client_id} connected to {topic}. Total connections: {self.connection_count}")

        # Send welcome message
        await websocket.send_json({"type": "connected", "timestamp": datetime.now().isoformat(), "data": {"message": f"Connected to {topic}", "client_id": client_id}})

    def disconnect(self, websocket: WebSocket):
        """Disconnect a client from all topics"""
        if websocket not in self.connection_info:
            return

        # Get connection info before removing
        client_info = self.connection_info[websocket]
        topic = client_info["topic"]
        tenant_id = client_info["tenant_id"]
        client_id = client_info["client_id"]

        # Remove from topic
        if topic in self.active_connections:
            if websocket in self.active_connections[topic]:
                self.active_connections[topic].remove(websocket)

        # Remove from tenant tracking
        if tenant_id in self.tenant_connections:
            if websocket in self.tenant_connections[tenant_id]:
                self.tenant_connections[tenant_id].remove(websocket)

        # Remove connection info
        if websocket in self.connection_info:
            del self.connection_info[websocket]

        logger.info(f"Client {client_id} disconnected from {topic}. Total connections: {self.connection_count}")

    async def broadcast(self, message: Dict, topic: str):
        """Broadcast a message to all connections in a topic"""
        if topic not in self.active_connections:
            return

        disconnected = []

        for connection in self.active_connections[topic]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {str(e)}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_tenant(self, message: Dict, tenant_id: int):
        """Broadcast a message to all connections for a specific tenant"""
        if tenant_id not in self.tenant_connections:
            return

        disconnected = []

        for connection in self.tenant_connections[tenant_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to tenant {tenant_id}: {str(e)}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.connection_info)

    def get_stats(self) -> Dict:
        """Get connection statistics"""
        # Count by tenant
        tenant_counts = {}
        for conn, info in self.connection_info.items():
            tenant_id = info.get("tenant_id")
            if tenant_id:
                tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1

        # Count by topic
        topic_counts = {topic: len(conns) for topic, conns in self.active_connections.items()}

        return {"total_connections": self.connection_count, "tenant_counts": tenant_counts, "topic_counts": topic_counts}


# Create a global instance of the manager
connection_manager = ConnectionManager()
