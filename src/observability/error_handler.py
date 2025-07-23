"""
Enhanced Error Handling and Observability for AWS Strands Integration

This module provides comprehensive error handling, logging, and metrics collection
for the Kubernetes monitoring tools and AWS Strands integration.
"""

import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from collections import defaultdict, deque
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and manages metrics for tool execution and agent usage.
    
    This class provides comprehensive metrics collection for monitoring
    tool performance, error rates, and usage patterns.
    """
    
    def __init__(self):
        # Basic metrics
        self._metrics = defaultdict(lambda: defaultdict(int))
        self._execution_times = defaultdict(deque)
        self._error_counts = defaultdict(int)
        self._success_counts = defaultdict(int)
        
        # Advanced metrics
        self._hourly_usage = defaultdict(lambda: defaultdict(int))  # Tool usage by hour
        self._daily_usage = defaultdict(lambda: defaultdict(int))   # Tool usage by day
        self._error_types = defaultdict(lambda: defaultdict(int))   # Error types by tool
        self._parameter_usage = defaultdict(lambda: defaultdict(int))  # Parameter usage by tool
        self._result_sizes = defaultdict(deque)  # Result sizes for monitoring
        self._response_times = deque(maxlen=1000)  # Overall response times
        
        # Timestamp of first metric collection
        self._start_time = datetime.now()
        
        # Thread safety
        self._lock = threading.Lock()
    
    def record_tool_execution(self, tool_name: str, execution_time: float, success: bool, error_type: Optional[str] = None, 
                             params: Optional[Dict[str, Any]] = None, result_size: Optional[int] = None):
        """
        Record comprehensive metrics for tool execution.
        
        Args:
            tool_name: Name of the tool being executed.
            execution_time: Time taken to execute the tool in seconds.
            success: Whether the execution was successful.
            error_type: Type of error if the execution failed.
            params: Parameters passed to the tool.
            result_size: Size of the result returned by the tool.
        """
        with self._lock:
            # Record execution time
            if execution_time is not None:
                self._execution_times[tool_name].append(execution_time)
                self._response_times.append(execution_time)
                
                # Keep only last 100 execution times per tool
                if len(self._execution_times[tool_name]) > 100:
                    self._execution_times[tool_name].popleft()
            
            # Record success/failure
            if success:
                self._success_counts[tool_name] += 1
            else:
                self._error_counts[tool_name] += 1
                if error_type:
                    self._error_types[tool_name][error_type] += 1
            
            # Record usage by time
            now = datetime.now()
            hour_key = now.strftime("%Y-%m-%d %H:00")
            day_key = now.strftime("%Y-%m-%d")
            
            self._hourly_usage[tool_name][hour_key] += 1
            self._daily_usage[tool_name][day_key] += 1
            
            # Record parameter usage if provided
            if params:
                for param_name, param_value in params.items():
                    if param_value is not None:
                        # For simple types, record the actual value
                        if isinstance(param_value, (str, int, bool, float)):
                            self._parameter_usage[tool_name][f"{param_name}={param_value}"] += 1
                        else:
                            # For complex types, just record that the parameter was used
                            self._parameter_usage[tool_name][f"{param_name}=<{type(param_value).__name__}>"] += 1
            
            # Record result size if provided
            if result_size is not None:
                if not tool_name in self._result_sizes:
                    self._result_sizes[tool_name] = deque(maxlen=100)
                self._result_sizes[tool_name].append(result_size)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary containing detailed metrics information.
        """
        with self._lock:
            now = datetime.now()
            uptime = (now - self._start_time).total_seconds()
            
            metrics_summary = {
                "timestamp": now.isoformat(),
                "uptime_seconds": uptime,
                "tool_metrics": {},
                "system_metrics": {
                    "total_tool_executions": sum(self._success_counts.values()) + sum(self._error_counts.values()),
                    "overall_success_rate": (
                        sum(self._success_counts.values()) / 
                        (sum(self._success_counts.values()) + sum(self._error_counts.values()))
                        if (sum(self._success_counts.values()) + sum(self._error_counts.values())) > 0 else 0
                    ),
                    "overall_avg_response_time": sum(self._response_times) / len(self._response_times) if self._response_times else 0,
                    "tools_used": len(set(list(self._success_counts.keys()) + list(self._error_counts.keys()))),
                    "executions_per_minute": (
                        (sum(self._success_counts.values()) + sum(self._error_counts.values())) / (uptime / 60)
                        if uptime > 0 else 0
                    )
                },
                "usage_trends": {
                    "hourly": {},
                    "daily": {}
                }
            }
            
            # Compile tool-specific metrics
            for tool_name in set(list(self._success_counts.keys()) + list(self._error_counts.keys())):
                execution_times = list(self._execution_times[tool_name])
                
                tool_metrics = {
                    "total_executions": self._success_counts[tool_name] + self._error_counts[tool_name],
                    "success_count": self._success_counts[tool_name],
                    "error_count": self._error_counts[tool_name],
                    "success_rate": (
                        self._success_counts[tool_name] / 
                        (self._success_counts[tool_name] + self._error_counts[tool_name])
                        if (self._success_counts[tool_name] + self._error_counts[tool_name]) > 0 else 0
                    ),
                    "execution_times": {
                        "avg": sum(execution_times) / len(execution_times) if execution_times else 0,
                        "min": min(execution_times) if execution_times else 0,
                        "max": max(execution_times) if execution_times else 0,
                        "p95": self._percentile(execution_times, 95) if execution_times else 0,
                        "p99": self._percentile(execution_times, 99) if execution_times else 0
                    }
                }
                
                # Add error type breakdown if errors occurred
                if self._error_counts[tool_name] > 0:
                    tool_metrics["error_types"] = dict(self._error_types[tool_name])
                
                # Add parameter usage statistics
                if tool_name in self._parameter_usage:
                    # Get top 5 most common parameter values
                    param_items = sorted(
                        self._parameter_usage[tool_name].items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:5]
                    tool_metrics["common_parameters"] = dict(param_items)
                
                # Add result size statistics if available
                if tool_name in self._result_sizes and self._result_sizes[tool_name]:
                    result_sizes = list(self._result_sizes[tool_name])
                    tool_metrics["result_sizes"] = {
                        "avg": sum(result_sizes) / len(result_sizes),
                        "min": min(result_sizes),
                        "max": max(result_sizes)
                    }
                
                metrics_summary["tool_metrics"][tool_name] = tool_metrics
            
            # Add usage trends
            for tool_name in self._hourly_usage:
                if tool_name not in metrics_summary["usage_trends"]["hourly"]:
                    metrics_summary["usage_trends"]["hourly"][tool_name] = {}
                
                # Get last 24 hours of data
                last_24_hours = sorted(self._hourly_usage[tool_name].items())[-24:]
                metrics_summary["usage_trends"]["hourly"][tool_name] = dict(last_24_hours)
            
            for tool_name in self._daily_usage:
                if tool_name not in metrics_summary["usage_trends"]["daily"]:
                    metrics_summary["usage_trends"]["daily"][tool_name] = {}
                
                # Get last 7 days of data
                last_7_days = sorted(self._daily_usage[tool_name].items())[-7:]
                metrics_summary["usage_trends"]["daily"][tool_name] = dict(last_7_days)
            
            return metrics_summary
    
    def _percentile(self, data: list[float], percentile: int) -> float:
        """
        Calculate the given percentile of a list of values.
        
        Args:
            data: List of values.
            percentile: Percentile to calculate (0-100).
            
        Returns:
            Percentile value.
        """
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            
            lower_value = sorted_data[lower_index]
            upper_value = sorted_data[upper_index] if upper_index < len(sorted_data) else sorted_data[lower_index]
            
            interpolation = index - lower_index
            return lower_value + (upper_value - lower_value) * interpolation


