"""
Base Stream Handler for AWS Strands Streaming

Provides base functionality for streaming responses and real-time data.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, AsyncGenerator, Optional, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)

@dataclass
class StreamEvent:
    """Represents a streaming event."""
    event_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = None

class StreamHandler(ABC):
    """
    Abstract base class for streaming handlers.
    
    Provides common functionality for different streaming implementations.
    """
    
    def __init__(self):
        """Initialize the stream handler."""
        self.is_active = False
        self.event_filters: List[Callable] = []
        self.event_transformers: List[Callable] = []
        
    @abstractmethod
    async def send_event(self, event: StreamEvent) -> bool:
        """
        Send an event through the stream.
        
        Args:
            event: Event to send
            
        Returns:
            True if event was sent successfully
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the stream and cleanup resources."""
        pass
    
    def add_filter(self, filter_func: Callable[[StreamEvent], bool]) -> None:
        """
        Add an event filter function.
        
        Args:
            filter_func: Function that returns True if event should be sent
        """
        self.event_filters.append(filter_func)
    
    def add_transformer(self, transform_func: Callable[[StreamEvent], StreamEvent]) -> None:
        """
        Add an event transformer function.
        
        Args:
            transform_func: Function that transforms the event
        """
        self.event_transformers.append(transform_func)
    
    def _should_send_event(self, event: StreamEvent) -> bool:
        """Check if an event should be sent based on filters."""
        for filter_func in self.event_filters:
            try:
                if not filter_func(event):
                    return False
            except Exception as e:
                logger.error(f"Event filter error: {e}")
                return False
        return True
    
    def _transform_event(self, event: StreamEvent) -> StreamEvent:
        """Apply transformations to an event."""
        transformed_event = event
        for transform_func in self.event_transformers:
            try:
                transformed_event = transform_func(transformed_event)
            except Exception as e:
                logger.error(f"Event transformer error: {e}")
                break
        return transformed_event
    
    async def process_and_send(self, event: StreamEvent) -> bool:
        """
        Process an event through filters and transformers, then send.
        
        Args:
            event: Event to process and send
            
        Returns:
            True if event was processed and sent successfully
        """
        if not self._should_send_event(event):
            return False
        
        transformed_event = self._transform_event(event)
        return await self.send_event(transformed_event)

class AnalysisStreamHandler(StreamHandler):
    """
    Stream handler for AWS Strands analysis results.
    
    Handles streaming of AI analysis results and monitoring insights.
    """
    
    def __init__(self, output_queue: asyncio.Queue):
        """
        Initialize the analysis stream handler.
        
        Args:
            output_queue: Queue to send processed events to
        """
        super().__init__()
        self.output_queue = output_queue
        self.analysis_buffer = []
        self.buffer_size = 10
        
    async def send_event(self, event: StreamEvent) -> bool:
        """Send an analysis event to the output queue."""
        try:
            await self.output_queue.put(event)
            return True
        except Exception as e:
            logger.error(f"Failed to send analysis event: {e}")
            return False
    
    async def send_analysis_chunk(
        self, 
        chunk_data: str, 
        analysis_id: str,
        chunk_type: str = "analysis_chunk"
    ) -> bool:
        """
        Send an analysis chunk as a streaming event.
        
        Args:
            chunk_data: Analysis chunk content
            analysis_id: ID of the analysis session
            chunk_type: Type of chunk
            
        Returns:
            True if chunk was sent successfully
        """
        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type=chunk_type,
            timestamp=datetime.utcnow(),
            data={
                "analysis_id": analysis_id,
                "chunk": chunk_data,
                "chunk_type": chunk_type,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata={"streaming": True}
        )
        
        return await self.process_and_send(event)
    
    async def send_analysis_complete(
        self, 
        analysis_result: Dict[str, Any], 
        analysis_id: str
    ) -> bool:
        """
        Send analysis completion event.
        
        Args:
            analysis_result: Complete analysis result
            analysis_id: ID of the analysis session
            
        Returns:
            True if completion event was sent successfully
        """
        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type="analysis_complete",
            timestamp=datetime.utcnow(),
            data={
                "analysis_id": analysis_id,
                "result": analysis_result,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata={"streaming": False, "final": True}
        )
        
        return await self.process_and_send(event)
    
    async def close(self) -> None:
        """Close the analysis stream handler."""
        self.is_active = False
        logger.info("Analysis stream handler closed")

class MonitoringStreamHandler(StreamHandler):
    """
    Stream handler for monitoring events.
    
    Handles streaming of Kubernetes monitoring events and cluster state changes.
    """
    
    def __init__(self, websocket_manager=None, sse_handler=None):
        """
        Initialize the monitoring stream handler.
        
        Args:
            websocket_manager: Optional WebSocket manager
            sse_handler: Optional SSE handler
        """
        super().__init__()
        self.websocket_manager = websocket_manager
        self.sse_handler = sse_handler
        self.event_history = []
        self.max_history = 1000
        
    async def send_event(self, event: StreamEvent) -> bool:
        """Send a monitoring event through available channels."""
        success_count = 0
        
        # Send through WebSocket if available
        if self.websocket_manager:
            try:
                message = {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                    "metadata": event.metadata or {}
                }
                
                sent_count = await self.websocket_manager.broadcast(
                    message, 
                    subscription="monitoring"
                )
                success_count += sent_count
                
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
        
        # Send through SSE if available
        if self.sse_handler:
            try:
                await self.sse_handler.broadcast_event(
                    event.data,
                    event_type=event.event_type,
                    event_id=event.event_id,
                    subscription_filter="monitoring"
                )
                success_count += 1
                
            except Exception as e:
                logger.error(f"SSE broadcast error: {e}")
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        return success_count > 0
    
    async def send_cluster_event(
        self, 
        event_type: str,
        resource_type: str,
        resource_name: str,
        namespace: Optional[str],
        message: str,
        severity: str = "info",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Send a cluster monitoring event.
        
        Args:
            event_type: Type of cluster event
            resource_type: Kubernetes resource type
            resource_name: Name of the resource
            namespace: Kubernetes namespace
            message: Event message
            severity: Event severity
            metadata: Additional metadata
            
        Returns:
            True if event was sent successfully
        """
        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type="cluster_event",
            timestamp=datetime.utcnow(),
            data={
                "event_type": event_type,
                "resource_type": resource_type,
                "resource_name": resource_name,
                "namespace": namespace,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat()
            },
            metadata=metadata or {}
        )
        
        return await self.process_and_send(event)
    
    async def send_health_status(self, health_data: Dict[str, Any]) -> bool:
        """
        Send cluster health status update.
        
        Args:
            health_data: Health status data
            
        Returns:
            True if status was sent successfully
        """
        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type="health_status",
            timestamp=datetime.utcnow(),
            data=health_data,
            metadata={"category": "health"}
        )
        
        return await self.process_and_send(event)
    
    def get_recent_events(self, count: int = 50) -> List[StreamEvent]:
        """Get recent monitoring events."""
        return self.event_history[-count:] if self.event_history else []
    
    async def close(self) -> None:
        """Close the monitoring stream handler."""
        self.is_active = False
        logger.info("Monitoring stream handler closed")

