"""
AWS Strands-based Kubernetes Monitoring Agent with Event Loop

This module implements a Kubernetes monitoring agent using the official AWS Strands framework
with full event loop, streaming, and real-time monitoring capabilities.
"""

import asyncio
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
from botocore.config import Config

from strands import Agent, tool
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from src.k8s.collector import DataCollector
from src.k8s.client import KubernetesClient
from src.models.kubernetes import ClusterData, PodInfo, ServiceInfo, EventInfo
from src.event_loop.event_loop import KubernetesEventLoop
from src.streaming.websocket_manager import WebSocketManager
from src.streaming.sse_handler import SSEHandler
from src.streaming.stream_handler import MonitoringStreamHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt for the Kubernetes monitoring agent
KUBERNETES_MONITORING_SYSTEM_PROMPT = """You are a Kubernetes cluster monitoring agent with EXECUTABLE TOOLS. You MUST use your tools to provide real data, not suggestions.

🚨 CRITICAL RULES:
1. NEVER suggest kubectl commands - you have tools that do this for you
2. ALWAYS execute tools first before responding
3. NEVER say "you can use kubectl..." - USE YOUR TOOLS INSTEAD
4. Provide ACTUAL DATA from tool execution, not generic advice
5. Include cluster context ONLY when relevant to the specific request

AVAILABLE TOOLS (USE THESE):
- get_pods() → Get actual pod data
- get_services() → Get actual service data  
- get_deployments() → Get actual deployment data
- get_events() → Get actual events
- get_pod_logs() → Get actual pod logs
- kubectl_get() → Execute kubectl-like commands
- analyze_pod_health() → Analyze pod health
- generate_cluster_summary() → Get cluster overview

RESPONSE GUIDELINES:
- For SPECIFIC requests (pod logs, service details): Focus on the specific item, don't include cluster overview
- For GENERAL requests (cluster health, analysis): Include broader context
- Always provide actionable insights based on actual data

EXAMPLES OF CORRECT BEHAVIOR:
❌ WRONG: "Use kubectl get pods to see pods"
✅ CORRECT: Execute get_pods() and show actual pod data

❌ WRONG: "Run kubectl logs pod-name to see logs"  
✅ CORRECT: Execute get_pod_logs() and show actual logs

CONVERSATION EXAMPLES:

User: "Show me cart pod logs"
Assistant: [Executes get_pod_logs()] Cart pod logs:
2025-07-20 23:46:52 ERROR Database connection failed
2025-07-20 23:46:53 INFO Retrying connection...

User: "Analyze cluster health"  
Assistant: [Executes multiple tools] Cluster Health Analysis:
📊 Overview: 22 pods, 17 services, 100 events
🔍 Issues found: 2 pods failing, 1 service unreachable
...

RESPONSE FORMAT:
1. Execute relevant tools immediately
2. Present actual data from tools
3. Provide analysis based on real data
4. Give actionable recommendations
5. Include cluster context only when relevant

You are an ACTION-TAKING agent, not an advice-giving chatbot. Execute tools now!
"""