class ErrorHandler:
    """Enhanced error handling with structured error responses and fallback mechanisms."""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.error_history = deque(maxlen=1000)  # Keep last 1000 errors
        self._lock = threading.Lock()
    
    def handle_tool_error(self, tool_name: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle and structure tool errors with proper logging and metrics."""
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "traceback": traceback.format_exc()
        }
        
        # Log the error
        logger.error(f"Tool {tool_name} failed: {error_info['error_type']}: {error_info['error_message']}")
        logger.debug(f"Full traceback for {tool_name}: {error_info['traceback']}")
        
        # Store error history
        with self._lock:
            self.error_history.append(error_info)
        
        # Record metrics
        self.metrics_collector.record_tool_execution(
            tool_name=tool_name,
            execution_time=0,  # Error occurred, no meaningful execution time
            success=False,
            error_type=error_info['error_type']
        )
        
        # Return structured error response
        return {
            "status": "error",
            "error": error_info['error_message'],
            "error_type": error_info['error_type'],
            "tool_name": tool_name,
            "timestamp": error_info['timestamp'],
            "suggestions": self._get_error_suggestions(error_info['error_type'])
        }
    
    def _get_error_suggestions(self, error_type: str) -> list:
        """Provide helpful suggestions based on error type."""
        suggestions = {
            "KubernetesClientError": [
                "Check if kubectl is configured correctly",
                "Verify cluster connectivity",
                "Ensure proper RBAC permissions"
            ],
            "ApiException": [
                "Check Kubernetes API server status",
                "Verify authentication credentials",
                "Check if the requested resource exists"
            ],
            "ConnectionError": [
                "Check network connectivity to Kubernetes cluster",
                "Verify cluster endpoint is accessible",
                "Check firewall and security group settings"
            ],
            "TimeoutError": [
                "Increase timeout settings",
                "Check cluster performance",
                "Verify network latency"
            ]
        }
        
        return suggestions.get(error_type, ["Check logs for more details", "Retry the operation"])
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        with self._lock:
            recent_errors = list(self.error_history)
        
        error_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_errors": len(recent_errors),
            "error_types": defaultdict(int),
            "tools_with_errors": defaultdict(int),
            "recent_errors": []
        }
        
        for error in recent_errors:
            error_summary["error_types"][error["error_type"]] += 1
            error_summary["tools_with_errors"][error["tool_name"]] += 1
        
        # Get last 10 errors
        error_summary["recent_errors"] = recent_errors[-10:] if recent_errors else []
        
        return error_summary


# Global instances
_metrics_collector = MetricsCollector()
_error_handler = ErrorHandler(_metrics_collector)


def with_error_handling(tool_name: str):
    """
    Decorator to add comprehensive error handling and metrics collection to tools.
    
    This decorator adds error handling, metrics collection, and fallback mechanisms
    to tool methods. It ensures that tools fail gracefully and provide structured
    error information.
    
    Args:
        tool_name: Name of the tool being decorated.
        
    Returns:
        Decorated function with error handling and metrics collection.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Execute the tool
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Estimate result size for metrics
                result_size = None
                if isinstance(result, dict):
                    try:
                        import json
                        result_size = len(json.dumps(result))
                    except:
                        pass
                
                # Record successful execution with enhanced metrics
                _metrics_collector.record_tool_execution(
                    tool_name=tool_name,
                    execution_time=execution_time,
                    success=True,
                    params=kwargs,
                    result_size=result_size
                )
                
                # Add execution time to result for observability
                if isinstance(result, dict):
                    result["execution_time"] = f"{execution_time:.3f}s"
                
                # Log successful execution
                logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Handle the error
                context = {
                    "args": str(args)[:200],  # Truncate long arguments
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},  # Truncate long values
                    "execution_time": f"{execution_time:.3f}s"
                }
                
                # Record failed execution with enhanced metrics
                _metrics_collector.record_tool_execution(
                    tool_name=tool_name,
                    execution_time=execution_time,
                    success=False,
                    error_type=type(e).__name__,
                    params=kwargs
                )
                
                # Try to get fallback data if available
                fallback_data = None
                if args and hasattr(args[0], '_get_fallback_data'):
                    try:
                        fallback_data = args[0]._get_fallback_data(tool_name, kwargs)
                    except Exception as fallback_error:
                        logger.warning(f"Failed to get fallback data for {tool_name}: {fallback_error}")
                
                # If fallback data is available, use it
                if fallback_data is not None:
                    logger.info(f"Using fallback data for {tool_name}")
                    
                    # Record fallback usage in metrics
                    _metrics_collector._metrics[tool_name]["fallback_used"] += 1
                    
                    return {
                        "data": fallback_data,
                        "status": "fallback",
                        "message": f"Using fallback data for {tool_name} due to error: {str(e)}",
                        "error_details": {
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        },
                        "execution_time": f"{execution_time:.3f}s"
                    }
                
                # If no fallback data, return error
                error_response = _error_handler.handle_tool_error(tool_name, e, context)
                
                # Add execution time to error response
                error_response["execution_time"] = f"{execution_time:.3f}s"
                
                return error_response
        
        return wrapper
    return decorator


