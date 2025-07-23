"""
AWS Strands analyzer optimized for VPC endpoint connectivity.
"""
import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from botocore.config import Config
import boto3

logger = logging.getLogger(__name__)

class StrandsVPCAnalyzer:
    """AWS Strands analyzer with VPC endpoint optimization."""
    
    def __init__(self):
        """Initialize Strands agent with VPC endpoint configuration."""
        self.strands_agent = None
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Configure for VPC endpoints
        bedrock_config = {
            'region_name': self.aws_region,
            'retries': {'max_attempts': 3, 'mode': 'adaptive'},
            'read_timeout': 60,
            'connect_timeout': 30,
            'max_pool_connections': 10
        }
        
        # VPC endpoints work automatically with proper DNS resolution
        if os.getenv('AWS_USE_VPC_ENDPOINTS', 'false').lower() == 'true':
            endpoint_url = os.getenv('AWS_BEDROCK_ENDPOINT_URL')
            if endpoint_url:
                logger.info(f"🔗 Using VPC endpoint: {endpoint_url}")
                # VPC endpoints are used automatically via DNS resolution
                # No need to set endpoint_url in Config
        
        self.bedrock_config = Config(**bedrock_config)
        
        self._initialize_strands_agent()
    
    def _initialize_strands_agent(self):
        """Initialize AWS Strands agent with VPC endpoint support."""
        try:
            from strands import Agent
            # Note: Tool import may not be available in this Strands version
            
            # Create Bedrock client with VPC endpoint configuration
            bedrock_runtime = boto3.client('bedrock-runtime', config=self.bedrock_config)
            
            # Initialize Strands agent with minimal configuration
            self.strands_agent = Agent(
                name="kubernetes-cluster-analyzer",
                # Use Claude Haiku - more reliable and faster
                model=os.getenv('AGENT_STRANDS_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')
            )
            
            logger.info(f"✅ Strands agent initialized with model: {os.getenv('AGENT_STRANDS_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0')}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Strands agent: {e}")
            self.strands_agent = None
    
    def _register_kubernetes_tools(self):
        """Register Kubernetes analysis tools with Strands."""
        if not self.strands_agent:
            return
        
        try:
            from strands.tools import Tool
            
            # Tool for analyzing pod health
            @Tool
            def analyze_pod_health(pods_data: str) -> str:
                """Analyze Kubernetes pod health status."""
                try:
                    pods = json.loads(pods_data) if isinstance(pods_data, str) else pods_data
                    
                    status_counts = {}
                    unhealthy_pods = []
                    
                    for pod in pods:
                        status = pod.get('status', {}).get('phase', 'Unknown')
                        status_counts[status] = status_counts.get(status, 0) + 1
                        
                        if status not in ['Running', 'Succeeded']:
                            pod_name = pod.get('metadata', {}).get('name', 'unknown')
                            namespace = pod.get('metadata', {}).get('namespace', 'default')
                            unhealthy_pods.append(f"{namespace}/{pod_name}: {status}")
                    
                    result = f"Pod Status Summary: {json.dumps(status_counts)}\n"
                    if unhealthy_pods:
                        result += f"Unhealthy Pods ({len(unhealthy_pods)}):\n" + "\n".join(unhealthy_pods[:10])
                    
                    return result
                except Exception as e:
                    return f"Error analyzing pods: {e}"
            
            # Tool for analyzing cluster events
            @Tool
            def analyze_cluster_events(events_data: str) -> str:
                """Analyze Kubernetes cluster events."""
                try:
                    events = json.loads(events_data) if isinstance(events_data, str) else events_data
                    
                    warning_events = []
                    error_events = []
                    
                    for event in events[:20]:  # Limit to recent events
                        event_type = event.get('type', 'Normal')
                        reason = event.get('reason', 'Unknown')
                        message = event.get('message', '')[:150]
                        
                        if event_type == 'Warning':
                            warning_events.append(f"{reason}: {message}")
                        elif event_type == 'Error':
                            error_events.append(f"{reason}: {message}")
                    
                    result = f"Event Analysis:\n"
                    result += f"Warning Events: {len(warning_events)}\n"
                    result += f"Error Events: {len(error_events)}\n"
                    
                    if warning_events:
                        result += "Recent Warnings:\n" + "\n".join(warning_events[:5])
                    
                    return result
                except Exception as e:
                    return f"Error analyzing events: {e}"
            
            # Tool for service analysis
            @Tool
            def analyze_services(services_data: str) -> str:
                """Analyze Kubernetes services."""
                try:
                    services = json.loads(services_data) if isinstance(services_data, str) else services_data
                    
                    service_types = {}
                    external_services = []
                    
                    for service in services:
                        svc_type = service.get('spec', {}).get('type', 'ClusterIP')
                        service_types[svc_type] = service_types.get(svc_type, 0) + 1
                        
                        if svc_type in ['LoadBalancer', 'NodePort']:
                            name = service.get('metadata', {}).get('name', 'unknown')
                            namespace = service.get('metadata', {}).get('namespace', 'default')
                            external_services.append(f"{namespace}/{name} ({svc_type})")
                    
                    result = f"Service Analysis:\n"
                    result += f"Service Types: {json.dumps(service_types)}\n"
                    if external_services:
                        result += f"External Services: {', '.join(external_services)}"
                    
                    return result
                except Exception as e:
                    return f"Error analyzing services: {e}"
            
            logger.info("✅ Kubernetes analysis tools registered with Strands")
            
        except Exception as e:
            logger.warning(f"Failed to register Kubernetes tools: {e}")
    
    async def analyze_with_strands(self, cluster_data, user_prompt: str) -> Dict[str, Any]:
        """Perform analysis using AWS Strands with VPC endpoint support."""
        
        if not self.strands_agent:
            raise Exception("Strands agent not initialized")
        
        logger.info("🤖 Starting AWS Strands analysis with VPC endpoints")
        
        # Create simple analysis prompt for Strands
        analysis_prompt = self._create_simple_strands_prompt(cluster_data, user_prompt)
        
        try:
            # Use Strands agent with increased timeout
            result = await asyncio.wait_for(
                self._invoke_strands_agent(analysis_prompt),
                timeout=60.0  # Increased to 60 seconds for AWS Strands
            )
            
            logger.info("✅ AWS Strands analysis completed successfully")
            
            return {
                "message": {
                    "role": "assistant",
                    "content": [{"text": result}]
                },
                "method": "aws_strands",
                "model_used": os.getenv('AGENT_STRANDS_MODEL', 'anthropic.claude-3-haiku-20240307-v1:0'),
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except asyncio.TimeoutError:
            error_msg = "AWS Strands analysis timed out - check network connectivity and model availability"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"AWS Strands analysis failed: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            # Log full traceback for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Also log the exception details
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception args: {e.args}")
            raise Exception(error_msg)
    
    def _create_simple_strands_prompt(self, cluster_data, user_prompt: str) -> str:
        """Create analysis prompt that instructs Claude to use tools for real data."""
        
        # Import the proper system prompt that instructs Claude to use tools
        from .strands_k8s_agent import KUBERNETES_MONITORING_SYSTEM_PROMPT
        
        # Create a prompt that tells Claude to use tools instead of providing pre-processed data
        prompt = f"""{KUBERNETES_MONITORING_SYSTEM_PROMPT}

USER REQUEST: {user_prompt}

INSTRUCTIONS:
1. Use your available tools to get REAL cluster data
2. Analyze the actual results from the tools  
3. Provide specific insights based on the real data you retrieve

Remember: You have tools available - USE THEM to get actual data instead of making assumptions."""
        
        return prompt

    async def _invoke_strands_agent(self, prompt: str) -> str:
        """Invoke the Strands agent with the given prompt."""
        if not self.strands_agent:
            raise Exception("Strands agent not initialized")
            
        try:
            logger.info("🤖 Invoking AWS Strands agent...")
            
            # Try async invoke first (preferred for Claude)
            if hasattr(self.strands_agent, 'invoke_async'):
                logger.info("📞 Using async invoke method")
                response = await asyncio.wait_for(
                    self.strands_agent.invoke_async(prompt),
                    timeout=45.0
                )
            else:
                logger.info("📞 Using sync invoke method in executor")
                # Fallback to sync method in executor
                def call_agent():
                    return self.strands_agent(prompt)
                
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, call_agent),
                    timeout=45.0
                )
            
            logger.info(f"✅ Strands response received: {type(response)}")
            
            # Handle different response formats
            if isinstance(response, str):
                logger.info(f"📝 Response content length: {len(response)}")
                return response
            elif isinstance(response, dict):
                content = response.get('content', str(response))
                logger.info(f"📝 Response content length: {len(content)}")
                return content
            elif hasattr(response, 'content'):
                logger.info(f"📝 Response content length: {len(response.content)}")
                return response.content
            else:
                content = str(response)
                logger.info(f"📝 Response string length: {len(content)}")
                return content
                
        except asyncio.TimeoutError:
            error_msg = "❌ Strands agent call timed out after 45 seconds - check model availability and network connectivity"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"❌ Strands agent invocation failed: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
            raise Exception(f"Strands invocation error: {str(e)}")
    
    def _get_kubernetes_system_prompt(self) -> str:
        """Get system prompt for Kubernetes analysis."""
        return """You are an expert Kubernetes cluster analyst with deep knowledge of:

- Pod lifecycle management and troubleshooting
- Service networking and load balancing
- Resource management and optimization
- Event analysis and root cause identification
- Security best practices
- Performance monitoring and alerting

Your role is to:
1. Analyze cluster health comprehensively
2. Identify issues with specific resource names
3. Provide actionable kubectl commands
4. Recommend monitoring and optimization strategies
5. Prioritize issues by severity and impact

Always provide practical, implementable solutions with clear next steps."""
