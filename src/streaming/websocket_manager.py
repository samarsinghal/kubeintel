"""
WebSocket Manager for Real-time Streaming

Handles WebSocket connections for real-time monitoring data streaming.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, asdict
import uuid

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client."""
    client_id: str
    websocket: WebSocket
    connected_at: datetime
    subscriptions: Set[str]
    metadata: Dict[str, Any]

class WebSocketManager:
    """
    Manages WebSocket connections for real-time streaming.
    
    Features:
    - Client connection management
    - Subscription-based message routing
    - Broadcast capabilities
    - Connection health monitoring
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.clients: Dict[str, WebSocketClient] = {}
        self.subscription_groups: Dict[str, Set[str]] = {}  # subscription -> client_ids
        self.is_running = False
        
        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.health_check_task = None
        
        logger.info("WebSocket Manager initialized")
    
    async def connect(self, websocket: WebSocket, client_metadata: Dict[str, Any] = None) -> str:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            client_metadata: Optional client metadata
            
        Returns:
            Client ID for the new connection
        """
        await websocket.accept()
        
        client_id = str(uuid.uuid4())
        client = WebSocketClient(
            client_id=client_id,
            websocket=websocket,
            connected_at=datetime.utcnow(),
            subscriptions=set(),
            metadata=client_metadata or {}
        )
        
        self.clients[client_id] = client
        
        logger.info(f"WebSocket client connected: {client_id}")
        
        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to AWS Strands Kubernetes Monitoring"
        })
        
        return client_id
    
    async def disconnect(self, client_id: str) -> None:
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: ID of the client to disconnect
        """
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        # Remove from all subscriptions
        for subscription in client.subscriptions.copy():
            await self.unsubscribe(client_id, subscription)
        
        # Remove client
        del self.clients[client_id]
        
        logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client ID
            message: Message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        
        try:
            await client.websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            # Remove disconnected client
            await self.disconnect(client_id)
            return False
    
    async def broadcast(self, message: Dict[str, Any], subscription: Optional[str] = None) -> int:
        """
        Broadcast a message to all clients or clients with specific subscription.
        
        Args:
            message: Message to broadcast
            subscription: Optional subscription filter
            
        Returns:
            Number of clients that received the message
        """
        if subscription:
            # Send to subscribed clients only
            client_ids = self.subscription_groups.get(subscription, set())
        else:
            # Send to all clients
            client_ids = set(self.clients.keys())
        
        successful_sends = 0
        failed_clients = []
        
        for client_id in client_ids:
            if await self.send_to_client(client_id, message):
                successful_sends += 1
            else:
                failed_clients.append(client_id)
        
        # Clean up failed clients
        for client_id in failed_clients:
            await self.disconnect(client_id)
        
        if subscription:
            logger.debug(f"Broadcasted to {successful_sends} clients in subscription '{subscription}'")
        else:
            logger.debug(f"Broadcasted to {successful_sends} clients")
        
        return successful_sends
    
    async def subscribe(self, client_id: str, subscription: str) -> bool:
        """
        Subscribe a client to a specific message type.
        
        Args:
            client_id: Client to subscribe
            subscription: Subscription name
            
        Returns:
            True if subscription was successful
        """
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        client.subscriptions.add(subscription)
        
        # Add to subscription group
        if subscription not in self.subscription_groups:
            self.subscription_groups[subscription] = set()
        self.subscription_groups[subscription].add(client_id)
        
        logger.info(f"Client {client_id} subscribed to '{subscription}'")
        
        # Send confirmation
        await self.send_to_client(client_id, {
            "type": "subscription_confirmed",
            "subscription": subscription,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def unsubscribe(self, client_id: str, subscription: str) -> bool:
        """
        Unsubscribe a client from a specific message type.
        
        Args:
            client_id: Client to unsubscribe
            subscription: Subscription name
            
        Returns:
            True if unsubscription was successful
        """
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        client.subscriptions.discard(subscription)
        
        # Remove from subscription group
        if subscription in self.subscription_groups:
            self.subscription_groups[subscription].discard(client_id)
            
            # Clean up empty subscription groups
            if not self.subscription_groups[subscription]:
                del self.subscription_groups[subscription]
        
        logger.info(f"Client {client_id} unsubscribed from '{subscription}'")
        
        # Send confirmation
        await self.send_to_client(client_id, {
            "type": "unsubscription_confirmed",
            "subscription": subscription,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def handle_client_message(self, client_id: str, message: str) -> None:
        """
        Handle incoming message from a WebSocket client.
        
        Args:
            client_id: ID of the sending client
            message: Raw message string
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe":
                subscription = data.get("subscription")
                if subscription:
                    await self.subscribe(client_id, subscription)
            
            elif message_type == "unsubscribe":
                subscription = data.get("subscription")
                if subscription:
                    await self.unsubscribe(client_id, subscription)
            
            elif message_type == "ping":
                # Respond to ping with pong
                await self.send_to_client(client_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif message_type == "get_status":
                # Send client status
                client = self.clients.get(client_id)
                if client:
                    await self.send_to_client(client_id, {
                        "type": "client_status",
                        "client_id": client_id,
                        "connected_at": client.connected_at.isoformat(),
                        "subscriptions": list(client.subscriptions),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {message}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Invalid JSON format",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Internal server error",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def start_health_monitoring(self) -> None:
        """Start health monitoring for WebSocket connections."""
        if self.is_running:
            return
        
        self.is_running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("WebSocket health monitoring started")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        self.is_running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket health monitoring stopped")
    
    async def _health_check_loop(self) -> None:
        """Health check loop for WebSocket connections."""
        while self.is_running:
            try:
                # Send ping to all clients
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                disconnected_clients = []
                
                for client_id, client in self.clients.items():
                    try:
                        await client.websocket.send_text(json.dumps(ping_message))
                    except Exception:
                        disconnected_clients.append(client_id)
                
                # Clean up disconnected clients
                for client_id in disconnected_clients:
                    await self.disconnect(client_id)
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self.clients)
    
    def get_subscription_stats(self) -> Dict[str, int]:
        """Get statistics about subscriptions."""
        return {
            subscription: len(client_ids)
            for subscription, client_ids in self.subscription_groups.items()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get WebSocket manager status."""
        return {
            "connected_clients": len(self.clients),
            "active_subscriptions": len(self.subscription_groups),
            "subscription_stats": self.get_subscription_stats(),
            "health_monitoring": self.is_running,
            "clients": [
                {
                    "client_id": client.client_id,
                    "connected_at": client.connected_at.isoformat(),
                    "subscriptions": list(client.subscriptions),
                    "metadata": client.metadata
                }
                for client in self.clients.values()
            ]
        }
    
    async def cleanup(self) -> None:
        """Clean up all connections and resources."""
        logger.info("Cleaning up WebSocket manager")
        
        # Stop health monitoring
        await self.stop_health_monitoring()
        
        # Disconnect all clients
        client_ids = list(self.clients.keys())
        for client_id in client_ids:
            await self.disconnect(client_id)
        
        # Clear data structures
        self.clients.clear()
        self.subscription_groups.clear()
        
        logger.info("WebSocket manager cleanup complete")
