# backend/app/websockets/connection_manager.py
from fastapi import WebSocket, status
from typing import Dict, List, Optional, Set, Any
import logging
import json
import asyncio
from datetime import datetime
from app.utils.json_utils import dumps
import time

logger = logging.getLogger("finexia-api")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.tenant_connections: Dict[int, Set[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, Dict] = {}
        self.last_heartbeat = {}  # Track last heartbeat time by client
        self._heartbeat_task = None

        # Connection statistics
        self.connection_stats = {"total_connections": 0, "connections_by_topic": {}, "connections_by_tenant": {}, "max_concurrent": 0, "total_messages_sent": 0, "total_messages_received": 0}

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

        # Track last heartbeat
        self.last_heartbeat[client_id] = time.time()

        # Update stats
        self.connection_stats["total_connections"] += 1
        current_connections = len(self.connection_info)
        if current_connections > self.connection_stats["max_concurrent"]:
            self.connection_stats["max_concurrent"] = current_connections

        # Update topic stats
        if topic not in self.connection_stats["connections_by_topic"]:
            self.connection_stats["connections_by_topic"][topic] = 0
        self.connection_stats["connections_by_topic"][topic] += 1

        # Update tenant stats
        if tenant_id:
            tenant_key = str(tenant_id)
            if tenant_key not in self.connection_stats["connections_by_tenant"]:
                self.connection_stats["connections_by_tenant"][tenant_key] = 0
            self.connection_stats["connections_by_tenant"][tenant_key] += 1

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

        # Remove from heartbeat tracking
        if client_id in self.last_heartbeat:
            del self.last_heartbeat[client_id]

        # Remove connection info
        if websocket in self.connection_info:
            del self.connection_info[websocket]

        logger.info(f"Client {client_id} disconnected from {topic}. Total connections: {self.connection_count}")

    async def broadcast(self, message: Dict, topic: str):
        """Broadcast a message to all connections in a topic"""
        if topic not in self.active_connections:
            return

        disconnected = []
        sent_count = 0

        for connection in self.active_connections[topic]:
            try:
                # Use custom JSON serialization
                json_str = dumps(message)
                await connection.send_text(json_str)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending to client: {str(e)}")
                disconnected.append(connection)

        # Update message count
        self.connection_stats["total_messages_sent"] += sent_count

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_tenant(self, message: Dict, tenant_id: int):
        """Broadcast a message to all connections for a specific tenant"""
        if tenant_id not in self.tenant_connections:
            return

        disconnected = []
        sent_count = 0

        for connection in self.tenant_connections[tenant_id]:
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending to tenant {tenant_id}: {str(e)}")
                disconnected.append(connection)

        # Update message count
        self.connection_stats["total_messages_sent"] += sent_count

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            # Use custom JSON serialization
            json_str = dumps(message)
            await websocket.send_text(json_str)
            self.connection_stats["total_messages_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            self.disconnect(websocket)

    async def start_heartbeat_monitor(self):
        """Start the heartbeat monitoring task"""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Periodically check for stale connections"""
        while True:
            try:
                current_time = time.time()
                stale_connections = []

                # Check for connections without heartbeats in last 30 seconds
                for ws, info in self.connection_info.items():
                    client_id = info.get("client_id")
                    if client_id in self.last_heartbeat:
                        last_beat = self.last_heartbeat[client_id]
                        if current_time - last_beat > 30:  # 30 seconds timeout
                            stale_connections.append(ws)
                            logger.warning(f"Client {client_id} connection stale, disconnecting")

                # Disconnect stale connections
                for ws in stale_connections:
                    await ws.close(code=1001, reason="Connection timeout")
                    self.disconnect(ws)

                # Send heartbeat to all connections
                heartbeat_msg = {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                for topic, connections in self.active_connections.items():
                    for ws in connections:
                        try:
                            await ws.send_json(heartbeat_msg)
                        except Exception as e:
                            logger.debug(f"Error sending heartbeat: {e}")
                            self.disconnect(ws)

                await asyncio.sleep(15)  # Check every 15 seconds
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)  # Retry after 5 seconds on error

    async def record_heartbeat(self, websocket: WebSocket):
        """Record a heartbeat from a client"""
        client_info = self.connection_info.get(websocket)
        if client_info:
            client_id = client_info.get("client_id")
            if client_id:
                self.last_heartbeat[client_id] = time.time()

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics"""
        active_count = len(self.connection_info)
        stats = {"active_connections": active_count, "connections_by_topic": {}, "connections_by_tenant": {}, "historical": {"total_connections": self.connection_stats["total_connections"], "max_concurrent": self.connection_stats["max_concurrent"], "total_messages_sent": self.connection_stats["total_messages_sent"], "total_messages_received": self.connection_stats["total_messages_received"]}}

        # Count current connections by topic
        for ws, info in self.connection_info.items():
            topic = info.get("topic")
            tenant_id = info.get("tenant_id")

            if topic:
                if topic not in stats["connections_by_topic"]:
                    stats["connections_by_topic"][topic] = 0
                stats["connections_by_topic"][topic] += 1

            if tenant_id:
                tenant_key = str(tenant_id)
                if tenant_key not in stats["connections_by_tenant"]:
                    stats["connections_by_tenant"][tenant_key] = 0
                stats["connections_by_tenant"][tenant_key] += 1

        return stats

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
