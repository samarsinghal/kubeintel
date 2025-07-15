"""
KubeIntel API Server

FastAPI-based REST API for Kubernetes cluster analysis using AI-powered insights.
Provides endpoints for cluster analysis, health monitoring, and predictive analytics.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional
import aiofiles

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import logging

from kubernetes_agent import KubernetesAgent
from background_monitor import BackgroundMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timeout configuration for different operations
class TimeoutConfig:
    """Configurable timeout values for different API operations."""
    CLUSTER_ANALYSIS = float(os.getenv("AGENT_ANALYSIS_TIMEOUT", "300"))  # Use env var or default to 5 minutes
    PREDICTIONS = float(os.getenv("AGENT_PREDICTIONS_TIMEOUT", "30"))     # Configurable predictions timeout
    FILE_OPERATIONS = float(os.getenv("AGENT_FILE_OPERATIONS_TIMEOUT", "10"))  # Configurable file operations timeout

# Initialize FastAPI application
app = FastAPI(
    title="KubeIntel API",
    description="AI-powered Kubernetes cluster analysis and monitoring",
    version="2.0.0"
)

# Mount static files for web interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global service instances
kubernetes_agent: Optional[KubernetesAgent] = None
background_monitor: Optional[BackgroundMonitor] = None

class AnalysisRequest(BaseModel):
    """Request model for cluster analysis."""
    analysis_request: str
    scope: str = "cluster"
    target: Optional[str] = None

async def execute_with_timeout(operation, timeout: float, operation_name: str):
    """
    Execute an async operation with timeout and graceful error handling.
    
    Args:
        operation: The async operation to execute
        timeout: Timeout in seconds
        operation_name: Name of the operation for logging
    
    Returns:
        The result of the operation
    
    Raises:
        HTTPException: On timeout or other errors
    """
    try:
        return await asyncio.wait_for(operation, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"{operation_name} timed out after {timeout} seconds")
        raise HTTPException(
            status_code=408,
            detail=f"{operation_name} timed out after {timeout} seconds"
        )
    except Exception as e:
        logger.error(f"{operation_name} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup (completely non-blocking)."""
    global kubernetes_agent, background_monitor
    
    logger.info("Starting KubeIntel API server")
    
    async def initialize_kubernetes_agent():
        """Initialize Kubernetes agent asynchronously."""
        try:
            # Wrap potentially blocking initialization in thread executor
            loop = asyncio.get_event_loop()
            agent = await loop.run_in_executor(None, KubernetesAgent)
            logger.info("Kubernetes agent initialized successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes agent: {e}")
            return None
    
    async def initialize_background_monitor():
        """Initialize background monitor asynchronously."""
        try:
            # Wrap potentially blocking initialization in thread executor
            loop = asyncio.get_event_loop()
            monitor = await loop.run_in_executor(None, BackgroundMonitor)
            logger.info("Background monitor initialized successfully")
            return monitor
        except Exception as e:
            logger.error(f"Failed to initialize background monitor: {e}")
            return None
    
    async def start_background_services():
        """Start background services without blocking startup."""
        try:
            if background_monitor:
                # Start background monitoring in a separate task
                monitor_task = asyncio.create_task(background_monitor.start())
                logger.info("Background monitoring startup initiated")
                
                # Don't await the task - let it run in background
                # Store task reference to prevent garbage collection
                app.state.monitor_task = monitor_task
            else:
                logger.warning("Background monitor not available - skipping background services")
        except Exception as e:
            logger.error(f"Failed to start background services: {e}")
    
    try:
        # Initialize services with configurable timeout to prevent hanging startup
        startup_timeout = float(os.getenv("AGENT_STARTUP_TIMEOUT", "30"))
        initialization_tasks = [
            asyncio.wait_for(initialize_kubernetes_agent(), timeout=startup_timeout),
            asyncio.wait_for(initialize_background_monitor(), timeout=startup_timeout)
        ]
        
        # Run initializations concurrently
        results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
        
        # Process results
        kubernetes_agent = results[0] if not isinstance(results[0], Exception) else None
        background_monitor = results[1] if not isinstance(results[1], Exception) else None
        
        # Log initialization results
        if kubernetes_agent:
            logger.info("Kubernetes agent ready")
        else:
            logger.warning("Kubernetes agent initialization failed - analysis features disabled")
        
        if background_monitor:
            logger.info("Background monitor ready")
            # Start background services asynchronously
            await start_background_services()
        else:
            logger.warning("Background monitor initialization failed - monitoring features disabled")
        
        # Server is ready regardless of service initialization status
        logger.info("KubeIntel API server startup completed")
        
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}")
        logger.warning("Server starting with limited functionality")
        # Don't raise - let the server start even if services fail

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of services with proper async handling."""
    global background_monitor
    
    logger.info("Initiating KubeIntel services shutdown")
    
    async def shutdown_background_monitor():
        """Shutdown background monitor gracefully."""
        if background_monitor:
            try:
                # Use configurable timeout for shutdown to prevent hanging
                shutdown_timeout = float(os.getenv("AGENT_SHUTDOWN_TIMEOUT", "30"))
                await asyncio.wait_for(
                    background_monitor.stop(),
                    timeout=shutdown_timeout
                )
                logger.info("Background monitoring stopped successfully")
            except asyncio.TimeoutError:
                logger.warning("Background monitor shutdown timed out")
            except Exception as e:
                logger.error(f"Error stopping background monitor: {e}")
        else:
            logger.info("Background monitor not initialized - nothing to stop")
    
    async def cleanup_background_tasks():
        """Cancel and cleanup background tasks."""
        try:
            # Cancel monitor task if it exists
            if hasattr(app.state, 'monitor_task'):
                monitor_task = app.state.monitor_task
                if not monitor_task.done():
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        logger.info("Background monitor task cancelled")
                    except Exception as e:
                        logger.warning(f"Error cancelling monitor task: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up background tasks: {e}")
    
    try:
        # Run shutdown operations concurrently with timeout
        shutdown_tasks = [
            shutdown_background_monitor(),
            cleanup_background_tasks()
        ]
        
        # Wait for all shutdown tasks with configurable overall timeout
        overall_shutdown_timeout = float(os.getenv("AGENT_SHUTDOWN_TIMEOUT", "45"))
        await asyncio.wait_for(
            asyncio.gather(*shutdown_tasks, return_exceptions=True),
            timeout=overall_shutdown_timeout
        )
        
        logger.info("KubeIntel services shutdown completed")
        
    except asyncio.TimeoutError:
        logger.warning("Shutdown process timed out - forcing exit")
    except Exception as e:
        logger.error(f"Unexpected error during shutdown: {e}")
    finally:
        logger.info("KubeIntel API server shutdown finished")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard interface."""
    try:
        # Use timeout for file operations to prevent hanging
        async def read_dashboard_file():
            async with aiofiles.open("static/index.html", "r") as f:
                return await f.read()
        
        content = await asyncio.wait_for(
            read_dashboard_file(),
            timeout=TimeoutConfig.FILE_OPERATIONS
        )
        return HTMLResponse(content=content)
    except asyncio.TimeoutError:
        logger.error("Dashboard file read timed out")
        raise HTTPException(status_code=408, detail="File read timeout")
    except FileNotFoundError:
        logger.error("Dashboard file not found: static/index.html")
        raise HTTPException(status_code=404, detail="Dashboard not found")
    except Exception as e:
        logger.error(f"Error serving dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Simple, robust health check endpoint."""
    try:
        return {
            "healthy": True,
            "status": "ok",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "server": "running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "healthy": False,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "server": "error"
        }

@app.get("/analyze")
async def analyze_cluster_get():
    """Analyze Kubernetes cluster with default request (GET method)."""
    # Default analysis request
    default_request = AnalysisRequest(analysis_request="Provide comprehensive cluster health analysis with specific pod counts and metrics")
    return await analyze_cluster(default_request)

@app.post("/analyze")
async def analyze_cluster(request: AnalysisRequest):
    """Analyze Kubernetes cluster based on user request."""
    if not kubernetes_agent:
        raise HTTPException(status_code=503, detail="Kubernetes agent not initialized")
    
    try:
        logger.info(f"Processing analysis request - scope: {request.scope}")
        
        analysis_id = f"analysis-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # Execute analysis with configurable timeout
        try:
            result = await asyncio.wait_for(
                kubernetes_agent.analyze_cluster(
                    request=request.analysis_request,
                    scope=request.scope,
                    namespace=request.target if request.scope == "namespace" else None
                ),
                timeout=TimeoutConfig.CLUSTER_ANALYSIS
            )
        except asyncio.TimeoutError:
            logger.warning(f"Analysis timed out: {analysis_id}")
            return {
                "analysis_id": analysis_id,
                "status": "timeout",
                "error": f"Analysis timed out after {TimeoutConfig.CLUSTER_ANALYSIS} seconds",
                "timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "timeout_duration": TimeoutConfig.CLUSTER_ANALYSIS
            }
        
        # Add metadata to result
        result["analysis_id"] = analysis_id
        result["timestamp"] = datetime.utcnow().isoformat()
        
        logger.info(f"Analysis completed: {analysis_id}")
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {
            "analysis_id": f"error-{uuid.uuid4().hex[:8]}",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "success": False
        }

@app.get("/predictions")
async def get_predictions():
    """Get predictive insights from background monitoring with improved formatting."""
    if not background_monitor:
        logger.warning("Predictions requested but background monitor not initialized")
        return {
            "status": "unavailable",
            "message": "Background monitoring not initialized",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        # Use configurable timeout for predictions to prevent blocking
        predictions = await asyncio.wait_for(
            background_monitor.get_predictions(),
            timeout=TimeoutConfig.PREDICTIONS
        )
        
        # Enhance the response with better formatting for frontend
        if predictions.get("status") == "active" and predictions.get("insights"):
            insights = predictions["insights"]
            
            # Format the analysis for better display
            formatted_analysis = insights.get("analysis", "")
            
            # Add metadata for frontend display
            predictions["display"] = {
                "title": "🧠 KubeIntel Background Intelligence",
                "subtitle": "🔮 Dynamic Cluster Predictions",
                "generated_at": "Real-time",
                "analysis": formatted_analysis,
                "next_analysis": "Continuous monitoring",
                "analysis_type": insights.get("type", "comprehensive_predictions"),
                "footer": "💡 Predictions are generated dynamically based on current cluster state"
            }
        
        return predictions
    except asyncio.TimeoutError:
        logger.warning("Predictions request timed out")
        return {
            "status": "timeout",
            "error": f"Predictions request timed out after {TimeoutConfig.PREDICTIONS} seconds",
            "timestamp": datetime.utcnow().isoformat(),
            "timeout_duration": TimeoutConfig.PREDICTIONS
        }
    except Exception as e:
        logger.error(f"Failed to get predictions: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# COST VISUALIZER API ENDPOINTS
# ============================================================================

@app.get("/cost-visualizer", response_class=HTMLResponse)
async def get_cost_visualizer_dashboard():
    """Serve the Cost Visualizer dashboard interface."""
    try:
        async with aiofiles.open("static/cost-visualizer.html", mode="r") as f:
            content = await f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        logger.error("cost-visualizer.html not found")
        raise HTTPException(status_code=404, detail="Cost visualizer page not found")
    except Exception as e:
        logger.error(f"Error serving cost visualizer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/cost/analysis")
async def get_cost_analysis():
    """Get comprehensive cost analysis and token usage data."""
    try:
        from cost_visualizer import get_cost_visualizer
        cost_visualizer = get_cost_visualizer()
        
        analysis = await cost_visualizer.get_session_costs()
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to get cost analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cost/session-details")
async def get_session_details():
    """Get detailed session information including file analysis."""
    try:
        # This endpoint would provide detailed session file analysis
        # For now, return basic session info
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "session_info": {
                "active_sessions": 1,
                "session_directory": "/tmp/strands/sessions",
                "estimated_files": 20,
                "rotation_status": "active"
            },
            "note": "Detailed session file analysis requires pod-level access"
        }
        
    except Exception as e:
        logger.error(f"Failed to get session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cost/projections")
async def get_cost_projections():
    """Get detailed cost projections and scenarios."""
    try:
        from cost_visualizer import get_cost_visualizer
        cost_visualizer = get_cost_visualizer()
        
        # Get current analysis
        analysis = await cost_visualizer.get_session_costs()
        
        # Return projections with additional scenarios
        projections = analysis.get('projections', {})
        
        # Add scenario analysis
        projections['scenarios'] = {
            "current_usage": projections.get('daily', {}),
            "high_usage": {
                "description": "20 agent analyses per day",
                "daily_cost": projections.get('daily', {}).get('total_estimated', 0) * 2,
                "monthly_cost": projections.get('monthly', {}).get('total_estimated', 0) * 2
            },
            "low_usage": {
                "description": "5 agent analyses per day",
                "daily_cost": projections.get('daily', {}).get('total_estimated', 0) * 0.5,
                "monthly_cost": projections.get('monthly', {}).get('total_estimated', 0) * 0.5
            }
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "projections": projections
        }
        
    except Exception as e:
        logger.error(f"Failed to get cost projections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# TELEMETRY API ENDPOINTS FOR FLOW VISUALIZER
# ============================================================================

@app.get("/flow-visualizer", response_class=HTMLResponse)
async def get_flow_visualizer():
    """Serve the Flow Visualizer interface."""
    try:
        async def read_flow_visualizer_file():
            async with aiofiles.open("static/flow-visualizer.html", "r") as f:
                return await f.read()
        
        content = await asyncio.wait_for(
            read_flow_visualizer_file(),
            timeout=TimeoutConfig.FILE_OPERATIONS
        )
        return HTMLResponse(content=content)
    except asyncio.TimeoutError:
        logger.error("Flow visualizer file read timed out")
        raise HTTPException(status_code=408, detail="File read timeout")
    except FileNotFoundError:
        logger.error("Flow visualizer file not found: static/flow-visualizer.html")
        raise HTTPException(status_code=404, detail="Flow visualizer not found")
    except Exception as e:
        logger.error(f"Error serving flow visualizer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/telemetry/agent-flows")
async def get_agent_flows(limit: int = 20):
    """Get recent agent analysis flows with telemetry data."""
    try:
        from telemetry_api import get_telemetry_collector
        telemetry = get_telemetry_collector()
        flows = telemetry.get_agent_flows(limit)
        
        return {
            "status": "success",
            "flows": flows,
            "count": len(flows),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get agent flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/monitor-flows")
async def get_monitor_flows(limit: int = 20):
    """Get recent background monitor flows with telemetry data."""
    try:
        from telemetry_api import get_telemetry_collector
        telemetry = get_telemetry_collector()
        flows = telemetry.get_monitor_flows(limit)
        
        return {
            "status": "success",
            "flows": flows,
            "count": len(flows),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get monitor flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/metrics")
async def get_flow_metrics():
    """Get aggregated flow metrics and statistics."""
    try:
        from telemetry_api import get_telemetry_collector
        telemetry = get_telemetry_collector()
        metrics = telemetry.get_flow_metrics()
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get flow metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/status")
async def get_telemetry_status():
    """Get telemetry system status and health."""
    try:
        from telemetry_api import get_telemetry_collector
        telemetry = get_telemetry_collector()
        metrics = telemetry.get_flow_metrics()
        
        return {
            "status": "active",
            "telemetry_enabled": True,
            "traces_enabled": telemetry.traces_enabled,
            "active_flows": metrics.get("active_flows", 0),
            "total_flows_tracked": metrics.get("total_flows", 0),
            "agent_flows": metrics.get("agent_flows", 0),
            "monitor_flows": metrics.get("monitor_flows", 0),
            "total_traces": metrics.get("total_traces", 0),
            "success_rate": metrics.get("success_rate", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get telemetry status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/traces")
async def get_traces(limit: int = 50, flow_type: str = None):
    """Get recent traces with optional filtering by flow type."""
    try:
        from telemetry_api import get_telemetry_collector
        telemetry = get_telemetry_collector()
        traces = telemetry.get_traces(limit, flow_type)
        
        return {
            "status": "success",
            "traces": traces,
            "count": len(traces),
            "traces_enabled": telemetry.traces_enabled,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/traces/{trace_id}")
async def get_trace_by_id(trace_id: str):
    """Get a specific trace by its ID."""
    try:
        from telemetry_api import get_telemetry_collector
        telemetry = get_telemetry_collector()
        trace = telemetry.get_trace_by_id(trace_id)
        
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
        
        return {
            "status": "success",
            "trace": trace,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace {trace_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Get configurable host and port settings
    host = os.getenv("AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("AGENT_PORT", "8000"))
    log_level = os.getenv("AGENT_LOG_LEVEL", "info").lower()
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        log_level=log_level
    )