def get_observability_metrics() -> Dict[str, Any]:
    """Get comprehensive observability metrics."""
    return {
        "metrics": _metrics_collector.get_metrics(),
        "errors": _error_handler.get_error_summary(),
        "system_info": {
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time(),  # This would be better with actual start time
            "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"
        }
    }


def log_tool_invocation(tool_name: str, args: tuple, kwargs: dict, result: Any):
    """
    Log tool invocation details with comprehensive information.
    
    This function logs detailed information about tool invocations, including
    parameters, results, execution time, and any errors or warnings.
    
    Args:
        tool_name: Name of the tool being invoked.
        args: Positional arguments passed to the tool.
        kwargs: Keyword arguments passed to the tool.
        result: Result returned by the tool.
    """
    # Log basic invocation info
    logger.info(f"Tool invoked: {tool_name}")
    
    # Log parameters (safely truncated)
    safe_args = [str(arg)[:100] + "..." if len(str(arg)) > 100 else str(arg) for arg in args[1:]] if len(args) > 1 else []
    safe_kwargs = {k: (str(v)[:100] + "..." if len(str(v)) > 100 else str(v)) for k, v in kwargs.items()}
    
    logger.debug(f"Tool {tool_name} args: {safe_args}")
    logger.debug(f"Tool {tool_name} kwargs: {safe_kwargs}")
    
    # Log result status
    if isinstance(result, dict):
        if result.get("status") == "error":
            logger.warning(f"Tool {tool_name} returned error: {result.get('error', 'Unknown error')}")
            logger.debug(f"Tool {tool_name} error details: {result.get('error_type', 'Unknown')}")
            
            # Log suggestions if available
            if "suggestions" in result:
                logger.info(f"Tool {tool_name} error suggestions: {result['suggestions']}")
                
        elif result.get("status") == "fallback":
            logger.warning(f"Tool {tool_name} using fallback data: {result.get('message', 'Fallback activated')}")
            
        else:
            # Log success with some result metadata
            result_summary = {}
            
            # Extract key metrics from result for logging
            if "count" in result:
                result_summary["count"] = result["count"]
            if "summary" in result and isinstance(result["summary"], dict):
                for key in ["running", "pending", "failed", "ready"]:
                    if key in result["summary"]:
                        result_summary[key] = result["summary"][key]
            
            logger.info(f"Tool {tool_name} completed successfully: {result_summary}")
    else:
        logger.debug(f"Tool {tool_name} completed successfully with non-dict result")
    
    # Log execution time if available
    if isinstance(result, dict) and "execution_time" in result:
        logger.info(f"Tool {tool_name} execution time: {result['execution_time']}")
        
    # Log any warnings in the result
    if isinstance(result, dict) and "warnings" in result and result["warnings"]:
        logger.warning(f"Tool {tool_name} warnings: {len(result['warnings'])} warnings found")
        for warning in result["warnings"][:3]:  # Log first 3 warnings
            logger.warning(f"Tool {tool_name} warning: {warning}")


