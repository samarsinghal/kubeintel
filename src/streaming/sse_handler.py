"""
Server-Sent Events (SSE) Handler for Streaming Responses

Provides SSE streaming capabilities for real-time monitoring data.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, Optional, List
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)

@dataclass
class SSEClient:
    """Represents an SSE client connection."""
    client_id: str
    connected_at: datetime
    subscriptions: set
    last_event_id: Optional[str] = None

class SSEHandler:
    """
    Server-Sent Events handler for streaming monitoring data.
    
    Features:
    - Real-time event streaming
    - Client reconnection support
    - Event filtering and routing
    - Connection management
    """
    
    def __init__(self):
        """Initialize the SSE handler."""
        self.clients: Dict[str, SSEClient] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        logger.info("SSE Handler initialized")
    
    async def create_stream(
        self, 
        client_id: Optional[str] = None,
        last_event_id: Optional[str] = None,
        subscriptions: List[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Create an SSE stream for a client.
        
        Args:
            client_id: Optional client identifier
            last_event_id: Last event ID for reconnection
            subscriptions: List of event types to subscribe to
            
        Yields:
            SSE formatted strings
        """
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Register client
        client = SSEClient(
            client_id=client_id,
            connected_at=datetime.utcnow(),
            subscriptions=set(subscriptions or []),
            last_event_id=last_event_id
        )
        self.clients[client_id] = client
        
        logger.info(f"SSE client connected: {client_id}")
        
        try:
            # Send initial connection event
            yield self._format_sse_event({
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to AWS Strands Kubernetes Monitoring"
            }, event_type="connection")
            
            # Send missed events if reconnecting
            if last_event_id:
                async for event in self._get_missed_events(last_event_id):
                    yield event
            
            # Keep connection alive and stream events
            while True:
                # Send heartbeat every 30 seconds
                yield self._format_sse_event({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                }, event_type="heartbeat")
                
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"SSE stream error for client {client_id}: {e}")
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def broadcast_event(
        self, 
        event_data: Dict[str, Any], 
        event_type: str = "data",
        event_id: Optional[str] = None,
        subscription_filter: Optional[str] = None
    ) -> int:
        """
        Broadcast an event to all connected SSE clients.
        
        Args:
            event_data: Event data to broadcast
            event_type: SSE event type
            event_id: Optional event ID
            subscription_filter: Optional subscription filter
            
        Returns:
            Number of clients that received the event
        """
        if not event_id:
            event_id = str(uuid.uuid4())
        
        # Add to event history
        event_record = {
            "id": event_id,
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
            "subscription": subscription_filter
        }
        
        self.event_history.append(event_record)
        
        # Trim history if too large
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
        
        # Format SSE event
        sse_event = self._format_sse_event(event_data, event_type, event_id)
        
        # Send to clients (this would typically be handled by a queue/pub-sub system)
        # For now, we'll store the event for clients to pick up
        logger.debug(f"Event broadcasted: {event_type} (ID: {event_id})")
        
        return len(self.clients)  # Return number of potential recipients
    
    def _format_sse_event(
        self, 
        data: Dict[str, Any], 
        event_type: str = "data",
        event_id: Optional[str] = None
    ) -> str:
        """
        Format data as an SSE event.
        
        Args:
            data: Event data
            event_type: SSE event type
            event_id: Optional event ID
            
        Returns:
            SSE formatted string
        """
        lines = []
        
        if event_id:
            lines.append(f"id: {event_id}")
        
        if event_type:
            lines.append(f"event: {event_type}")
        
        # Handle multi-line data
        data_str = json.dumps(data)
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        lines.append("")  # Empty line to end the event
        
        return "\n".join(lines) + "\n"
    
    async def _get_missed_events(self, last_event_id: str) -> AsyncGenerator[str, None]:
        """
        Get events that were missed since the last event ID.
        
        Args:
            last_event_id: Last received event ID
            
        Yields:
            SSE formatted missed events
        """
        # Find the index of the last event
        last_index = -1
        for i, event in enumerate(self.event_history):
            if event["id"] == last_event_id:
                last_index = i
                break
        
        # Send events after the last received one
        if last_index >= 0:
            missed_events = self.event_history[last_index + 1:]
            for event in missed_events:
                yield self._format_sse_event(
                    event["data"], 
                    event["type"], 
                    event["id"]
                )
    
    def get_client_count(self) -> int:
        """Get the number of connected SSE clients."""
        return len(self.clients)
    
    def get_status(self) -> Dict[str, Any]:
        """Get SSE handler status."""
        return {
            "connected_clients": len(self.clients),
            "event_history_size": len(self.event_history),
            "max_history_size": self.max_history_size,
            "clients": [
                {
                    "client_id": client.client_id,
                    "connected_at": client.connected_at.isoformat(),
                    "subscriptions": list(client.subscriptions),
                    "last_event_id": client.last_event_id
                }
                for client in self.clients.values()
            ]
        }

class MonitoringSSEStream:
    """
    Specialized SSE stream for monitoring events.
    
    Provides structured streaming of Kubernetes monitoring data.
    """
    
    def __init__(self, sse_handler: SSEHandler):
        """Initialize the monitoring SSE stream."""
        self.sse_handler = sse_handler
        self.event_queue = asyncio.Queue()
        self.is_streaming = False
    
    async def start_streaming(self) -> AsyncGenerator[str, None]:
        """Start streaming monitoring events."""
        self.is_streaming = True
        
        try:
            # Send initial status
            yield self.sse_handler._format_sse_event({
                "type": "stream_started",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Monitoring stream started"
            }, event_type="status")
            
            # Stream events from queue
            while self.is_streaming:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(
                        self.event_queue.get(), 
                        timeout=30.0
                    )
                    
                    yield self.sse_handler._format_sse_event(
                        event["data"],
                        event.get("type", "monitoring"),
                        event.get("id")
                    )
                    
                except asyncio.TimeoutError:
                    # Send heartbeat on timeout
                    yield self.sse_handler._format_sse_event({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    }, event_type="heartbeat")
                    
        except asyncio.CancelledError:
            logger.info("Monitoring SSE stream cancelled")
        finally:
            self.is_streaming = False
    
    async def add_event(self, event_data: Dict[str, Any], event_type: str = "monitoring") -> None:
        """
        Add an event to the streaming queue.
        
        Args:
            event_data: Event data to stream
            event_type: Type of event
        """
        if self.is_streaming:
            await self.event_queue.put({
                "data": event_data,
                "type": event_type,
                "id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def stop_streaming(self) -> None:
        """Stop the streaming."""
        self.is_streaming = False
