"""
Continuous Monitoring System for AWS Strands Kubernetes Agent

Implements 24/7 automated cluster watching with event-driven triggers and background processing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
import json
import hashlib
from collections import defaultdict, deque

from ..k8s.client import KubernetesClient
from ..k8s.collector import DataCollector
from ..models.kubernetes import ClusterData
from .trend_analyzer import TrendAnalyzer
from .predictive_analytics import PredictiveAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class ClusterSnapshot:
    """Represents a point-in-time cluster state snapshot."""
    timestamp: datetime
    cluster_hash: str
    pod_count: int
    service_count: int
    event_count: int
    resource_usage: Dict[str, float]
    health_score: float
    issues: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class ChangeEvent:
    """Represents a detected change in cluster state."""
    event_id: str
    timestamp: datetime
    change_type: str  # 'pod_created', 'pod_deleted', 'service_modified', etc.
    resource_type: str
    resource_name: str
    namespace: str
    old_state: Optional[Dict[str, Any]]
    new_state: Dict[str, Any]
    severity: str  # 'low', 'medium', 'high', 'critical'
    requires_analysis: bool

class ContinuousMonitor:
    """
    24/7 Continuous Kubernetes Cluster Monitoring System
    
    Features:
    - Real-time cluster state tracking
    - Event-driven change detection
    - Background processing
    - Trend analysis
    - Predictive analytics
    - Intelligent alerting
    """
    
    def __init__(
        self,
        strands_agent,
        k8s_client: KubernetesClient,
        data_collector: DataCollector,
        monitoring_interval: int = 30,
        trend_window_hours: int = 24,
        enable_predictive: bool = True
    ):
        """Initialize the continuous monitoring system."""
        self.strands_agent = strands_agent
        self.k8s_client = k8s_client
        self.data_collector = data_collector
        self.monitoring_interval = monitoring_interval
        self.trend_window_hours = trend_window_hours
        self.enable_predictive = enable_predictive
        
        # State management
        self.is_running = False
        self.current_snapshot: Optional[ClusterSnapshot] = None
        self.previous_snapshot: Optional[ClusterSnapshot] = None
        
        # Historical data storage
        self.snapshots_history: deque = deque(maxlen=2880)  # 24 hours at 30s intervals
        self.change_events: deque = deque(maxlen=10000)  # Last 10k events
        self.analysis_cache: Dict[str, Any] = {}
        
        # Monitoring components
        self.trend_analyzer = TrendAnalyzer(trend_window_hours)
        self.predictive_analyzer = PredictiveAnalyzer() if enable_predictive else None
        
        # Event subscribers
        self.event_subscribers: List[callable] = []
        self.analysis_subscribers: List[callable] = []
        
        # Performance tracking
        self.metrics = {
            "monitoring_cycles": 0,
            "changes_detected": 0,
            "analyses_triggered": 0,
            "predictions_made": 0,
            "average_cycle_time": 0.0,
            "last_cycle_time": 0.0
        }
        
        logger.info("Continuous Monitor initialized")
    
    async def start_monitoring(self):
        """Start the continuous monitoring system."""
        if self.is_running:
            logger.warning("Continuous monitoring is already running")
            return
        
        self.is_running = True
        logger.info("🔄 Starting 24/7 continuous cluster monitoring")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._monitoring_loop(), name="monitoring_loop"),
            asyncio.create_task(self._change_detection_loop(), name="change_detection"),
            asyncio.create_task(self._trend_analysis_loop(), name="trend_analysis"),
            asyncio.create_task(self._cleanup_loop(), name="cleanup"),
        ]
        
        if self.enable_predictive:
            tasks.append(
                asyncio.create_task(self._predictive_analysis_loop(), name="predictive_analysis")
            )
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Continuous monitoring error: {e}")
            await self.stop_monitoring()
            raise
    
    async def stop_monitoring(self):
        """Stop the continuous monitoring system."""
        logger.info("🛑 Stopping continuous cluster monitoring")
        self.is_running = False
        
        # Cancel all running tasks
        for task in asyncio.all_tasks():
            if not task.done() and task.get_name() in [
                "monitoring_loop", "change_detection", "trend_analysis", 
                "cleanup", "predictive_analysis"
            ]:
                task.cancel()
        
        logger.info("Continuous monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop - captures cluster snapshots."""
        logger.info("📊 Starting monitoring loop")
        
        while self.is_running:
            try:
                cycle_start = datetime.utcnow()
                
                # Capture current cluster state
                snapshot = await self._capture_cluster_snapshot()
                
                # Update current state
                self.previous_snapshot = self.current_snapshot
                self.current_snapshot = snapshot
                
                # Store in history
                self.snapshots_history.append(snapshot)
                
                # Update metrics
                cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
                self.metrics["monitoring_cycles"] += 1
                self.metrics["last_cycle_time"] = cycle_time
                self.metrics["average_cycle_time"] = (
                    (self.metrics["average_cycle_time"] * (self.metrics["monitoring_cycles"] - 1) + cycle_time)
                    / self.metrics["monitoring_cycles"]
                )
                
                logger.debug(f"Monitoring cycle completed in {cycle_time:.2f}s")
                
                # Wait for next cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _change_detection_loop(self):
        """Detect and process cluster changes."""
        logger.info("🔍 Starting change detection loop")
        
        while self.is_running:
            try:
                if self.current_snapshot and self.previous_snapshot:
                    # Detect changes between snapshots
                    changes = await self._detect_changes(
                        self.previous_snapshot, 
                        self.current_snapshot
                    )
                    
                    # Process detected changes
                    for change in changes:
                        await self._process_change_event(change)
                
                await asyncio.sleep(5)  # Check for changes every 5 seconds
                
            except Exception as e:
                logger.error(f"Change detection error: {e}")
                await asyncio.sleep(10)
    
    async def _trend_analysis_loop(self):
        """Perform trend analysis on historical data."""
        logger.info("📈 Starting trend analysis loop")
        
        while self.is_running:
            try:
                if len(self.snapshots_history) >= 10:  # Need minimum data
                    # Perform trend analysis
                    trends = await self.trend_analyzer.analyze_trends(
                        list(self.snapshots_history)
                    )
                    
                    # Check for concerning trends
                    await self._process_trend_analysis(trends)
                
                # Run trend analysis every 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Trend analysis error: {e}")
                await asyncio.sleep(60)
    
    async def _predictive_analysis_loop(self):
        """Perform predictive analytics."""
        if not self.predictive_analyzer:
            return
        
        logger.info("🔮 Starting predictive analysis loop")
        
        while self.is_running:
            try:
                if len(self.snapshots_history) >= 60:  # Need sufficient history
                    # Generate predictions
                    predictions = await self.predictive_analyzer.generate_predictions(
                        list(self.snapshots_history)
                    )
                    
                    # Process predictions
                    await self._process_predictions(predictions)
                    self.metrics["predictions_made"] += len(predictions)
                
                # Run predictive analysis every 15 minutes
                await asyncio.sleep(900)
                
            except Exception as e:
                logger.error(f"Predictive analysis error: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_loop(self):
        """Clean up old data and maintain system health."""
        logger.info("🧹 Starting cleanup loop")
        
        while self.is_running:
            try:
                # Clean up old cache entries
                current_time = datetime.utcnow()
                cache_keys_to_remove = []
                
                for key, value in self.analysis_cache.items():
                    if isinstance(value, dict) and 'timestamp' in value:
                        cache_time = datetime.fromisoformat(value['timestamp'])
                        if (current_time - cache_time).total_seconds() > 3600:  # 1 hour
                            cache_keys_to_remove.append(key)
                
                for key in cache_keys_to_remove:
                    del self.analysis_cache[key]
                
                logger.debug(f"Cleaned up {len(cache_keys_to_remove)} cache entries")
                
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(1800)  # Retry in 30 minutes
    
    async def _capture_cluster_snapshot(self) -> ClusterSnapshot:
        """Capture a comprehensive cluster state snapshot."""
        try:
            # Collect cluster data
            cluster_data = await self.data_collector.collect_cluster_data(
                include_logs=False  # Don't include logs for performance
            )
            
            # Calculate cluster hash for change detection
            cluster_state = {
                'pods': [(p.name, p.namespace, p.status, p.ready) for p in cluster_data.pods],
                'services': [(s.name, s.namespace, s.type) for s in cluster_data.services],
                'events': [(e.reason, e.message, e.count) for e in cluster_data.events[-50:]]  # Last 50 events
            }
            cluster_hash = hashlib.md5(json.dumps(cluster_state, sort_keys=True).encode()).hexdigest()
            
            # Calculate health score
            health_score = await self._calculate_health_score(cluster_data)
            
            # Identify current issues
            issues = await self._identify_issues(cluster_data)
            
            # Calculate resource usage
            resource_usage = await self._calculate_resource_usage(cluster_data)
            
            snapshot = ClusterSnapshot(
                timestamp=datetime.utcnow(),
                cluster_hash=cluster_hash,
                pod_count=len(cluster_data.pods),
                service_count=len(cluster_data.services),
                event_count=len(cluster_data.events),
                resource_usage=resource_usage,
                health_score=health_score,
                issues=issues,
                metadata={
                    'namespaces': len(set(p.namespace for p in cluster_data.pods if p.namespace)),
                    'running_pods': len([p for p in cluster_data.pods if p.status == 'Running']),
                    'failed_pods': len([p for p in cluster_data.pods if p.status in ['Failed', 'CrashLoopBackOff']])
                }
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to capture cluster snapshot: {e}")
            # Return minimal snapshot
            return ClusterSnapshot(
                timestamp=datetime.utcnow(),
                cluster_hash="error",
                pod_count=0,
                service_count=0,
                event_count=0,
                resource_usage={},
                health_score=0.0,
                issues=[{"type": "monitoring_error", "message": str(e)}],
                metadata={}
            )
    
    async def _detect_changes(self, previous: ClusterSnapshot, current: ClusterSnapshot) -> List[ChangeEvent]:
        """Detect changes between two cluster snapshots."""
        changes = []
        
        try:
            # Hash-based change detection
            if previous.cluster_hash != current.cluster_hash:
                # Detailed change analysis
                
                # Pod count changes
                if previous.pod_count != current.pod_count:
                    change_type = "pods_scaled_up" if current.pod_count > previous.pod_count else "pods_scaled_down"
                    severity = "medium" if abs(current.pod_count - previous.pod_count) > 5 else "low"
                    
                    changes.append(ChangeEvent(
                        event_id=f"pod_count_change_{datetime.utcnow().isoformat()}",
                        timestamp=datetime.utcnow(),
                        change_type=change_type,
                        resource_type="pods",
                        resource_name="cluster",
                        namespace="all",
                        old_state={"count": previous.pod_count},
                        new_state={"count": current.pod_count},
                        severity=severity,
                        requires_analysis=severity in ["medium", "high", "critical"]
                    ))
                
                # Health score changes
                health_diff = abs(current.health_score - previous.health_score)
                if health_diff > 0.1:  # Significant health change
                    severity = "critical" if health_diff > 0.5 else "high" if health_diff > 0.3 else "medium"
                    
                    changes.append(ChangeEvent(
                        event_id=f"health_change_{datetime.utcnow().isoformat()}",
                        timestamp=datetime.utcnow(),
                        change_type="health_score_changed",
                        resource_type="cluster",
                        resource_name="health",
                        namespace="all",
                        old_state={"health_score": previous.health_score},
                        new_state={"health_score": current.health_score},
                        severity=severity,
                        requires_analysis=True
                    ))
                
                # New issues detected
                current_issue_types = {issue.get('type') for issue in current.issues}
                previous_issue_types = {issue.get('type') for issue in previous.issues}
                new_issues = current_issue_types - previous_issue_types
                
                for issue_type in new_issues:
                    changes.append(ChangeEvent(
                        event_id=f"new_issue_{issue_type}_{datetime.utcnow().isoformat()}",
                        timestamp=datetime.utcnow(),
                        change_type="new_issue_detected",
                        resource_type="issue",
                        resource_name=issue_type,
                        namespace="all",
                        old_state=None,
                        new_state={"issue_type": issue_type},
                        severity="high",
                        requires_analysis=True
                    ))
            
            return changes
            
        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            return []
    
    async def _process_change_event(self, change: ChangeEvent):
        """Process a detected change event."""
        try:
            # Store the change event
            self.change_events.append(change)
            self.metrics["changes_detected"] += 1
            
            logger.info(f"🔄 Change detected: {change.change_type} - {change.resource_name} ({change.severity})")
            
            # Notify subscribers
            for subscriber in self.event_subscribers:
                try:
                    await subscriber(change)
                except Exception as e:
                    logger.error(f"Event subscriber error: {e}")
            
            # Trigger analysis if required
            if change.requires_analysis:
                await self._trigger_analysis(change)
            
        except Exception as e:
            logger.error(f"Failed to process change event: {e}")
    
    async def _trigger_analysis(self, change: ChangeEvent):
        """Trigger AI analysis for significant changes."""
        try:
            # Check if we've already analyzed this recently
            cache_key = f"{change.change_type}_{change.resource_name}_{change.namespace}"
            if cache_key in self.analysis_cache:
                last_analysis = datetime.fromisoformat(self.analysis_cache[cache_key]['timestamp'])
                if (datetime.utcnow() - last_analysis).total_seconds() < 300:  # 5 minutes
                    logger.debug(f"Skipping analysis - recent analysis exists for {cache_key}")
                    return
            
            # Create analysis prompt
            prompt = self._create_change_analysis_prompt(change)
            
            # Trigger Strands analysis
            logger.info(f"🤖 Triggering AI analysis for: {change.change_type}")
            analysis_result = await self.strands_agent.invoke_async(prompt)
            
            # Cache the analysis
            self.analysis_cache[cache_key] = {
                'timestamp': datetime.utcnow().isoformat(),
                'change_event': asdict(change),
                'analysis': analysis_result
            }
            
            # Notify analysis subscribers
            for subscriber in self.analysis_subscribers:
                try:
                    await subscriber(change, analysis_result)
                except Exception as e:
                    logger.error(f"Analysis subscriber error: {e}")
            
            self.metrics["analyses_triggered"] += 1
            
        except Exception as e:
            logger.error(f"Failed to trigger analysis: {e}")
    
    def _create_change_analysis_prompt(self, change: ChangeEvent) -> str:
        """Create an analysis prompt for a change event."""
        prompt_parts = [
            f"🔄 CLUSTER CHANGE DETECTED - IMMEDIATE ANALYSIS REQUIRED",
            f"",
            f"Change Type: {change.change_type}",
            f"Resource: {change.resource_type}/{change.resource_name}",
            f"Namespace: {change.namespace}",
            f"Severity: {change.severity}",
            f"Timestamp: {change.timestamp}",
            f"",
            f"Previous State: {json.dumps(change.old_state, indent=2) if change.old_state else 'N/A'}",
            f"Current State: {json.dumps(change.new_state, indent=2)}",
            f"",
            f"Please provide:",
            f"1. Impact assessment of this change",
            f"2. Potential root causes",
            f"3. Immediate actions required (if any)",
            f"4. Monitoring recommendations",
            f"5. Risk level assessment",
            f"",
            f"Focus on actionable insights and immediate concerns."
        ]
        
        return "\n".join(prompt_parts)
    
    async def _calculate_health_score(self, cluster_data: ClusterData) -> float:
        """Calculate overall cluster health score (0.0 to 1.0)."""
        try:
            if not cluster_data.pods:
                return 0.0
            
            # Pod health metrics
            running_pods = len([p for p in cluster_data.pods if p.status == 'Running' and p.ready])
            total_pods = len(cluster_data.pods)
            pod_health = running_pods / total_pods if total_pods > 0 else 0.0
            
            # Event severity metrics
            warning_events = len([e for e in cluster_data.events if e.type == 'Warning'])
            error_events = len([e for e in cluster_data.events if e.type == 'Error'])
            total_events = len(cluster_data.events)
            
            event_health = 1.0
            if total_events > 0:
                event_health = max(0.0, 1.0 - (warning_events * 0.1 + error_events * 0.3) / total_events)
            
            # Restart frequency
            high_restart_pods = len([p for p in cluster_data.pods if p.restart_count > 5])
            restart_health = max(0.0, 1.0 - (high_restart_pods / total_pods) if total_pods > 0 else 1.0)
            
            # Weighted health score
            health_score = (pod_health * 0.5 + event_health * 0.3 + restart_health * 0.2)
            
            return round(health_score, 3)
            
        except Exception as e:
            logger.error(f"Health score calculation failed: {e}")
            return 0.5  # Neutral score on error
    
    async def _identify_issues(self, cluster_data: ClusterData) -> List[Dict[str, Any]]:
        """Identify current cluster issues."""
        issues = []
        
        try:
            # Failed pods
            failed_pods = [p for p in cluster_data.pods if p.status in ['Failed', 'CrashLoopBackOff', 'Error']]
            for pod in failed_pods:
                issues.append({
                    'type': 'pod_failure',
                    'severity': 'high',
                    'resource': f"{pod.namespace}/{pod.name}",
                    'message': f"Pod {pod.name} is in {pod.status} state",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # High restart count pods
            high_restart_pods = [p for p in cluster_data.pods if p.restart_count > 10]
            for pod in high_restart_pods:
                issues.append({
                    'type': 'high_restarts',
                    'severity': 'medium',
                    'resource': f"{pod.namespace}/{pod.name}",
                    'message': f"Pod {pod.name} has {pod.restart_count} restarts",
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            # Recent error events
            recent_errors = [e for e in cluster_data.events 
                           if e.type == 'Error' and e.last_timestamp 
                           and (datetime.utcnow() - e.last_timestamp).total_seconds() < 300]
            
            for event in recent_errors:
                issues.append({
                    'type': 'recent_error',
                    'severity': 'high',
                    'resource': f"{event.namespace}/{event.involved_object_name}",
                    'message': event.message,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            return issues
            
        except Exception as e:
            logger.error(f"Issue identification failed: {e}")
            return [{'type': 'monitoring_error', 'message': str(e)}]
    
    async def _calculate_resource_usage(self, cluster_data: ClusterData) -> Dict[str, float]:
        """Calculate cluster resource usage metrics."""
        try:
            # Basic resource calculations
            total_pods = len(cluster_data.pods)
            running_pods = len([p for p in cluster_data.pods if p.status == 'Running'])
            
            return {
                'pod_utilization': running_pods / total_pods if total_pods > 0 else 0.0,
                'service_count': len(cluster_data.services),
                'namespace_count': len(set(p.namespace for p in cluster_data.pods if p.namespace)),
                'event_rate': len([e for e in cluster_data.events 
                                 if e.last_timestamp and 
                                 (datetime.utcnow() - e.last_timestamp).total_seconds() < 3600])
            }
            
        except Exception as e:
            logger.error(f"Resource usage calculation failed: {e}")
            return {}
    
    async def _process_trend_analysis(self, trends: Dict[str, Any]):
        """Process trend analysis results."""
        try:
            # Check for concerning trends
            concerning_trends = []
            
            for metric, trend_data in trends.items():
                if trend_data.get('direction') == 'increasing' and trend_data.get('rate', 0) > 0.1:
                    if metric in ['failed_pods', 'error_events', 'restart_rate']:
                        concerning_trends.append({
                            'metric': metric,
                            'trend': trend_data,
                            'severity': 'high'
                        })
                elif trend_data.get('direction') == 'decreasing' and trend_data.get('rate', 0) < -0.1:
                    if metric in ['health_score', 'running_pods']:
                        concerning_trends.append({
                            'metric': metric,
                            'trend': trend_data,
                            'severity': 'medium'
                        })
            
            # Trigger analysis for concerning trends
            for trend in concerning_trends:
                await self._trigger_trend_analysis(trend)
                
        except Exception as e:
            logger.error(f"Trend analysis processing failed: {e}")
    
    async def _trigger_trend_analysis(self, trend: Dict[str, Any]):
        """Trigger analysis for concerning trends."""
        try:
            prompt = f"""
            📈 TREND ANALYSIS ALERT
            
            Metric: {trend['metric']}
            Trend Direction: {trend['trend'].get('direction')}
            Rate of Change: {trend['trend'].get('rate', 0):.3f}
            Severity: {trend['severity']}
            
            This trend has been detected over the monitoring period.
            Please analyze:
            1. What might be causing this trend?
            2. What are the potential impacts?
            3. What preventive actions should be taken?
            4. Should we increase monitoring frequency for related metrics?
            """
            
            analysis_result = await self.strands_agent.invoke_async(prompt)
            logger.info(f"📈 Trend analysis completed for {trend['metric']}")
            
        except Exception as e:
            logger.error(f"Trend analysis trigger failed: {e}")
    
    async def _process_predictions(self, predictions: List[Dict[str, Any]]):
        """Process predictive analysis results."""
        try:
            for prediction in predictions:
                if prediction.get('confidence', 0) > 0.7 and prediction.get('severity') in ['high', 'critical']:
                    await self._trigger_predictive_analysis(prediction)
                    
        except Exception as e:
            logger.error(f"Prediction processing failed: {e}")
    
    async def _trigger_predictive_analysis(self, prediction: Dict[str, Any]):
        """Trigger analysis for high-confidence predictions."""
        try:
            prompt = f"""
            🔮 PREDICTIVE ANALYSIS ALERT
            
            Prediction: {prediction.get('prediction_type')}
            Confidence: {prediction.get('confidence', 0):.2f}
            Severity: {prediction.get('severity')}
            Time Frame: {prediction.get('time_frame')}
            
            Predicted Issue: {prediction.get('description')}
            
            Please provide:
            1. Preventive actions to avoid this predicted issue
            2. Monitoring adjustments needed
            3. Resource planning recommendations
            4. Risk mitigation strategies
            """
            
            analysis_result = await self.strands_agent.invoke_async(prompt)
            logger.info(f"🔮 Predictive analysis completed for {prediction.get('prediction_type')}")
            
        except Exception as e:
            logger.error(f"Predictive analysis trigger failed: {e}")
    
    def subscribe_to_events(self, callback: callable):
        """Subscribe to change events."""
        self.event_subscribers.append(callback)
    
    def subscribe_to_analysis(self, callback: callable):
        """Subscribe to analysis results."""
        self.analysis_subscribers.append(callback)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            'is_running': self.is_running,
            'current_snapshot': asdict(self.current_snapshot) if self.current_snapshot else None,
            'snapshots_count': len(self.snapshots_history),
            'changes_count': len(self.change_events),
            'metrics': self.metrics.copy(),
            'cache_size': len(self.analysis_cache)
        }
    
    def get_recent_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent change events."""
        recent_changes = list(self.change_events)[-limit:]
        return [asdict(change) for change in recent_changes]
    
    def get_health_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health score trend over time."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_snapshots = [
            s for s in self.snapshots_history 
            if s.timestamp >= cutoff_time
        ]
        
        return [
            {
                'timestamp': s.timestamp.isoformat(),
                'health_score': s.health_score,
                'pod_count': s.pod_count,
                'issues_count': len(s.issues)
            }
            for s in recent_snapshots
        ]
