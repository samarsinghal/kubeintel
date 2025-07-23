"""
AWS Strands Kubernetes Monitoring API with Event Loop and Streaming

FastAPI server that provides REST API and real-time streaming capabilities
for the AWS Strands Kubernetes monitoring agent.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import uuid

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from src.strands_k8s_agent import StrandsKubernetesAgent
from src.streaming.sse_handler import MonitoringSSEStream
from src.api.observability import router as observability_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
strands_agent: Optional[StrandsKubernetesAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global strands_agent
    
    # Startup
    logger.info("Starting AWS Strands Kubernetes Monitoring API")
    try:
        strands_agent = StrandsKubernetesAgent(
            enable_event_loop=True,   # Re-enable event loop for predictive analytics
            enable_streaming=False    # Keep streaming disabled
        )
        
        # Start monitoring in background
        asyncio.create_task(strands_agent.start_monitoring())
        
        logger.info("AWS Strands agent started successfully")
    except Exception as e:
        logger.error(f"Failed to start Strands agent: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AWS Strands Kubernetes Monitoring API")
    if strands_agent:
        await strands_agent.stop_monitoring()

# Create FastAPI app with lifespan
app = FastAPI(
    title="AWS Strands Kubernetes Monitoring Agent",
    description="AI-powered Kubernetes cluster monitoring with real-time streaming",
    version="1.0.1",
    lifespan=lifespan
)

# Request/Response Models
class AnalysisRequest(BaseModel):
    scope: str = Field(default="cluster", description="Analysis scope: cluster, namespace, or service")
    target: Optional[str] = Field(default=None, description="Target namespace or service name")
    analysis_request: str = Field(description="What to analyze or question to ask")
    include_logs: bool = Field(default=False, description="Include pod logs in analysis")

class StreamingRequest(BaseModel):
    prompt: str = Field(description="Analysis prompt")
    namespace: Optional[str] = Field(default=None, description="Optional namespace filter")
    include_logs: bool = Field(default=False, description="Include pod logs")
    stream_type: str = Field(default="analysis", description="Type of stream: analysis, monitoring, events")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(observability_router)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI."""
    try:
        with open("static/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>AWS Strands Kubernetes Monitoring</title></head>
            <body>
                <h1>AWS Strands Kubernetes Monitoring Agent</h1>
                <p>Real-time Kubernetes monitoring with AI-powered analysis</p>
                <ul>
                    <li><a href="/docs">API Documentation</a></li>
                    <li><a href="/health">Health Check</a></li>
                    <li><a href="/status">Event Loop Status</a></li>
                    <li><a href="/dashboard">Observability Dashboard</a></li>
                </ul>
            </body>
        </html>
        """)

@app.get("/dashboard", response_class=HTMLResponse)
async def observability_dashboard():
    """Serve the Strands observability dashboard."""
    try:
        with open("static/dashboard.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Strands Observability Dashboard</title></head>
            <body>
                <h1>Strands Observability Dashboard</h1>
                <p>Dashboard file not found. Please make sure the dashboard.html file exists in the static directory.</p>
                <p><a href="/">Back to Home</a></p>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint with comprehensive status."""
    try:
        if not strands_agent:
            return JSONResponse(
                status_code=503,
                content={"healthy": False, "error": "Agent not initialized"}
            )
        
        # Get event loop status
        event_loop_status = strands_agent.get_event_loop_status()
        
        # Get streaming status
        websocket_manager = strands_agent.get_websocket_manager()
        sse_handler = strands_agent.get_sse_handler()
        
        streaming_status = {
            "websocket_clients": websocket_manager.get_client_count() if websocket_manager else 0,
            "sse_clients": sse_handler.get_client_count() if sse_handler else 0
        }
        
        return {
            "healthy": True,
            "framework": "AWS Strands",
            "version": "1.0.1",
            "components": {
                "strands_agent": True,
                "kubernetes_api": True,
                "event_loop": event_loop_status.get("running", False),
                "streaming": True,
                "tools_available": 3
            },
            "event_loop": event_loop_status,
            "streaming": streaming_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"healthy": False, "error": str(e)}
        )