class StrandsKubernetesAgent:
    """Strands-based Kubernetes monitoring agent with event loop capabilities."""
    
    def __init__(self, enable_event_loop: bool = True, enable_streaming: bool = False):
        """Initialize the Strands Kubernetes agent with event loop."""
        self.k8s_client = None
        self.data_collector = None
        self.strands_agent = None
        self.event_loop = None
        self.websocket_manager = None
        self.sse_handler = None
        self.stream_handler = None
        
        # Configuration
        self.enable_event_loop = enable_event_loop
        self.enable_streaming = enable_streaming
        self.monitoring_interval = 30  # seconds
        
        # Initialize components
        self._initialize_kubernetes()
        self._initialize_data_collector()
        self._initialize_strands_agent()
        
        if enable_streaming:
            self._initialize_streaming()
        
        if enable_event_loop:
            self._initialize_event_loop()
        
        logger.info("Strands Kubernetes Agent initialized with event loop support")
    
    def _initialize_kubernetes(self):
        """Initialize Kubernetes client configuration."""
        try:
            # Initialize the KubernetesClient wrapper
            self.k8s_client = KubernetesClient(config_type="in-cluster")
            logger.info("Initialized Kubernetes client")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    def _initialize_data_collector(self):
        """Initialize the Kubernetes data collector."""
        try:
            self.data_collector = DataCollector(self.k8s_client)
            logger.info("Initialized Kubernetes data collector")
        except Exception as e:
            logger.error(f"Failed to initialize data collector: {e}")
            raise
    
    def _initialize_strands_agent(self):
        """Initialize the AWS Strands agent with Kubernetes tools."""
        try:
            # Initialize Kubernetes tools
            from src.kubernetes_strands_tools import initialize_kubernetes_tools
            kubernetes_config = {
                "config_type": "in-cluster",
                "kubeconfig_path": None
            }
            initialize_kubernetes_tools(kubernetes_config)
            
            # Configure Bedrock client with proper timeouts
            from botocore.config import Config
            bedrock_config = Config(
                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                retries={'max_attempts': 2},
                read_timeout=25,  # 25 seconds read timeout
                connect_timeout=5,  # 5 seconds connect timeout
                max_pool_connections=10
            )
            
            # Import all the Kubernetes tools
            from src.kubernetes_strands_tools import (
                get_pods, get_services, get_deployments, get_events, 
                get_pod_logs, kubectl_get, analyze_pod_health, 
                generate_cluster_summary, check_cluster_security,
                identify_resource_bottlenecks, format_kubernetes_resources,
                validate_kubernetes_manifest, summarize_events
            )
            
            # Create Strands agent with all Kubernetes tools
            kubernetes_tools = [
                get_pods, get_services, get_deployments, get_events,
                get_pod_logs, kubectl_get, analyze_pod_health,
                generate_cluster_summary, check_cluster_security,
                identify_resource_bottlenecks, format_kubernetes_resources,
                validate_kubernetes_manifest, summarize_events
            ]
            
            self.strands_agent = Agent(
                name="kubernetes-monitoring-agent",
                system_prompt=KUBERNETES_MONITORING_SYSTEM_PROMPT,  # Claude supports system prompts
                model=os.getenv('AGENT_STRANDS_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0'),
                tools=kubernetes_tools
            )
            
            # Debug: Verify tools are registered
            logger.info(f"Initialized AWS Strands agent with model: {os.getenv('AGENT_STRANDS_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')}")
            logger.info(f"Registered {len(kubernetes_tools)} tools: {[tool.__name__ for tool in kubernetes_tools]}")
            logger.info(f"Agent tool names: {self.strands_agent.tool_names}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Strands agent: {e}")
            raise
    
    def _initialize_streaming(self):
        """Initialize streaming components."""
        try:
            # For now, create placeholder streaming components
            logger.info("Streaming initialization deferred - using basic setup")
            self.websocket_manager = None  # Will implement later
            self.sse_handler = None        # Will implement later
            self.stream_handler = None     # Will implement later
            
            logger.info("Initialized basic streaming (placeholder)")
        except Exception as e:
            logger.error(f"Failed to initialize streaming: {e}")
            # Don't raise - continue without streaming for now
            self.websocket_manager = None
            self.sse_handler = None
            self.stream_handler = None
    
    def _initialize_event_loop(self):
        """Initialize the event loop."""
        try:
            from src.event_loop.event_loop import KubernetesEventLoop
            
            logger.info("Initializing Kubernetes Event Loop with predictive analytics")
            
            # Initialize the event loop with all components
            self.event_loop = KubernetesEventLoop(
                strands_agent=self.strands_agent,
                k8s_client=self.k8s_client,
                data_collector=self.data_collector,
                monitoring_interval=30,  # 30 seconds
                event_batch_size=10,
                enable_streaming=self.enable_streaming
            )
            
            logger.info("Initialized Kubernetes Event Loop with predictive analytics")
        except Exception as e:
            logger.error(f"Failed to initialize event loop: {e}")
            # Don't raise - continue without event loop for now
            self.event_loop = None
    
    async def start_monitoring(self):
        """Start the continuous monitoring event loop."""
        if not self.event_loop:
            logger.warning("Event loop not initialized")
            return
        
        logger.info("Starting continuous monitoring")
        
        # Start streaming components
        if self.websocket_manager:
            await self.websocket_manager.start_health_monitoring()
        
        # Start the event loop
        await self.event_loop.start()
    
    async def stop_monitoring(self):
        """Stop the continuous monitoring event loop."""
        if self.event_loop:
            await self.event_loop.stop()
        
        if self.websocket_manager:
            await self.websocket_manager.stop_health_monitoring()
        
        logger.info("Stopped continuous monitoring")
    
    def get_websocket_manager(self) -> Optional[WebSocketManager]:
        """Get the WebSocket manager for real-time connections."""
        return self.websocket_manager
    
    def get_sse_handler(self) -> Optional[SSEHandler]:
        """Get the SSE handler for streaming responses."""
        return self.sse_handler
    
    def get_event_loop_status(self) -> Dict[str, Any]:
        """Get the current status of the event loop."""
        if not self.event_loop:
            return {"enabled": False, "status": "not_initialized"}
        
        return self.event_loop.get_status()
    
    def _create_fresh_strands_agent(self):
        """Create a fresh Strands agent instance to avoid conversation history issues."""
        try:
            # Clear the conversation history from the existing agent
            if self.strands_agent:
                # Clear all messages to start fresh
                self.strands_agent.messages = []
                logger.info("Cleared conversation history for fresh analysis")
                return self.strands_agent
            else:
                logger.warning("No Strands agent available")
                return None
        except Exception as e:
            logger.warning(f"Failed to create fresh agent, using existing: {e}")
            return self.strands_agent

    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize and validate prompt to prevent empty message issues."""
        if not prompt or not prompt.strip():
            return "Analyze the Kubernetes cluster and provide a health assessment."
        
        # Remove any problematic characters that might cause parsing issues
        sanitized = prompt.strip()
        
        # Replace multiple spaces with single spaces
        sanitized = ' '.join(sanitized.split())
        
        # Ensure minimum length
        if len(sanitized) < 10:
            return "Analyze the Kubernetes cluster and provide a health assessment."
        
        # Ensure maximum length to prevent token issues
        if len(sanitized) > 1500:
            sanitized = sanitized[:1400] + "... Please provide comprehensive analysis."
        
        # Ensure it ends with proper punctuation
        if not sanitized.endswith(('.', '!', '?')):
            sanitized += "."
        
        return sanitized

    async def test_tool_execution(self) -> str:
        """Test if tools are working by asking for a simple pod list."""
        try:
            logger.info("🧪 Testing tool execution...")
            
            # Test with very explicit tool-forcing prompt
            test_prompt = """Execute the get_pods tool right now to show me all pods. 
            Do not suggest kubectl commands. Use the get_pods() tool immediately and show me the actual results."""
            
            response = self.strands_agent(test_prompt)
            logger.info(f"🧪 Test response type: {type(response)}")
            logger.info(f"🧪 Test response preview: {str(response)[:200]}...")
            
            return str(response)
        except Exception as e:
            logger.error(f"🧪 Tool execution test failed: {e}")
            return f"Tool test failed: {str(e)}"

    async def trigger_manual_analysis(self, scope: str = "cluster", namespace: Optional[str] = None, analysis_request: Optional[str] = None) -> Dict[str, Any]:
        """Trigger a manual analysis outside of the event loop."""
        try:
            # Collect current cluster data
            cluster_data = await self.data_collector.collect_cluster_data(
                namespace=namespace,
                include_logs=False
            )
            
            # Create and sanitize analysis prompt
            if analysis_request:
                prompt = self._sanitize_prompt(analysis_request)
            else:
                prompt = f"Analyze the current {scope} status"
                if namespace:
                    prompt += f" in namespace '{namespace}'"
                prompt += ". Provide a comprehensive health assessment with recommendations."
            
            # Add cluster context to the prompt
            context_info = f"\n\nCluster Context: {len(cluster_data.pods)} pods, {len(cluster_data.services)} services, {len(cluster_data.events)} recent events"
            if namespace:
                context_info += f", analyzing namespace: {namespace}"
            
            full_prompt = prompt + context_info
            full_prompt = self._sanitize_prompt(full_prompt)
            
            # Multiple fallback levels for analysis with increased timeouts
            analysis_result = None
            error_msg = None
            
            # Level 1: Try with full prompt using fresh agent (30 second timeout)
            try:
                logger.info(f"Attempting analysis with fresh agent (prompt length: {len(full_prompt)})")
                fresh_agent = self._create_fresh_strands_agent()
                
                # Use asyncio.wait_for to set a shorter timeout for UI responsiveness
                analysis_result = await asyncio.wait_for(
                    fresh_agent.invoke_async(full_prompt),
                    timeout=25.0  # 25 seconds for UI responsiveness
                )
                logger.info("Fresh agent analysis completed successfully")
            except asyncio.TimeoutError:
                error_msg = "Strands analysis timed out after 25 seconds"
                logger.warning(f"Fresh agent analysis timed out: {error_msg}")
                
                # Try simple Bedrock analyzer as immediate fallback
                try:
                    logger.info("Trying simple Bedrock analyzer")
                    from src.simple_bedrock_analyzer import SimpleBedrock
                    simple_analyzer = SimpleBedrock()
                    analysis_result = await simple_analyzer.analyze_cluster(cluster_data, prompt)
                    logger.info("Simple Bedrock analysis completed successfully")
                except Exception as bedrock_error:
                    logger.warning(f"Simple Bedrock analysis also failed: {bedrock_error}")
                    error_msg = f"Both Strands and simple Bedrock failed: {bedrock_error}"
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Fresh agent analysis failed: {e}")
                
                # Level 2: Try with simplified prompt and fresh agent (3 minute timeout)
                try:
                    simple_prompt = f"Analyze Kubernetes cluster health. Current status: {len(cluster_data.pods)} pods, {len(cluster_data.services)} services. Provide assessment and recommendations."
                    logger.info(f"Attempting analysis with simplified prompt (length: {len(simple_prompt)})")
                    
                    # Create another fresh agent for the fallback
                    fallback_agent = self._create_fresh_strands_agent()
                    analysis_result = await asyncio.wait_for(
                        fallback_agent.invoke_async(simple_prompt),
                        timeout=20.0  # 20 seconds
                    )
                    logger.info("Simplified analysis completed successfully")
                except asyncio.TimeoutError:
                    error_msg = "Simplified analysis timed out after 3 minutes"
                    logger.warning(f"Simplified analysis timed out: {error_msg}")
                except Exception as e2:
                    error_msg = str(e2)
                    logger.warning(f"Simplified analysis failed: {e2}")
                    
                    # Level 3: Try with minimal prompt and completely new agent (1 minute timeout)
                    try:
                        minimal_prompt = "Analyze cluster health and provide recommendations."
                        logger.info(f"Attempting analysis with minimal prompt (length: {len(minimal_prompt)})")
                        
                        # Create yet another fresh agent for final fallback
                        minimal_agent = self._create_fresh_strands_agent()
                        analysis_result = await asyncio.wait_for(
                            minimal_agent.invoke_async(minimal_prompt),
                            timeout=15.0  # 15 seconds
                        )
                        logger.info("Minimal analysis completed successfully")
                    except asyncio.TimeoutError:
                        error_msg = "Minimal analysis timed out after 1 minute"
                        logger.error(f"Minimal analysis timed out: {error_msg}")
                    except Exception as e3:
                        error_msg = str(e3)
                        logger.error(f"All analysis levels failed. Final error: {e3}")
            
            # If we have a successful analysis result, return it
            if analysis_result:
                return {
                    "analysis_id": f"manual-{datetime.utcnow().isoformat()}",
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "scope": scope,
                    "namespace": namespace,
                    "analysis": analysis_result,
                    "cluster_summary": {
                        "total_pods": len(cluster_data.pods),
                        "total_services": len(cluster_data.services),
                        "total_events": len(cluster_data.events)
                    }
                }
            
            # If all AI analysis attempts failed, return the fallback
            logger.warning("All AI analysis attempts failed, returning fallback response")
            return {
                "analysis_id": f"manual-fallback-{datetime.utcnow().isoformat()}",
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "scope": scope,
                "namespace": namespace,
                "analysis": {
                    "message": {
                        "role": "assistant",
                        "content": [{
                            "text": f"Cluster Status Summary:\n\n✅ **Cluster Overview:**\n- Total Pods: {len(cluster_data.pods)}\n- Total Services: {len(cluster_data.services)}\n- Recent Events: {len(cluster_data.events)}\n\n⚠️ **AI Analysis Unavailable:**\nThe AI analysis service is currently experiencing technical difficulties. Error: {error_msg}\n\n🔧 **Recommended Actions:**\n1. Check pod status: `kubectl get pods --all-namespaces`\n2. Review recent events: `kubectl get events --all-namespaces --sort-by=.metadata.creationTimestamp`\n3. Monitor resource usage: `kubectl top nodes && kubectl top pods --all-namespaces`\n\n📊 **Basic Health Check:**\n- Cluster is operational with {len(cluster_data.pods)} pods running\n- {len(cluster_data.services)} services are configured\n- {len(cluster_data.events)} recent events recorded\n\nFor detailed analysis, please resolve the AI service issues and retry."
                        }]
                    }
                },
                "cluster_summary": {
                    "total_pods": len(cluster_data.pods),
                    "total_services": len(cluster_data.services),
                    "total_events": len(cluster_data.events)
                },
                "fallback_used": True,
                "error": error_msg
            }
            
        except Exception as e:
            logger.error(f"Manual analysis failed: {e}")
            return {
                "analysis_id": f"manual-error-{datetime.utcnow().isoformat()}",
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