class FallbackMechanism:
    """Provides fallback mechanisms for failed operations."""
    
    @staticmethod
    def get_basic_cluster_info() -> Dict[str, Any]:
        """Fallback method to get basic cluster information."""
        return {
            "status": "fallback",
            "message": "Using fallback mechanism - limited cluster information available",
            "basic_info": {
                "timestamp": datetime.now().isoformat(),
                "fallback_mode": True,
                "available_operations": ["basic_health_check", "simple_pod_list"]
            }
        }
    
    @staticmethod
    def get_fallback_analysis(error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when primary analysis fails."""
        return {
            "status": "fallback_analysis",
            "message": "Primary analysis failed, providing basic recommendations",
            "recommendations": [
                "Check cluster connectivity",
                "Verify authentication credentials",
                "Review recent cluster events",
                "Check resource availability"
            ],
            "error_context": error_context,
            "timestamp": datetime.now().isoformat()
        }
def with_logging(tool_name: str):
    """
    Decorator to add comprehensive logging to tools.
    
    This decorator logs tool invocations, parameters, and results.
    It should be applied after the @tool decorator but before @with_error_handling.
    
    Args:
        tool_name: Name of the tool being decorated.
        
    Returns:
        Decorated function with logging.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the tool
            result = func(*args, **kwargs)
            
            # Log the invocation
            log_tool_invocation(tool_name, args, kwargs, result)
            
            return result
        return wrapper
    return decorator