@app.post("/analyze")
async def analyze_cluster(request: AnalysisRequest):
    """Analyze cluster with AI-powered insights - real-time response only."""
    if not strands_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        logger.info(f"Real-time analysis request - scope: {request.scope}, target: {request.target}")
        
        # Collect cluster data first
        cluster_data = await strands_agent.data_collector.collect_cluster_data(
            namespace=request.target if request.scope == "namespace" else None,
            include_logs=request.include_logs
        )
        
        # Use AWS Strands with VPC endpoint support - NO FALLBACK
        try:
            from src.strands_vpc_analyzer import StrandsVPCAnalyzer
            
            logger.info("🤖 Starting AWS Strands analysis with VPC endpoints")
            strands_analyzer = StrandsVPCAnalyzer()
            
            result = await asyncio.wait_for(
                strands_analyzer.analyze_with_strands(
                    cluster_data=cluster_data,
                    user_prompt=request.analysis_request
                ),
                timeout=30.0  # 30 second timeout for AWS Strands
            )
            
            logger.info("✅ AWS Strands analysis completed successfully!")
            
            # Only include cluster summary for cluster-wide requests
            response_data = {
                "analysis_id": f"strands-{datetime.utcnow().isoformat()}",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "scope": request.scope,
                "namespace": request.target,
                "analysis": result
            }
            
            # Add cluster summary only for cluster-wide analysis or when explicitly requested
            if (request.scope == "cluster" or 
                "cluster" in request.analysis_request.lower() or 
                "summary" in request.analysis_request.lower()):
                response_data["cluster_summary"] = {
                    "total_pods": len(cluster_data.pods),
                    "total_services": len(cluster_data.services),
                    "total_events": len(cluster_data.events)
                }
            
            return response_data
            
        except Exception as e:
            logger.error(f"AWS Strands analysis failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"AWS Strands analysis failed: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/stream/events")
async def stream_events(request: Request):
    """Server-Sent Events stream for real-time monitoring."""
    if not strands_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    sse_handler = strands_agent.get_sse_handler()
    if not sse_handler:
        raise HTTPException(status_code=503, detail="Streaming not available")
    
    async def event_stream():
        try:
            monitoring_stream = MonitoringSSEStream(sse_handler)
            async for event in monitoring_stream.start_streaming():
                yield event
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring."""
    if not strands_agent:
        await websocket.close(code=1011, reason="Agent not initialized")
        return
    
    websocket_manager = strands_agent.get_websocket_manager()
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket not available")
        return
    
    client_id = None
    try:
        # Connect client
        client_id = await websocket_manager.connect(websocket)
        
        # Handle messages
        while True:
            try:
                message = await websocket.receive_text()
                await websocket_manager.handle_client_message(client_id, message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if client_id:
            await websocket_manager.disconnect(client_id)

@app.get("/namespaces")
async def list_namespaces():
    """List all Kubernetes namespaces."""
    if not strands_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Use the data collector to get namespace information
        cluster_data = await strands_agent.data_collector.collect_cluster_data(include_logs=False)
        
        # Extract unique namespaces from pods and services
        namespaces = set()
        for pod in cluster_data.pods:
            if pod.namespace:
                namespaces.add(pod.namespace)
        for service in cluster_data.services:
            if service.namespace:
                namespaces.add(service.namespace)
        
        return {
            "namespaces": sorted(list(namespaces)),
            "count": len(namespaces),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictions")
async def get_predictions():
    """Get current predictive analytics insights."""
    if not strands_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Check if event loop is available and has predictive capabilities
        if not hasattr(strands_agent, 'event_loop') or not strands_agent.event_loop:
            return {
                "status": "unavailable",
                "message": "Event loop not initialized - predictions require continuous monitoring",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get prediction summary from event loop
        prediction_summary = strands_agent.event_loop.get_prediction_summary()
        
        # Add metadata
        prediction_summary["timestamp"] = datetime.utcnow().isoformat()
        prediction_summary["data_points"] = len(strands_agent.event_loop.cluster_snapshots)
        prediction_summary["monitoring_duration"] = (
            f"{len(strands_agent.event_loop.cluster_snapshots) * strands_agent.event_loop.monitoring_interval // 60} minutes"
            if strands_agent.event_loop.cluster_snapshots else "0 minutes"
        )
        
        return prediction_summary
        
    except Exception as e:
        logger.error(f"Failed to get predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictions/detailed")
async def get_detailed_predictions():
    """Get detailed predictive analytics with full prediction objects."""
    if not strands_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        if not hasattr(strands_agent, 'event_loop') or not strands_agent.event_loop:
            return {
                "status": "unavailable",
                "message": "Event loop not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get recent predictions from the predictive analyzer
        recent_predictions = []
        if hasattr(strands_agent.event_loop, 'predictive_analyzer'):
            # Get predictions from the last 24 hours
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            recent_predictions = [
                {
                    "id": p.prediction_id,
                    "type": p.prediction_type,
                    "description": p.description,
                    "confidence": p.confidence,
                    "severity": p.severity,
                    "time_frame": p.time_frame,
                    "probability": p.probability,
                    "impact_assessment": p.impact_assessment,
                    "recommended_actions": p.recommended_actions,
                    "based_on_metrics": p.based_on_metrics,
                    "created_at": p.created_at.isoformat()
                }
                for p in strands_agent.event_loop.predictive_analyzer.prediction_history
                if p.created_at >= cutoff_time
            ]
        
        return {
            "status": "active" if recent_predictions else "no_recent_predictions",
            "predictions": recent_predictions,
            "total_predictions": len(recent_predictions),
            "data_points_available": len(strands_agent.event_loop.cluster_snapshots),
            "prediction_capabilities": [
                "resource_exhaustion",
                "pod_failure_prediction",
                "performance_degradation",
                "capacity_planning",
                "anomaly_detection"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get detailed predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
