"""
API endpoints for observability and metrics.

This module provides API endpoints for accessing observability data,
metrics, and health information for the Kubernetes monitoring tools
and AWS Strands integration.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from src.observability.error_handler import get_observability_metrics

# Create router
router = APIRouter(
    prefix="/api/observability",
    tags=["observability"],
    responses={404: {"description": "Not found"}},
)


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get comprehensive metrics for the application.
    
    Returns:
        Dictionary containing detailed metrics information.
    """
    try:
        return get_observability_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/health")
async def get_health() -> Dict[str, Any]:
    """
    Get health status of the application.
    
    Returns:
        Dictionary containing health status information.
    """
    metrics = get_observability_metrics()
    
    # Calculate overall health status
    error_rate = 0
    if metrics["metrics"]["system_metrics"]["total_tool_executions"] > 0:
        error_rate = 1 - metrics["metrics"]["system_metrics"]["overall_success_rate"]
    
    health_status = "healthy"
    if error_rate > 0.5:
        health_status = "critical"
    elif error_rate > 0.2:
        health_status = "warning"
    
    return {
        "status": health_status,
        "timestamp": metrics["system_info"]["timestamp"],
        "uptime": metrics["system_info"]["uptime"],
        "error_rate": error_rate,
        "total_errors": metrics["errors"]["total_errors"],
        "recent_errors": len(metrics["errors"]["recent_errors"])
    }


@router.get("/tools/{tool_name}")
async def get_tool_metrics(tool_name: str) -> Dict[str, Any]:
    """
    Get metrics for a specific tool.
    
    Args:
        tool_name: Name of the tool to get metrics for.
        
    Returns:
        Dictionary containing tool metrics.
    """
    metrics = get_observability_metrics()
    
    if tool_name not in metrics["metrics"]["tool_metrics"]:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    
    return {
        "tool_name": tool_name,
        "metrics": metrics["metrics"]["tool_metrics"][tool_name],
        "usage_trends": {
            "hourly": metrics["metrics"]["usage_trends"]["hourly"].get(tool_name, {}),
            "daily": metrics["metrics"]["usage_trends"]["daily"].get(tool_name, {})
        }
    }


@router.get("/errors")
async def get_errors() -> Dict[str, Any]:
    """
    Get error summary.
    
    Returns:
        Dictionary containing error summary.
    """
    metrics = get_observability_metrics()
    return metrics["errors"]


@router.get("/dashboard")
async def get_dashboard_data() -> Dict[str, Any]:
    """
    Get comprehensive dashboard data.
    
    Returns:
        Dictionary containing dashboard data.
    """
    metrics = get_observability_metrics()
    
    # Calculate additional dashboard metrics
    tool_metrics = metrics["metrics"]["tool_metrics"]
    
    # Sort tools by usage
    tools_by_usage = sorted(
        [(name, data["total_executions"]) for name, data in tool_metrics.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Sort tools by error rate
    tools_by_error_rate = []
    for name, data in tool_metrics.items():
        if data["total_executions"] > 0:
            error_rate = data["error_count"] / data["total_executions"]
            tools_by_error_rate.append((name, error_rate))
    
    tools_by_error_rate.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate response time trends
    response_time_trends = {}
    for tool_name, hourly_data in metrics["metrics"]["usage_trends"]["hourly"].items():
        if tool_name in tool_metrics:
            response_time_trends[tool_name] = tool_metrics[tool_name]["execution_times"]["avg"]
    
    return {
        "summary": metrics["metrics"]["system_metrics"],
        "top_tools_by_usage": dict(tools_by_usage[:5]),
        "top_tools_by_error_rate": dict(tools_by_error_rate[:5]),
        "response_time_trends": response_time_trends,
        "error_summary": {
            "total_errors": metrics["errors"]["total_errors"],
            "error_types": metrics["errors"]["error_types"],
            "tools_with_errors": metrics["errors"]["tools_with_errors"]
        },
        "timestamp": metrics["system_info"]["timestamp"]
    }