# Utility functions for common stream operations

def create_severity_filter(min_severity: str) -> Callable[[StreamEvent], bool]:
    """
    Create a filter that only allows events above a certain severity.
    
    Args:
        min_severity: Minimum severity level
        
    Returns:
        Filter function
    """
    severity_levels = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}
    min_level = severity_levels.get(min_severity.lower(), 1)
    
    def severity_filter(event: StreamEvent) -> bool:
        event_severity = event.data.get("severity", "info")
        event_level = severity_levels.get(event_severity.lower(), 1)
        return event_level >= min_level
    
    return severity_filter

def create_namespace_filter(allowed_namespaces: List[str]) -> Callable[[StreamEvent], bool]:
    """
    Create a filter that only allows events from specific namespaces.
    
    Args:
        allowed_namespaces: List of allowed namespace names
        
    Returns:
        Filter function
    """
    def namespace_filter(event: StreamEvent) -> bool:
        event_namespace = event.data.get("namespace")
        return event_namespace is None or event_namespace in allowed_namespaces
    
    return namespace_filter

def create_event_type_filter(allowed_types: List[str]) -> Callable[[StreamEvent], bool]:
    """
    Create a filter that only allows specific event types.
    
    Args:
        allowed_types: List of allowed event types
        
    Returns:
        Filter function
    """
    def type_filter(event: StreamEvent) -> bool:
        return event.event_type in allowed_types
    
    return type_filter
