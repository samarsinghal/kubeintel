"""
Predictive Analytics System for Kubernetes Monitoring

Provides forecasting and predictive issue detection capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import statistics
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

@dataclass
class Prediction:
    """Represents a predictive analysis result."""
    prediction_id: str
    prediction_type: str
    description: str
    confidence: float  # 0.0 to 1.0
    severity: str  # 'low', 'medium', 'high', 'critical'
    time_frame: str  # When the prediction might occur
    probability: float  # Probability of occurrence
    impact_assessment: str
    recommended_actions: List[str]
    based_on_metrics: List[str]
    created_at: datetime

class PredictiveAnalyzer:
    """
    Advanced predictive analytics system for Kubernetes clusters.
    
    Features:
    - Resource exhaustion prediction
    - Failure pattern recognition
    - Capacity planning forecasts
    - Performance degradation prediction
    - Anomaly-based issue forecasting
    """
    
    def __init__(self):
        """Initialize the predictive analyzer."""
        self.prediction_history: List[Prediction] = []
        self.pattern_cache: Dict[str, Any] = {}
        self.thresholds = {
            'pod_failure_rate': 0.1,  # 10% failure rate threshold
            'restart_rate_increase': 2.0,  # 2x increase in restart rate
            'health_score_decline': 0.2,  # 20% decline in health score
            'resource_growth_rate': 0.3,  # 30% growth rate
            'event_spike_threshold': 3.0  # 3x normal event rate
        }
        
        logger.info("Predictive Analyzer initialized")
    
    async def generate_predictions(self, snapshots: List[Any]) -> List[Prediction]:
        """Generate predictions based on historical cluster data."""
        try:
            if len(snapshots) < 10:  # Need sufficient history
                logger.debug("Insufficient data for predictions")
                return []
            
            predictions = []
            
            # Sort snapshots by timestamp
            snapshots.sort(key=lambda x: x.timestamp)
            
            # Generate different types of predictions
            predictions.extend(await self._predict_resource_exhaustion(snapshots))
            predictions.extend(await self._predict_pod_failures(snapshots))
            predictions.extend(await self._predict_performance_degradation(snapshots))
            predictions.extend(await self._predict_capacity_issues(snapshots))
            predictions.extend(await self._predict_anomaly_based_issues(snapshots))
            
            # Filter high-confidence predictions
            high_confidence_predictions = [
                p for p in predictions 
                if p.confidence > 0.6
            ]
            
            # Store predictions
            self.prediction_history.extend(high_confidence_predictions)
            
            # Keep only recent predictions (last 7 days)
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            self.prediction_history = [
                p for p in self.prediction_history 
                if p.created_at >= cutoff_time
            ]
            
            logger.info(f"Generated {len(high_confidence_predictions)} high-confidence predictions")
            return high_confidence_predictions
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {e}")
            return []
    
    async def _predict_resource_exhaustion(self, snapshots: List[Any]) -> List[Prediction]:
        """Predict potential resource exhaustion scenarios."""
        predictions = []
        
        try:
            # Analyze pod count growth
            pod_counts = [(s.timestamp, s.pod_count) for s in snapshots]
            pod_growth_rate = self._calculate_growth_rate(pod_counts)
            
            if pod_growth_rate > self.thresholds['resource_growth_rate']:
                # Predict when pod limit might be reached
                current_pods = snapshots[-1].pod_count
                estimated_limit = 250  # Typical cluster pod limit
                
                if pod_growth_rate > 0:
                    hours_to_limit = (estimated_limit - current_pods) / (pod_growth_rate * current_pods)
                    
                    if 0 < hours_to_limit < 168:  # Within a week
                        confidence = min(0.9, pod_growth_rate * 2)
                        time_frame = self._format_time_frame(hours_to_limit)
                        
                        predictions.append(Prediction(
                            prediction_id=f"resource_exhaustion_{datetime.utcnow().isoformat()}",
                            prediction_type="resource_exhaustion",
                            description=f"Pod limit may be reached in {time_frame} based on current growth rate",
                            confidence=confidence,
                            severity="high" if hours_to_limit < 24 else "medium",
                            time_frame=time_frame,
                            probability=confidence,
                            impact_assessment="New pod deployments will fail, affecting application scaling",
                            recommended_actions=[
                                "Review pod resource requests and limits",
                                "Consider cluster scaling or additional nodes",
                                "Implement pod disruption budgets",
                                "Monitor resource usage trends closely"
                            ],
                            based_on_metrics=["pod_count", "growth_rate"],
                            created_at=datetime.utcnow()
                        ))
            
            # Analyze namespace resource usage
            namespace_growth = self._analyze_namespace_growth(snapshots)
            for namespace, growth_data in namespace_growth.items():
                if growth_data['rate'] > self.thresholds['resource_growth_rate']:
                    predictions.append(Prediction(
                        prediction_id=f"namespace_exhaustion_{namespace}_{datetime.utcnow().isoformat()}",
                        prediction_type="namespace_resource_exhaustion",
                        description=f"Namespace '{namespace}' showing rapid resource growth",
                        confidence=growth_data['confidence'],
                        severity="medium",
                        time_frame="1-3 days",
                        probability=growth_data['confidence'],
                        impact_assessment=f"Namespace {namespace} may consume excessive cluster resources",
                        recommended_actions=[
                            f"Review resource quotas for namespace {namespace}",
                            "Implement resource limits",
                            "Monitor application scaling patterns"
                        ],
                        based_on_metrics=["namespace_pod_count", "resource_usage"],
                        created_at=datetime.utcnow()
                    ))
            
            return predictions
            
        except Exception as e:
            logger.error(f"Resource exhaustion prediction failed: {e}")
            return []
    
    async def _predict_pod_failures(self, snapshots: List[Any]) -> List[Prediction]:
        """Predict potential pod failure scenarios."""
        predictions = []
        
        try:
            # Analyze restart patterns
            restart_data = []
            failure_data = []
            
            for snapshot in snapshots:
                total_restarts = sum(
                    issue.get('restart_count', 0) 
                    for issue in snapshot.issues 
                    if issue.get('type') == 'high_restarts'
                )
                restart_data.append((snapshot.timestamp, total_restarts))
                
                failed_pods = len([
                    issue for issue in snapshot.issues 
                    if issue.get('type') == 'pod_failure'
                ])
                failure_data.append((snapshot.timestamp, failed_pods))
            
            # Analyze restart rate increase
            restart_rate = self._calculate_growth_rate(restart_data)
            if restart_rate > self.thresholds['restart_rate_increase']:
                confidence = min(0.8, restart_rate / 3.0)
                
                predictions.append(Prediction(
                    prediction_id=f"pod_failure_pattern_{datetime.utcnow().isoformat()}",
                    prediction_type="pod_failure_increase",
                    description="Increasing pod restart rate indicates potential stability issues",
                    confidence=confidence,
                    severity="high" if restart_rate > 5.0 else "medium",
                    time_frame="6-24 hours",
                    probability=confidence,
                    impact_assessment="Application stability may be compromised, affecting user experience",
                    recommended_actions=[
                        "Investigate pod logs for error patterns",
                        "Review resource limits and requests",
                        "Check for memory leaks or resource contention",
                        "Consider implementing circuit breakers"
                    ],
                    based_on_metrics=["restart_count", "pod_failures"],
                    created_at=datetime.utcnow()
                ))
            
            # Analyze failure patterns
            failure_rate = self._calculate_growth_rate(failure_data)
            if failure_rate > self.thresholds['pod_failure_rate']:
                confidence = min(0.9, failure_rate * 2)
                
                predictions.append(Prediction(
                    prediction_id=f"pod_failure_escalation_{datetime.utcnow().isoformat()}",
                    prediction_type="pod_failure_escalation",
                    description="Pod failure rate is increasing, indicating systemic issues",
                    confidence=confidence,
                    severity="critical" if failure_rate > 0.5 else "high",
                    time_frame="2-12 hours",
                    probability=confidence,
                    impact_assessment="Service availability may be significantly impacted",
                    recommended_actions=[
                        "Immediate investigation of failing pods",
                        "Check cluster node health",
                        "Review recent deployments or changes",
                        "Consider rollback if recent changes detected"
                    ],
                    based_on_metrics=["pod_failures", "failure_rate"],
                    created_at=datetime.utcnow()
                ))
            
            return predictions
            
        except Exception as e:
            logger.error(f"Pod failure prediction failed: {e}")
            return []
    
    async def _predict_performance_degradation(self, snapshots: List[Any]) -> List[Prediction]:
        """Predict performance degradation scenarios."""
        predictions = []
        
        try:
            # Analyze health score trends
            health_scores = [(s.timestamp, s.health_score) for s in snapshots]
            health_trend = self._calculate_trend(health_scores)
            
            if health_trend['direction'] == 'decreasing' and abs(health_trend['rate']) > self.thresholds['health_score_decline']:
                confidence = min(0.8, abs(health_trend['rate']) * 3)
                
                # Predict when health score might reach critical levels
                current_health = snapshots[-1].health_score
                critical_threshold = 0.3
                
                if health_trend['rate'] < 0:
                    hours_to_critical = (current_health - critical_threshold) / abs(health_trend['rate'])
                    
                    if 0 < hours_to_critical < 72:  # Within 3 days
                        time_frame = self._format_time_frame(hours_to_critical)
                        
                        predictions.append(Prediction(
                            prediction_id=f"performance_degradation_{datetime.utcnow().isoformat()}",
                            prediction_type="performance_degradation",
                            description=f"Cluster health declining, may reach critical levels in {time_frame}",
                            confidence=confidence,
                            severity="high" if hours_to_critical < 12 else "medium",
                            time_frame=time_frame,
                            probability=confidence,
                            impact_assessment="Overall cluster performance and reliability will be compromised",
                            recommended_actions=[
                                "Investigate root causes of health score decline",
                                "Review recent changes and deployments",
                                "Check resource utilization patterns",
                                "Consider scaling or optimization measures"
                            ],
                            based_on_metrics=["health_score", "trend_analysis"],
                            created_at=datetime.utcnow()
                        ))
            
            # Analyze event rate increases
            event_counts = [(s.timestamp, s.event_count) for s in snapshots]
            event_rate = self._calculate_growth_rate(event_counts)
            
            if event_rate > self.thresholds['event_spike_threshold']:
                confidence = min(0.7, event_rate / 5.0)
                
                predictions.append(Prediction(
                    prediction_id=f"event_spike_prediction_{datetime.utcnow().isoformat()}",
                    prediction_type="event_spike",
                    description="Kubernetes event rate is spiking, indicating cluster stress",
                    confidence=confidence,
                    severity="medium",
                    time_frame="1-6 hours",
                    probability=confidence,
                    impact_assessment="Increased cluster activity may lead to performance issues",
                    recommended_actions=[
                        "Monitor event types and sources",
                        "Check for resource contention",
                        "Review scheduler performance",
                        "Consider event rate limiting"
                    ],
                    based_on_metrics=["event_count", "event_rate"],
                    created_at=datetime.utcnow()
                ))
            
            return predictions
            
        except Exception as e:
            logger.error(f"Performance degradation prediction failed: {e}")
            return []
    
    async def _predict_capacity_issues(self, snapshots: List[Any]) -> List[Prediction]:
        """Predict capacity-related issues."""
        predictions = []
        
        try:
            # Analyze service growth
            service_counts = [(s.timestamp, s.service_count) for s in snapshots]
            service_growth = self._calculate_growth_rate(service_counts)
            
            if service_growth > 0.2:  # 20% growth rate
                confidence = min(0.7, service_growth * 2)
                
                predictions.append(Prediction(
                    prediction_id=f"capacity_planning_{datetime.utcnow().isoformat()}",
                    prediction_type="capacity_planning",
                    description="Service count growing rapidly, capacity planning needed",
                    confidence=confidence,
                    severity="medium",
                    time_frame="1-2 weeks",
                    probability=confidence,
                    impact_assessment="Cluster may need additional capacity to handle growth",
                    recommended_actions=[
                        "Plan for cluster scaling",
                        "Review resource allocation strategies",
                        "Consider auto-scaling policies",
                        "Monitor resource utilization trends"
                    ],
                    based_on_metrics=["service_count", "growth_patterns"],
                    created_at=datetime.utcnow()
                ))
            
            return predictions
            
        except Exception as e:
            logger.error(f"Capacity prediction failed: {e}")
            return []
    
    async def _predict_anomaly_based_issues(self, snapshots: List[Any]) -> List[Prediction]:
        """Predict issues based on anomaly patterns."""
        predictions = []
        
        try:
            # Look for recurring anomaly patterns
            anomaly_counts = []
            for snapshot in snapshots:
                total_anomalies = len(snapshot.issues)
                anomaly_counts.append((snapshot.timestamp, total_anomalies))
            
            # Detect anomaly spikes
            if len(anomaly_counts) >= 5:
                recent_anomalies = [count for _, count in anomaly_counts[-5:]]
                avg_anomalies = statistics.mean(recent_anomalies)
                
                if avg_anomalies > 3:  # More than 3 issues on average
                    confidence = min(0.8, avg_anomalies / 10)
                    
                    predictions.append(Prediction(
                        prediction_id=f"anomaly_pattern_{datetime.utcnow().isoformat()}",
                        prediction_type="anomaly_escalation",
                        description="Persistent anomaly pattern detected, may indicate underlying issues",
                        confidence=confidence,
                        severity="medium",
                        time_frame="4-24 hours",
                        probability=confidence,
                        impact_assessment="Underlying issues may cause service disruptions",
                        recommended_actions=[
                            "Investigate recurring issue patterns",
                            "Check for common root causes",
                            "Review system logs for correlations",
                            "Consider preventive measures"
                        ],
                        based_on_metrics=["anomaly_count", "issue_patterns"],
                        created_at=datetime.utcnow()
                    ))
            
            return predictions
            
        except Exception as e:
            logger.error(f"Anomaly-based prediction failed: {e}")
            return []
    
    def _calculate_growth_rate(self, data_points: List[Tuple[datetime, float]]) -> float:
        """Calculate growth rate from time series data."""
        try:
            if len(data_points) < 2:
                return 0.0
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x[0])
            
            # Calculate rate of change
            start_value = data_points[0][1]
            end_value = data_points[-1][1]
            time_diff = (data_points[-1][0] - data_points[0][0]).total_seconds() / 3600  # hours
            
            if start_value == 0 or time_diff == 0:
                return 0.0
            
            # Growth rate per hour
            growth_rate = (end_value - start_value) / (start_value * time_diff)
            return growth_rate
            
        except Exception as e:
            logger.error(f"Growth rate calculation failed: {e}")
            return 0.0
    
    def _calculate_trend(self, data_points: List[Tuple[datetime, float]]) -> Dict[str, Any]:
        """Calculate trend information from time series data."""
        try:
            if len(data_points) < 3:
                return {'direction': 'unknown', 'rate': 0.0, 'confidence': 0.0}
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x[0])
            
            # Simple linear regression
            n = len(data_points)
            x_values = [(dp[0] - data_points[0][0]).total_seconds() / 3600 for dp in data_points]
            y_values = [dp[1] for dp in data_points]
            
            # Calculate slope
            x_mean = sum(x_values) / n
            y_mean = sum(y_values) / n
            
            numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return {'direction': 'stable', 'rate': 0.0, 'confidence': 0.0}
            
            slope = numerator / denominator
            
            # Determine direction
            direction = 'stable'
            if abs(slope) > 0.01:
                direction = 'increasing' if slope > 0 else 'decreasing'
            
            # Calculate R-squared for confidence
            y_pred = [slope * x_values[i] + (y_mean - slope * x_mean) for i in range(n)]
            ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
            ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
            confidence = max(0.0, r_squared)
            
            return {
                'direction': direction,
                'rate': slope,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Trend calculation failed: {e}")
            return {'direction': 'unknown', 'rate': 0.0, 'confidence': 0.0}
    
    def _analyze_namespace_growth(self, snapshots: List[Any]) -> Dict[str, Dict[str, float]]:
        """Analyze growth patterns by namespace."""
        try:
            namespace_data = defaultdict(list)
            
            for snapshot in snapshots:
                if snapshot.metadata and 'namespaces' in snapshot.metadata:
                    namespace_count = snapshot.metadata['namespaces']
                    namespace_data['total'].append((snapshot.timestamp, namespace_count))
            
            growth_analysis = {}
            for namespace, data_points in namespace_data.items():
                if len(data_points) >= 3:
                    growth_rate = self._calculate_growth_rate(data_points)
                    trend = self._calculate_trend(data_points)
                    
                    growth_analysis[namespace] = {
                        'rate': growth_rate,
                        'confidence': trend['confidence']
                    }
            
            return growth_analysis
            
        except Exception as e:
            logger.error(f"Namespace growth analysis failed: {e}")
            return {}
    
    def _format_time_frame(self, hours: float) -> str:
        """Format time frame in human-readable format."""
        if hours < 1:
            return f"{int(hours * 60)} minutes"
        elif hours < 24:
            return f"{int(hours)} hours"
        elif hours < 168:  # 1 week
            return f"{int(hours / 24)} days"
        else:
            return f"{int(hours / 168)} weeks"
    
    def get_prediction_summary(self) -> Dict[str, Any]:
        """Get summary of current predictions."""
        try:
            if not self.prediction_history:
                return {'status': 'no_predictions', 'predictions': []}
            
            # Recent predictions (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_predictions = [
                p for p in self.prediction_history 
                if p.created_at >= recent_cutoff
            ]
            
            # Categorize by severity
            severity_counts = defaultdict(int)
            type_counts = defaultdict(int)
            
            for prediction in recent_predictions:
                severity_counts[prediction.severity] += 1
                type_counts[prediction.prediction_type] += 1
            
            return {
                'status': 'active',
                'total_predictions': len(recent_predictions),
                'severity_breakdown': dict(severity_counts),
                'type_breakdown': dict(type_counts),
                'high_confidence_count': len([p for p in recent_predictions if p.confidence > 0.8]),
                'recent_predictions': [
                    {
                        'type': p.prediction_type,
                        'description': p.description,
                        'confidence': p.confidence,
                        'severity': p.severity,
                        'time_frame': p.time_frame
                    }
                    for p in recent_predictions[-5:]  # Last 5 predictions
                ]
            }
            
        except Exception as e:
            logger.error(f"Prediction summary failed: {e}")
            return {'status': 'error', 'error': str(e)}
