"""
Trend Analysis System for Kubernetes Monitoring

Provides historical data analysis and pattern recognition capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

@dataclass
class TrendData:
    """Represents trend analysis data for a metric."""
    metric_name: str
    direction: str  # 'increasing', 'decreasing', 'stable'
    rate: float  # Rate of change
    confidence: float  # Confidence in trend (0.0 to 1.0)
    r_squared: float  # Correlation coefficient
    data_points: int
    time_span_hours: float
    prediction_next_hour: Optional[float]
    anomalies_detected: List[Dict[str, Any]]

class TrendAnalyzer:
    """
    Advanced trend analysis system for Kubernetes metrics.
    
    Features:
    - Linear regression analysis
    - Anomaly detection
    - Pattern recognition
    - Seasonal analysis
    - Predictive trending
    """
    
    def __init__(self, window_hours: int = 24):
        """Initialize the trend analyzer."""
        self.window_hours = window_hours
        self.trend_cache: Dict[str, TrendData] = {}
        self.anomaly_threshold = 2.0  # Standard deviations for anomaly detection
        
        logger.info(f"Trend Analyzer initialized with {window_hours}h window")
    
    async def analyze_trends(self, snapshots: List[Any]) -> Dict[str, TrendData]:
        """Analyze trends across multiple metrics from cluster snapshots."""
        try:
            if len(snapshots) < 3:
                logger.warning("Insufficient data for trend analysis")
                return {}
            
            trends = {}
            
            # Extract time series data
            time_series = self._extract_time_series(snapshots)
            
            # Analyze each metric
            for metric_name, values in time_series.items():
                if len(values) >= 3:  # Need minimum data points
                    trend_data = await self._analyze_metric_trend(metric_name, values)
                    trends[metric_name] = trend_data
            
            # Cache results
            self.trend_cache.update(trends)
            
            logger.info(f"Analyzed trends for {len(trends)} metrics")
            return trends
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return {}
    
    def _extract_time_series(self, snapshots: List[Any]) -> Dict[str, List[Tuple[datetime, float]]]:
        """Extract time series data from snapshots."""
        time_series = defaultdict(list)
        
        for snapshot in snapshots:
            timestamp = snapshot.timestamp
            
            # Core metrics
            time_series['health_score'].append((timestamp, snapshot.health_score))
            time_series['pod_count'].append((timestamp, float(snapshot.pod_count)))
            time_series['service_count'].append((timestamp, float(snapshot.service_count)))
            time_series['event_count'].append((timestamp, float(snapshot.event_count)))
            time_series['issues_count'].append((timestamp, float(len(snapshot.issues))))
            
            # Resource usage metrics
            for metric, value in snapshot.resource_usage.items():
                time_series[f'resource_{metric}'].append((timestamp, float(value)))
            
            # Metadata metrics
            if snapshot.metadata:
                time_series['running_pods'].append((timestamp, float(snapshot.metadata.get('running_pods', 0))))
                time_series['failed_pods'].append((timestamp, float(snapshot.metadata.get('failed_pods', 0))))
                time_series['namespaces'].append((timestamp, float(snapshot.metadata.get('namespaces', 0))))
        
        return dict(time_series)
    
    async def _analyze_metric_trend(self, metric_name: str, values: List[Tuple[datetime, float]]) -> TrendData:
        """Analyze trend for a specific metric."""
        try:
            # Sort by timestamp
            values.sort(key=lambda x: x[0])
            
            # Extract timestamps and values
            timestamps = [v[0] for v in values]
            metric_values = [v[1] for v in values]
            
            # Convert timestamps to hours from start
            start_time = timestamps[0]
            time_hours = [(t - start_time).total_seconds() / 3600 for t in timestamps]
            
            # Perform linear regression
            slope, intercept, r_squared = self._linear_regression(time_hours, metric_values)
            
            # Determine trend direction
            direction = 'stable'
            if abs(slope) > 0.01:  # Threshold for significant change
                direction = 'increasing' if slope > 0 else 'decreasing'
            
            # Calculate confidence based on R-squared and data points
            confidence = min(1.0, r_squared * (len(values) / 10))  # Scale by data points
            
            # Predict next hour value
            next_hour = time_hours[-1] + 1
            prediction_next_hour = slope * next_hour + intercept
            
            # Detect anomalies
            anomalies = self._detect_anomalies(timestamps, metric_values)
            
            return TrendData(
                metric_name=metric_name,
                direction=direction,
                rate=slope,
                confidence=confidence,
                r_squared=r_squared,
                data_points=len(values),
                time_span_hours=(timestamps[-1] - timestamps[0]).total_seconds() / 3600,
                prediction_next_hour=prediction_next_hour,
                anomalies_detected=anomalies
            )
            
        except Exception as e:
            logger.error(f"Metric trend analysis failed for {metric_name}: {e}")
            return TrendData(
                metric_name=metric_name,
                direction='unknown',
                rate=0.0,
                confidence=0.0,
                r_squared=0.0,
                data_points=len(values),
                time_span_hours=0.0,
                prediction_next_hour=None,
                anomalies_detected=[]
            )
    
    def _linear_regression(self, x: List[float], y: List[float]) -> Tuple[float, float, float]:
        """Perform linear regression and return slope, intercept, and R-squared."""
        try:
            n = len(x)
            if n < 2:
                return 0.0, 0.0, 0.0
            
            # Calculate means
            x_mean = sum(x) / n
            y_mean = sum(y) / n
            
            # Calculate slope and intercept
            numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return 0.0, y_mean, 0.0
            
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean
            
            # Calculate R-squared
            y_pred = [slope * x[i] + intercept for i in range(n)]
            ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
            ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
            
            return slope, intercept, max(0.0, r_squared)
            
        except Exception as e:
            logger.error(f"Linear regression failed: {e}")
            return 0.0, 0.0, 0.0
    
    def _detect_anomalies(self, timestamps: List[datetime], values: List[float]) -> List[Dict[str, Any]]:
        """Detect anomalies in the time series data."""
        try:
            if len(values) < 5:  # Need minimum data for anomaly detection
                return []
            
            anomalies = []
            
            # Calculate rolling statistics
            window_size = min(5, len(values) // 2)
            
            for i in range(window_size, len(values)):
                # Get window data
                window_values = values[i-window_size:i]
                current_value = values[i]
                
                # Calculate statistics
                mean_val = statistics.mean(window_values)
                std_val = statistics.stdev(window_values) if len(window_values) > 1 else 0
                
                # Check for anomaly
                if std_val > 0:
                    z_score = abs(current_value - mean_val) / std_val
                    
                    if z_score > self.anomaly_threshold:
                        anomalies.append({
                            'timestamp': timestamps[i].isoformat(),
                            'value': current_value,
                            'expected_range': [mean_val - 2*std_val, mean_val + 2*std_val],
                            'z_score': z_score,
                            'severity': 'high' if z_score > 3.0 else 'medium'
                        })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []
    
    def get_trend_summary(self) -> Dict[str, Any]:
        """Get a summary of all current trends."""
        try:
            if not self.trend_cache:
                return {'status': 'no_data', 'trends': {}}
            
            summary = {
                'status': 'active',
                'total_metrics': len(self.trend_cache),
                'trends': {},
                'alerts': []
            }
            
            # Categorize trends
            increasing_trends = []
            decreasing_trends = []
            stable_trends = []
            concerning_trends = []
            
            for metric_name, trend_data in self.trend_cache.items():
                trend_info = {
                    'direction': trend_data.direction,
                    'rate': trend_data.rate,
                    'confidence': trend_data.confidence,
                    'anomalies': len(trend_data.anomalies_detected)
                }
                
                summary['trends'][metric_name] = trend_info
                
                # Categorize
                if trend_data.direction == 'increasing':
                    increasing_trends.append(metric_name)
                elif trend_data.direction == 'decreasing':
                    decreasing_trends.append(metric_name)
                else:
                    stable_trends.append(metric_name)
                
                # Check for concerning trends
                if self._is_concerning_trend(metric_name, trend_data):
                    concerning_trends.append({
                        'metric': metric_name,
                        'reason': self._get_concern_reason(metric_name, trend_data),
                        'severity': self._get_trend_severity(metric_name, trend_data)
                    })
            
            summary.update({
                'increasing_count': len(increasing_trends),
                'decreasing_count': len(decreasing_trends),
                'stable_count': len(stable_trends),
                'concerning_trends': concerning_trends
            })
            
            return summary
            
        except Exception as e:
            logger.error(f"Trend summary generation failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _is_concerning_trend(self, metric_name: str, trend_data: TrendData) -> bool:
        """Determine if a trend is concerning."""
        # High confidence trends with significant rates
        if trend_data.confidence > 0.7 and abs(trend_data.rate) > 0.1:
            # Concerning metrics when increasing
            if trend_data.direction == 'increasing' and metric_name in [
                'failed_pods', 'issues_count', 'event_count', 'resource_cpu_usage'
            ]:
                return True
            
            # Concerning metrics when decreasing
            if trend_data.direction == 'decreasing' and metric_name in [
                'health_score', 'running_pods', 'resource_pod_utilization'
            ]:
                return True
        
        # High number of anomalies
        if len(trend_data.anomalies_detected) > 3:
            return True
        
        return False
    
    def _get_concern_reason(self, metric_name: str, trend_data: TrendData) -> str:
        """Get the reason why a trend is concerning."""
        reasons = []
        
        if abs(trend_data.rate) > 0.1:
            reasons.append(f"{trend_data.direction} at rate {trend_data.rate:.3f}")
        
        if len(trend_data.anomalies_detected) > 0:
            reasons.append(f"{len(trend_data.anomalies_detected)} anomalies detected")
        
        if trend_data.confidence > 0.8:
            reasons.append("high confidence trend")
        
        return "; ".join(reasons) if reasons else "trend analysis flagged"
    
    def _get_trend_severity(self, metric_name: str, trend_data: TrendData) -> str:
        """Get the severity level of a concerning trend."""
        if metric_name in ['health_score', 'failed_pods'] and trend_data.confidence > 0.8:
            return 'high'
        elif len(trend_data.anomalies_detected) > 5:
            return 'high'
        elif abs(trend_data.rate) > 0.2:
            return 'medium'
        else:
            return 'low'
    
    def get_metric_forecast(self, metric_name: str, hours_ahead: int = 24) -> Optional[Dict[str, Any]]:
        """Get forecast for a specific metric."""
        try:
            if metric_name not in self.trend_cache:
                return None
            
            trend_data = self.trend_cache[metric_name]
            
            if trend_data.confidence < 0.5:
                return {
                    'metric': metric_name,
                    'forecast_available': False,
                    'reason': 'insufficient_confidence'
                }
            
            # Simple linear projection
            current_prediction = trend_data.prediction_next_hour
            if current_prediction is None:
                return None
            
            forecast_value = current_prediction + (trend_data.rate * (hours_ahead - 1))
            
            # Calculate confidence decay over time
            time_confidence = max(0.1, trend_data.confidence * (0.9 ** (hours_ahead / 24)))
            
            return {
                'metric': metric_name,
                'forecast_available': True,
                'hours_ahead': hours_ahead,
                'predicted_value': forecast_value,
                'confidence': time_confidence,
                'trend_direction': trend_data.direction,
                'trend_rate': trend_data.rate,
                'based_on_points': trend_data.data_points
            }
            
        except Exception as e:
            logger.error(f"Forecast generation failed for {metric_name}: {e}")
            return None
