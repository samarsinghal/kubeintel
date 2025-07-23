"""
AWS Strands Event Loop Implementation

Provides continuous monitoring and event-driven analysis of Kubernetes clusters.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, AsyncGenerator
import json
from dataclasses import dataclass, asdict

from strands import Agent

from ..k8s.client import KubernetesClient
from ..k8s.collector import DataCollector
from ..models.kubernetes import ClusterData
from .event_processor import EventProcessor
from .monitoring_scheduler import MonitoringScheduler
from .predictive_analytics import PredictiveAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class MonitoringEvent:
    """Represents a monitoring event in the system."""
    event_id: str
    event_type: str
    timestamp: datetime
    namespace: Optional[str]
    resource_type: str
    resource_name: str
    message: str
    severity: str
    metadata: Dict[str, Any]

class KubernetesEventLoop:
    """
    AWS Strands-powered event loop for continuous Kubernetes monitoring.
    
    This class implements:
    - Continuous cluster monitoring
    - Event-driven analysis
    - Real-time streaming responses
    - Intelligent alerting and notifications
    """
    
    def __init__(
        self,
        strands_agent: Agent,
        k8s_client: KubernetesClient,
        data_collector: DataCollector,
        monitoring_interval: int = 30,
        event_batch_size: int = 10,
        enable_streaming: bool = False
    ):
        """
        Initialize the Kubernetes Event Loop.
        
        Args:
            strands_agent: The AWS Strands agent instance
            k8s_client: Kubernetes API client
            data_collector: Data collection service
            monitoring_interval: Seconds between monitoring cycles
            event_batch_size: Number of events to process in batch
            enable_streaming: Enable streaming responses
        """
        self.strands_agent = strands_agent
        self.k8s_client = k8s_client
        self.data_collector = data_collector
        self.monitoring_interval = monitoring_interval
        self.event_batch_size = event_batch_size
        self.enable_streaming = enable_streaming
        
        # Event processing components
        self.event_processor = EventProcessor(strands_agent)
        self.scheduler = MonitoringScheduler(monitoring_interval)
        self.predictive_analyzer = PredictiveAnalyzer()
        
        # State management
        self.is_running = False
        self.last_analysis_time = None
        self.event_queue = asyncio.Queue()
        self.subscribers = []
        self.cluster_state = {}
        self.cluster_snapshots = []  # Store snapshots for predictive analytics
        
        # Performance tracking
        self.metrics = {
            "events_processed": 0,
            "analyses_completed": 0,
            "errors_encountered": 0,
            "last_cycle_duration": 0,
            "predictions_generated": 0
        }
        
        logger.info("Kubernetes Event Loop initialized")
    
    async def start(self) -> None:
        """Start the event loop and begin continuous monitoring."""
        if self.is_running:
            logger.warning("Event loop is already running")
            return
        
        self.is_running = True
        logger.info("Starting AWS Strands Kubernetes Event Loop")
        
        # Start background tasks without waiting for them
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._event_processing_task = asyncio.create_task(self._event_processing_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Event loop background tasks started")
    
    async def stop(self) -> None:
        """Stop the event loop and cleanup resources."""
        logger.info("Stopping AWS Strands Kubernetes Event Loop")
        self.is_running = False
        
        # Cancel specific background tasks
        tasks_to_cancel = []
        if hasattr(self, '_monitoring_task') and not self._monitoring_task.done():
            tasks_to_cancel.append(self._monitoring_task)
        if hasattr(self, '_event_processing_task') and not self._event_processing_task.done():
            tasks_to_cancel.append(self._event_processing_task)
        if hasattr(self, '_health_check_task') and not self._health_check_task.done():
            tasks_to_cancel.append(self._health_check_task)
        
        for task in tasks_to_cancel:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event loop stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that continuously watches the cluster."""
        logger.info("Starting monitoring loop")
        
        while self.is_running:
            try:
                cycle_start = datetime.utcnow()
                
                # Collect current cluster state
                cluster_data = await self.data_collector.collect_cluster_data(
                    include_logs=False  # Logs collected on-demand
                )
                
                # Create cluster snapshot for predictive analytics
                await self._create_cluster_snapshot(cluster_data)
                
                # Detect changes and generate events
                events = await self._detect_cluster_changes(cluster_data)
                
                # Queue events for processing
                for event in events:
                    await self.event_queue.put(event)
                
                # Update metrics
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                self.metrics["last_cycle_duration"] = cycle_duration
                self.last_analysis_time = datetime.utcnow()
                
                logger.debug(f"Monitoring cycle completed in {cycle_duration:.2f}s, {len(events)} events generated")
                
                # Wait for next cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                self.metrics["errors_encountered"] += 1
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _event_processing_loop(self) -> None:
        """Process events from the queue using AWS Strands analysis."""
        logger.info("Starting event processing loop")
        
        while self.is_running:
            try:
                # Collect events in batches
                events = []
                timeout = 1.0  # Wait up to 1 second for events
                
                try:
                    # Get first event (blocking)
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=timeout)
                    events.append(event)
                    
                    # Collect additional events (non-blocking)
                    while len(events) < self.event_batch_size:
                        try:
                            event = self.event_queue.get_nowait()
                            events.append(event)
                        except asyncio.QueueEmpty:
                            break
                            
                except asyncio.TimeoutError:
                    continue  # No events to process
                
                if events:
                    await self._process_event_batch(events)
                    
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self.metrics["errors_encountered"] += 1
                await asyncio.sleep(1)
    
    async def _health_check_loop(self) -> None:
        """Periodic health checks and system maintenance."""
        while self.is_running:
            try:
                # Check system health
                await self._perform_health_check()
                
                # Log metrics periodically
                if self.metrics["events_processed"] % 100 == 0:
                    logger.info(f"Event loop metrics: {self.metrics}")
                
                await asyncio.sleep(60)  # Health check every minute
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)
    
    async def _detect_cluster_changes(self, current_data: ClusterData) -> List[MonitoringEvent]:
        """Detect changes in cluster state and generate events."""
        events = []
        
        try:
            # Convert current data to comparable format
            current_state = self._cluster_data_to_state(current_data)
            
            if not self.cluster_state:
                # First run - establish baseline
                self.cluster_state = current_state
                events.append(MonitoringEvent(
                    event_id=f"baseline-{datetime.utcnow().isoformat()}",
                    event_type="baseline_established",
                    timestamp=datetime.utcnow(),
                    namespace=None,
                    resource_type="cluster",
                    resource_name="cluster",
                    message="Baseline cluster state established",
                    severity="info",
                    metadata={"pod_count": len(current_data.pods), "service_count": len(current_data.services)}
                ))
                return events
            
            # Detect pod changes
            events.extend(await self._detect_pod_changes(current_state, self.cluster_state))
            
            # Detect service changes
            events.extend(await self._detect_service_changes(current_state, self.cluster_state))
            
            # Detect new events
            events.extend(await self._detect_new_events(current_data))
            
            # Update stored state
            self.cluster_state = current_state
            
        except Exception as e:
            logger.error(f"Error detecting cluster changes: {e}")
            events.append(MonitoringEvent(
                event_id=f"error-{datetime.utcnow().isoformat()}",
                event_type="detection_error",
                timestamp=datetime.utcnow(),
                namespace=None,
                resource_type="system",
                resource_name="event_loop",
                message=f"Error detecting changes: {str(e)}",
                severity="error",
                metadata={"error": str(e)}
            ))
        
        return events
    
    async def _process_event_batch(self, events: List[MonitoringEvent]) -> None:
        """Process a batch of events using AWS Strands analysis."""
        try:
            # Create analysis prompt from events
            prompt = self._create_analysis_prompt(events)
            
            # Generate predictive insights if we have sufficient history
            predictions = []
            if len(self.cluster_snapshots) >= 10:
                predictions = await self.predictive_analyzer.generate_predictions(self.cluster_snapshots)
                if predictions:
                    logger.info(f"Generated {len(predictions)} predictions")
                    # Add predictions to the analysis context
                    prompt += self._add_predictions_to_prompt(predictions)
            
            # Use Strands agent for intelligent analysis
            # ALWAYS use non-streaming mode to avoid "tool use in streaming mode" error
            if False:  # Force disable streaming completely
                # Stream analysis results
                async for chunk in self._stream_analysis(prompt, events):
                    await self._broadcast_to_subscribers(chunk)
            else:
                # Single analysis result
                result = await self._analyze_events(prompt, events)
                await self._broadcast_to_subscribers(result)
            
            # Broadcast predictions separately if available
            if predictions:
                prediction_result = {
                    "type": "predictions",
                    "timestamp": datetime.utcnow().isoformat(),
                    "predictions": [
                        {
                            "id": p.prediction_id,
                            "type": p.prediction_type,
                            "description": p.description,
                            "confidence": p.confidence,
                            "severity": p.severity,
                            "time_frame": p.time_frame,
                            "probability": p.probability,
                            "impact": p.impact_assessment,
                            "actions": p.recommended_actions
                        }
                        for p in predictions
                    ]
                }
                await self._broadcast_to_subscribers(prediction_result)
            
            # Update metrics
            self.metrics["events_processed"] += len(events)
            self.metrics["analyses_completed"] += 1
            if predictions:
                self.metrics["predictions_generated"] = self.metrics.get("predictions_generated", 0) + len(predictions)
            
        except Exception as e:
            logger.error(f"Error processing event batch: {e}")
            self.metrics["errors_encountered"] += 1
    
    def _create_analysis_prompt(self, events: List[MonitoringEvent]) -> str:
        """Create an analysis prompt from monitoring events."""
        if not events:
            return "No recent events detected. Cluster appears to be operating normally. Please provide a brief status summary."
        
        try:
            prompt_parts = [
                "Analyze the following Kubernetes cluster events and provide insights:",
                "",
                f"Event Summary: {len(events)} events detected",
            ]
            
            # Safely get time range
            try:
                timestamps = [e.timestamp for e in events if e.timestamp]
                if timestamps:
                    prompt_parts.append(f"Time Range: {min(timestamps)} to {max(timestamps)}")
            except Exception as e:
                logger.debug(f"Error getting time range: {e}")
                prompt_parts.append("Time Range: Recent events")
            
            prompt_parts.extend(["", "Events:"])
            
            for i, event in enumerate(events, 1):
                try:
                    # Safely format each event
                    severity = getattr(event, 'severity', 'unknown').upper()
                    event_type = getattr(event, 'event_type', 'unknown')
                    resource_type = getattr(event, 'resource_type', 'unknown')
                    resource_name = getattr(event, 'resource_name', 'unknown')
                    namespace = getattr(event, 'namespace', None) or 'cluster-wide'
                    message = getattr(event, 'message', 'No message available')
                    timestamp = getattr(event, 'timestamp', 'Unknown time')
                    
                    prompt_parts.append(f"{i}. [{severity}] {event_type}")
                    prompt_parts.append(f"   Resource: {resource_type}/{resource_name}")
                    prompt_parts.append(f"   Namespace: {namespace}")
                    prompt_parts.append(f"   Message: {message}")
                    prompt_parts.append(f"   Time: {timestamp}")
                    prompt_parts.append("")
                except Exception as e:
                    logger.debug(f"Error formatting event {i}: {e}")
                    prompt_parts.append(f"{i}. [ERROR] Failed to format event")
                    prompt_parts.append("")
            
            prompt_parts.extend([
                "Please provide:",
                "1. Summary of the most critical issues",
                "2. Recommended actions to take",
                "3. Potential impact assessment",
                "4. Priority level for each issue"
            ])
            
            prompt = "\n".join(prompt_parts)
            
            # Ensure prompt is not empty and has meaningful content
            if len(prompt.strip()) < 50:
                return "Please analyze the current Kubernetes cluster status and provide a health assessment."
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating analysis prompt: {e}")
            return "Please provide a general Kubernetes cluster health analysis."
    
    async def _stream_analysis(self, prompt: str, events: List[MonitoringEvent]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream analysis results using AWS Strands - DISABLED FOR TITAN COMPATIBILITY."""
        # This method is disabled to prevent "tool use in streaming mode" errors
        # Instead, return a single analysis result
        try:
            result = await self._analyze_events(prompt, events)
            yield result
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            yield {
                "type": "analysis_error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "streaming": False
            }
    
    async def _analyze_events(self, prompt: str, events: List[MonitoringEvent]) -> Dict[str, Any]:
        """Analyze events using AWS Strands (non-streaming)."""
        try:
            # Use Strands agent for analysis
            result = await self.strands_agent.invoke_async(prompt)
            
            return {
                "type": "analysis_complete",
                "timestamp": datetime.utcnow().isoformat(),
                "event_count": len(events),
                "analysis": result,
                "events": [asdict(event) for event in events],
                "streaming": False
            }
        except Exception as e:
            logger.error(f"Event analysis error: {e}")
            return {
                "type": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "event_count": len(events)
            }
    
    async def _broadcast_to_subscribers(self, data: Dict[str, Any]) -> None:
        """Broadcast analysis results to all subscribers."""
        if not self.subscribers:
            return
        
        # Send to all active subscribers
        for subscriber in self.subscribers[:]:  # Copy list to avoid modification during iteration
            try:
                await subscriber.send(data)
            except Exception as e:
                logger.warning(f"Failed to send to subscriber: {e}")
                # Remove failed subscriber
                if subscriber in self.subscribers:
                    self.subscribers.remove(subscriber)
    
    def subscribe(self, subscriber) -> None:
        """Add a subscriber for real-time updates."""
        self.subscribers.append(subscriber)
        logger.info(f"New subscriber added. Total subscribers: {len(self.subscribers)}")
    
    def unsubscribe(self, subscriber) -> None:
        """Remove a subscriber."""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"Subscriber removed. Total subscribers: {len(self.subscribers)}")
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        health_status = {
            "event_loop_running": self.is_running,
            "last_analysis": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "queue_size": self.event_queue.qsize(),
            "subscriber_count": len(self.subscribers),
            "metrics": self.metrics.copy(),
            "kubernetes_connection": False,
            "strands_agent_ready": False
        }
        
        try:
            # Test Kubernetes connection using the correct method
            health_status["kubernetes_connection"] = self.k8s_client.health_check()
        except Exception as e:
            logger.warning(f"Kubernetes health check failed: {e}")
        
        try:
            # Test Strands agent - simplified check for 1.0.x
            health_status["strands_agent_ready"] = self.strands_agent is not None
        except Exception as e:
            logger.warning(f"Strands agent health check failed: {e}")
        
        return health_status
    
    def _cluster_data_to_state(self, cluster_data: ClusterData) -> Dict[str, Any]:
        """Convert cluster data to a comparable state representation."""
        return {
            "pods": {pod.name: {
                "namespace": pod.namespace,
                "status": pod.status,
                "ready": pod.ready,
                "restarts": pod.restart_count
            } for pod in cluster_data.pods},
            "services": {svc.name: {
                "namespace": svc.namespace,
                "type": svc.type,
                "cluster_ip": svc.cluster_ip
            } for svc in cluster_data.services},
            "timestamp": datetime.utcnow()
        }
    
    async def _detect_pod_changes(self, current: Dict, previous: Dict) -> List[MonitoringEvent]:
        """Detect changes in pod states."""
        events = []
        current_pods = current.get("pods", {})
        previous_pods = previous.get("pods", {})
        
        # New pods
        for pod_name, pod_data in current_pods.items():
            if pod_name not in previous_pods:
                events.append(MonitoringEvent(
                    event_id=f"pod-new-{pod_name}-{datetime.utcnow().isoformat()}",
                    event_type="pod_created",
                    timestamp=datetime.utcnow(),
                    namespace=pod_data["namespace"],
                    resource_type="pod",
                    resource_name=pod_name,
                    message=f"New pod created: {pod_name}",
                    severity="info",
                    metadata=pod_data
                ))
        
        # Deleted pods
        for pod_name, pod_data in previous_pods.items():
            if pod_name not in current_pods:
                events.append(MonitoringEvent(
                    event_id=f"pod-deleted-{pod_name}-{datetime.utcnow().isoformat()}",
                    event_type="pod_deleted",
                    timestamp=datetime.utcnow(),
                    namespace=pod_data["namespace"],
                    resource_type="pod",
                    resource_name=pod_name,
                    message=f"Pod deleted: {pod_name}",
                    severity="warning",
                    metadata=pod_data
                ))
        
        # Status changes
        for pod_name, current_pod in current_pods.items():
            if pod_name in previous_pods:
                previous_pod = previous_pods[pod_name]
                
                # Status change
                if current_pod["status"] != previous_pod["status"]:
                    severity = "error" if current_pod["status"] in ["Failed", "CrashLoopBackOff"] else "info"
                    events.append(MonitoringEvent(
                        event_id=f"pod-status-{pod_name}-{datetime.utcnow().isoformat()}",
                        event_type="pod_status_changed",
                        timestamp=datetime.utcnow(),
                        namespace=current_pod["namespace"],
                        resource_type="pod",
                        resource_name=pod_name,
                        message=f"Pod status changed: {previous_pod['status']} → {current_pod['status']}",
                        severity=severity,
                        metadata={"previous": previous_pod, "current": current_pod}
                    ))
                
                # Restart count increase
                if current_pod["restarts"] > previous_pod["restarts"]:
                    events.append(MonitoringEvent(
                        event_id=f"pod-restart-{pod_name}-{datetime.utcnow().isoformat()}",
                        event_type="pod_restarted",
                        timestamp=datetime.utcnow(),
                        namespace=current_pod["namespace"],
                        resource_type="pod",
                        resource_name=pod_name,
                        message=f"Pod restarted: {current_pod['restarts'] - previous_pod['restarts']} times",
                        severity="warning",
                        metadata={"restart_count": current_pod["restarts"]}
                    ))
        
        return events
    
    async def _detect_service_changes(self, current: Dict, previous: Dict) -> List[MonitoringEvent]:
        """Detect changes in service states."""
        events = []
        current_services = current.get("services", {})
        previous_services = previous.get("services", {})
        
        # New services
        for svc_name, svc_data in current_services.items():
            if svc_name not in previous_services:
                events.append(MonitoringEvent(
                    event_id=f"service-new-{svc_name}-{datetime.utcnow().isoformat()}",
                    event_type="service_created",
                    timestamp=datetime.utcnow(),
                    namespace=svc_data["namespace"],
                    resource_type="service",
                    resource_name=svc_name,
                    message=f"New service created: {svc_name}",
                    severity="info",
                    metadata=svc_data
                ))
        
        # Deleted services
        for svc_name, svc_data in previous_services.items():
            if svc_name not in current_services:
                events.append(MonitoringEvent(
                    event_id=f"service-deleted-{svc_name}-{datetime.utcnow().isoformat()}",
                    event_type="service_deleted",
                    timestamp=datetime.utcnow(),
                    namespace=svc_data["namespace"],
                    resource_type="service",
                    resource_name=svc_name,
                    message=f"Service deleted: {svc_name}",
                    severity="warning",
                    metadata=svc_data
                ))
        
        return events
    
    async def _detect_new_events(self, cluster_data: ClusterData) -> List[MonitoringEvent]:
        """Detect new Kubernetes events that require attention."""
        events = []
        
        try:
            # Process recent Kubernetes events
            for k8s_event in cluster_data.events:
                # Focus on warning and error events from the last few minutes
                if k8s_event.type in ["Warning", "Error"] and k8s_event.last_timestamp:
                    try:
                        # Handle timezone-aware vs timezone-naive datetime comparison
                        current_time = datetime.utcnow()
                        event_time = k8s_event.last_timestamp
                        
                        # If event_time is timezone-aware, make current_time timezone-aware too
                        if event_time.tzinfo is not None:
                            from datetime import timezone
                            current_time = current_time.replace(tzinfo=timezone.utc)
                        # If event_time is timezone-naive but current_time is timezone-aware, remove timezone
                        elif current_time.tzinfo is not None:
                            current_time = current_time.replace(tzinfo=None)
                        
                        # Check if event is recent (last 5 minutes)
                        if (current_time - event_time).total_seconds() < 300:
                            severity = "error" if k8s_event.type == "Error" else "warning"
                            
                            # Safely get object name - check for different possible attributes
                            object_name = "unknown"
                            if hasattr(k8s_event, 'involved_object_name') and k8s_event.involved_object_name:
                                object_name = k8s_event.involved_object_name
                            elif hasattr(k8s_event, 'object_name') and k8s_event.object_name:
                                object_name = k8s_event.object_name
                            elif hasattr(k8s_event, 'name') and k8s_event.name:
                                object_name = k8s_event.name
                            
                            events.append(MonitoringEvent(
                                event_id=f"k8s-event-{getattr(k8s_event, 'name', 'unknown')}-{datetime.utcnow().isoformat()}",
                                event_type="kubernetes_event",
                                timestamp=event_time,
                                namespace=getattr(k8s_event, 'namespace', None),
                                resource_type=getattr(k8s_event, 'involved_object_kind', 'unknown').lower() if getattr(k8s_event, 'involved_object_kind', None) else "unknown",
                                resource_name=object_name,
                                message=getattr(k8s_event, 'message', 'No message available'),
                                severity=severity,
                                metadata={
                                    "reason": getattr(k8s_event, 'reason', 'Unknown'),
                                    "count": getattr(k8s_event, 'count', 1),
                                    "source": getattr(k8s_event, 'source_component', 'Unknown')
                                }
                            ))
                    except Exception as e:
                        logger.debug(f"Error processing event {getattr(k8s_event, 'name', 'unknown')}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error in _detect_new_events: {e}")
        
        return events
    
    async def _create_cluster_snapshot(self, cluster_data: ClusterData) -> None:
        """Create a cluster snapshot for predictive analytics."""
        try:
            # Create a simplified snapshot object for predictive analysis
            snapshot = type('ClusterSnapshot', (), {
                'timestamp': datetime.utcnow(),
                'pod_count': len(cluster_data.pods),
                'service_count': len(cluster_data.services),
                'event_count': len(cluster_data.events),
                'health_score': self._calculate_health_score(cluster_data),
                'issues': self._extract_issues(cluster_data),
                'metadata': {
                    'namespaces': len(set(pod.namespace for pod in cluster_data.pods if pod.namespace)),
                    'nodes': len(set(pod.node_name for pod in cluster_data.pods if pod.node_name)),
                    'running_pods': len([pod for pod in cluster_data.pods if pod.status == 'Running']),
                    'failed_pods': len([pod for pod in cluster_data.pods if pod.status in ['Failed', 'Error']])
                }
            })()
            
            # Add to snapshots list
            self.cluster_snapshots.append(snapshot)
            
            # Keep only last 100 snapshots (about 50 minutes of history at 30s intervals)
            if len(self.cluster_snapshots) > 100:
                self.cluster_snapshots = self.cluster_snapshots[-100:]
                
        except Exception as e:
            logger.error(f"Failed to create cluster snapshot: {e}")
    
    def _calculate_health_score(self, cluster_data: ClusterData) -> float:
        """Calculate a simple health score for the cluster."""
        try:
            if not cluster_data.pods:
                return 1.0
            
            total_pods = len(cluster_data.pods)
            running_pods = len([pod for pod in cluster_data.pods if pod.status == 'Running'])
            failed_pods = len([pod for pod in cluster_data.pods if pod.status in ['Failed', 'Error']])
            pending_pods = len([pod for pod in cluster_data.pods if pod.status == 'Pending'])
            
            # Base score from running pods
            running_score = running_pods / total_pods if total_pods > 0 else 1.0
            
            # Penalty for failed pods
            failure_penalty = (failed_pods / total_pods) * 0.5 if total_pods > 0 else 0.0
            
            # Minor penalty for pending pods
            pending_penalty = (pending_pods / total_pods) * 0.1 if total_pods > 0 else 0.0
            
            # Event-based penalty
            error_events = len([event for event in cluster_data.events if event.type == 'Error'])
            warning_events = len([event for event in cluster_data.events if event.type == 'Warning'])
            event_penalty = min(0.2, (error_events * 0.05) + (warning_events * 0.02))
            
            health_score = max(0.0, running_score - failure_penalty - pending_penalty - event_penalty)
            return min(1.0, health_score)
            
        except Exception as e:
            logger.error(f"Health score calculation failed: {e}")
            return 0.5  # Default to neutral score
    
    def _extract_issues(self, cluster_data: ClusterData) -> List[Dict[str, Any]]:
        """Extract issues from cluster data for predictive analysis."""
        issues = []
        
        try:
            # Pod-related issues
            for pod in cluster_data.pods:
                if pod.status in ['Failed', 'Error']:
                    issues.append({
                        'type': 'pod_failure',
                        'resource': f"{pod.namespace}/{pod.name}",
                        'status': pod.status,
                        'restart_count': pod.restart_count or 0
                    })
                elif pod.restart_count and pod.restart_count > 5:
                    issues.append({
                        'type': 'high_restarts',
                        'resource': f"{pod.namespace}/{pod.name}",
                        'restart_count': pod.restart_count
                    })
            
            # Event-based issues
            for event in cluster_data.events:
                try:
                    if event.type in ['Error', 'Warning'] and getattr(event, 'count', 0) and getattr(event, 'count', 0) > 3:
                        # Safely get object name - check for different possible attributes
                        object_name = "unknown"
                        if hasattr(event, 'involved_object_name') and event.involved_object_name:
                            object_name = event.involved_object_name
                        elif hasattr(event, 'object_name') and event.object_name:
                            object_name = event.object_name
                        elif hasattr(event, 'name') and event.name:
                            object_name = event.name
                        
                        namespace = getattr(event, 'namespace', None)
                        resource_identifier = f"{namespace}/{object_name}" if namespace else object_name
                        
                        issues.append({
                            'type': 'recurring_event',
                            'event_type': event.type,
                            'reason': getattr(event, 'reason', 'Unknown'),
                            'count': getattr(event, 'count', 1),
                            'resource': resource_identifier
                        })
                except Exception as e:
                    logger.debug(f"Error processing event for issues: {e}")
                    continue
            
            return issues
            
        except Exception as e:
            logger.error(f"Issue extraction failed: {e}")
            return []
    
    def _add_predictions_to_prompt(self, predictions) -> str:
        """Add predictive insights to the analysis prompt."""
        if not predictions:
            return ""
        
        prompt_addition = "\n\n## PREDICTIVE INSIGHTS\n"
        prompt_addition += "The following predictions have been generated based on historical cluster data:\n\n"
        
        for prediction in predictions:
            prompt_addition += f"**{prediction.prediction_type.upper()}** (Confidence: {prediction.confidence:.1%})\n"
            prompt_addition += f"- {prediction.description}\n"
            prompt_addition += f"- Severity: {prediction.severity}\n"
            prompt_addition += f"- Time Frame: {prediction.time_frame}\n"
            prompt_addition += f"- Recommended Actions: {', '.join(prediction.recommended_actions[:2])}\n\n"
        
        prompt_addition += "Please incorporate these predictions into your analysis and provide guidance on preventive measures.\n"
        return prompt_addition
    
    def get_prediction_summary(self) -> Dict[str, Any]:
        """Get summary of current predictions."""
        return self.predictive_analyzer.get_prediction_summary()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current event loop status."""
        status = {
            "running": self.is_running,
            "last_analysis": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "queue_size": self.event_queue.qsize(),
            "subscribers": len(self.subscribers),
            "metrics": self.metrics.copy(),
            "monitoring_interval": self.monitoring_interval,
            "streaming_enabled": self.enable_streaming,
            "snapshots_stored": len(self.cluster_snapshots)
        }
        
        # Add prediction summary if available
        prediction_summary = self.get_prediction_summary()
        if prediction_summary.get('status') != 'no_predictions':
            status['predictions'] = prediction_summary
            
        return status
