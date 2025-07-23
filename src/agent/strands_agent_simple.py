"""
AWS Strands Kubernetes monitoring agent following official deployment patterns.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import the actual Strands agent implementation
from src.strands_k8s_agent import StrandsKubernetesAgent

from src.k8s.collector import DataCollector

logger = logging.getLogger(__name__)


class KubernetesMonitoringAgent:
    """AWS Strands monitoring agent with real-time capabilities."""

    def __init__(self, data_collector: DataCollector, strands_config=None, aws_config=None):
        """Initialize the Kubernetes monitoring agent."""
        self.data_collector = data_collector
        self.strands_config = strands_config or {}
        self.aws_config = aws_config
        
        # Use the actual Strands agent implementation
        self.real_agent = StrandsKubernetesAgent(
            enable_event_loop=False,  # Disable event loop for this use case
            enable_streaming=not self.disable_streaming
        )
        
        # Get streaming configuration
        self.disable_streaming = True  # Default to disabled for Bedrock compatibility
        if self.aws_config:
            agent_config = self.aws_config.get_strands_config()
            self.disable_streaming = agent_config.get("disable_streaming", True)
            self.fallback_model = agent_config.get("fallback_model", "amazon.titan-text-express-v1")
        else:
            self.fallback_model = "amazon.titan-text-express-v1"
        
        logger.info("Initialized Kubernetes Monitoring Agent with Real Strands implementation")

    async def analyze_cluster(self, namespace: Optional[str] = None, analysis_request: Optional[str] = None, include_logs: bool = False, **kwargs) -> Dict[str, Any]:
        """Analyze the cluster using the Strands Kubernetes agent."""
        try:
            # Use the trigger_manual_analysis method from StrandsKubernetesAgent
            result = await self.real_agent.trigger_manual_analysis(
                scope="cluster" if not namespace else "namespace",
                namespace=namespace,
                analysis_request=analysis_request
            )
            
            if result.get("status") == "completed":
                # Extract the analysis content
                analysis_content = result.get("analysis", {})
                
                # Handle both AI analysis and fallback responses
                if isinstance(analysis_content, dict) and "message" in analysis_content:
                    # This is a fallback response
                    analysis_text = analysis_content["message"]["content"][0]["text"]
                elif isinstance(analysis_content, str):
                    # This is a direct AI analysis
                    analysis_text = analysis_content
                else:
                    # Handle other formats
                    analysis_text = str(analysis_content)
                
                return {
                    "analysis_id": result.get("analysis_id", str(uuid.uuid4())),
                    "status": "completed",
                    "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                    "analysis": analysis_text,
                    "tool_calls": [],  # StrandsKubernetesAgent doesn't expose tool calls directly
                    "findings": self._extract_findings(analysis_text),
                    "recommendations": self._extract_recommendations(analysis_text),
                    "summary": self._create_summary(analysis_text),
                    "cluster_summary": result.get("cluster_summary", {}),
                    "fallback_used": result.get("fallback_used", False)
                }
            else:
                return {
                    "analysis_id": result.get("analysis_id", str(uuid.uuid4())),
                    "status": "failed",
                    "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                    "error": result.get("error", "Unknown error"),
                    "analysis": "Analysis failed due to technical issues",
                    "tool_calls": [],
                    "findings": [],
                    "recommendations": ["Check agent configuration and AWS permissions"],
                    "summary": f"Analysis failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            logger.error(f"Error during cluster analysis: {str(e)}")
            analysis_id = str(uuid.uuid4())
            return {
                "analysis_id": analysis_id,
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "analysis": "Analysis failed due to unexpected error",
                "tool_calls": [],
                "findings": [],
                "recommendations": ["Check agent logs for detailed error information"],
                "summary": f"Analysis failed: {str(e)}"
            }

    def _extract_findings(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Extract findings from the analysis text."""
        findings = []
        
        # Simple keyword-based extraction (can be enhanced with NLP)
        if "error" in analysis_text.lower() or "failed" in analysis_text.lower():
            findings.append({
                "type": "error",
                "resource": "cluster",
                "message": "Errors detected in cluster analysis",
                "severity": "high"
            })
        
        if "warning" in analysis_text.lower() or "issue" in analysis_text.lower():
            findings.append({
                "type": "warning",
                "resource": "cluster",
                "message": "Warnings or issues detected",
                "severity": "medium"
            })
        
        if "healthy" in analysis_text.lower() or "normal" in analysis_text.lower():
            findings.append({
                "type": "info",
                "resource": "cluster",
                "message": "Cluster appears healthy",
                "severity": "low"
            })
        
        return findings

    def _extract_recommendations(self, analysis_text: str) -> List[str]:
        """Extract recommendations from the analysis text."""
        recommendations = []
        
        # Look for recommendation patterns
        lines = analysis_text.split('\n')
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['recommend', 'should', 'consider', 'suggest']):
                if line and not line.startswith('#'):
                    recommendations.append(line)
        
        # Default recommendations if none found
        if not recommendations:
            recommendations = [
                "Monitor cluster resources regularly",
                "Check pod logs for any errors",
                "Verify service connectivity"
            ]
        
        return recommendations[:5]  # Limit to 5 recommendations

    def _create_summary(self, analysis_text: str) -> str:
        """Create a summary of the analysis."""
        # Simple summary creation (can be enhanced)
        word_count = len(analysis_text.split())
        
        if "error" in analysis_text.lower():
            return f"Analysis completed with errors detected. Review the {word_count} word analysis for details."
        elif "warning" in analysis_text.lower():
            return f"Analysis completed with warnings. Review the {word_count} word analysis for recommendations."
        else:
            return f"Analysis completed successfully. Generated {word_count} word comprehensive analysis."

    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the monitoring agent."""
        try:
            # Check if the real agent components are healthy
            k8s_healthy = self.real_agent.k8s_client is not None
            data_collector_healthy = self.real_agent.data_collector is not None
            strands_healthy = self.real_agent.strands_agent is not None
            
            # Get event loop status if available
            event_loop_status = {}
            try:
                event_loop_status = self.real_agent.get_event_loop_status()
            except:
                event_loop_status = {"status": "not_available"}
            
            return {
                "healthy": k8s_healthy and data_collector_healthy and strands_healthy,
                "components": {
                    "kubernetes_api": k8s_healthy,
                    "data_collector": data_collector_healthy,
                    "strands_agent": strands_healthy,
                    "tools_registered": 3,  # Approximate number of tools
                    "model": self.fallback_model,
                    "region": "us-east-1",  # Default region
                    "strands_available": strands_healthy,
                    "event_loop": event_loop_status
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": "0.2.0"
            }
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                "healthy": False,
                "components": {
                    "kubernetes_api": False,
                    "data_collector": False,
                    "strands_agent": False,
                    "tools_registered": 0,
                    "model": "unknown",
                    "region": "unknown",
                    "strands_available": False
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": "0.2.0",
                "error": str(e)
            }

    async def stream_analysis(self, prompt: str, namespace: Optional[str] = None, include_logs: bool = False):
        """Stream analysis results (for compatibility)."""
        # For now, return the full analysis as a single chunk
        # This can be enhanced to provide real streaming
        result = await self.analyze_cluster(analysis_request=prompt, namespace=namespace, include_logs=include_logs)
        
        # Yield the result as a streaming response
        yield f"data: {json.dumps(result)}\n\n"

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the agent."""
        return self.get_health_status()

    async def get_cluster_data(self, namespace: Optional[str] = None, include_logs: bool = False) -> Dict[str, Any]:
        """Get cluster data using the data collector."""
        try:
            # Use the data collector from the real agent
            if self.real_agent.data_collector:
                cluster_data = await self.real_agent.data_collector.collect_cluster_data(
                    namespace=namespace,
                    include_logs=include_logs
                )
                
                # Convert ClusterData object to dictionary format
                return {
                    "status": "success",
                    "data": {
                        "pods": [pod.to_dict() if hasattr(pod, 'to_dict') else pod for pod in cluster_data.pods],
                        "services": [svc.to_dict() if hasattr(svc, 'to_dict') else svc for svc in cluster_data.services],
                        "events": [evt.to_dict() if hasattr(evt, 'to_dict') else evt for evt in cluster_data.events],
                        "logs": cluster_data.logs if hasattr(cluster_data, 'logs') else []
                    }
                }
            else:
                return {
                    "status": "error",
                    "error": "Data collector not available",
                    "data": {}
                }
        except Exception as e:
            logger.error(f"Error getting cluster data: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "data": {}
            }
