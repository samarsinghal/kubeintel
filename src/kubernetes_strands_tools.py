"""
Kubernetes tools for AWS Strands integration.

This module provides Strands tools for accessing and analyzing Kubernetes resources
using the @tool decorator from AWS Strands directly.
"""

import logging
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from strands import tool
from src.k8s.client import KubernetesClient, KubernetesClientError
from src.observability.error_handler import with_error_handling, log_tool_invocation, with_logging
import time
import traceback

# Configure logging
logger = structlog.get_logger(__name__)


class KubernetesToolsProvider:
    """
    Provider class for Kubernetes tools using AWS Strands.
    
    This class initializes the Kubernetes client and provides access to
    cluster data for the Strands tools.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Kubernetes tools provider.
        
        Args:
            config: Configuration dictionary for Kubernetes client.
        """
        self.config = config
        
        # Initialize Kubernetes client
        config_type = config.get("config_type", "in-cluster")
        kubeconfig_path = config.get("kubeconfig_path")
        self.k8s_client = KubernetesClient(config_type=config_type, kubeconfig_path=kubeconfig_path)
        
        logger.info("KubernetesToolsProvider initialized")


# Global instance for tools to use
_k8s_provider = None


def initialize_kubernetes_tools(config: Dict[str, Any]):
    """Initialize the global Kubernetes tools provider."""
    global _k8s_provider
    _k8s_provider = KubernetesToolsProvider(config)


# =============================================================================
# DATA ACCESS TOOLS
# =============================================================================

@tool
@with_logging("get_pods")
@with_error_handling("get_pods")
def get_pods(namespace: Optional[str] = None, label_selector: Optional[str] = None, 
            field_selector: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieve current pod information from Kubernetes cluster.
    
    Args:
        namespace: Optional namespace to filter pods. If None, includes all namespaces.
        label_selector: Optional label selector to filter pods (format: "key1=value1,key2=value2").
        field_selector: Optional field selector for filtering (format: "status.phase=Running").
        limit: Optional maximum number of pods to return.
        
    Returns:
        Dictionary containing pod information and metadata.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Validate inputs
        if namespace is not None and not isinstance(namespace, str):
            return {"error": "namespace must be a string"}
        
        if label_selector is not None and not isinstance(label_selector, str):
            return {"error": "label_selector must be a string"}
            
        if field_selector is not None and not isinstance(field_selector, str):
            return {"error": "field_selector must be a string"}
            
        if limit is not None:
            try:
                limit = int(limit)
                if limit <= 0:
                    return {"error": "limit must be a positive integer"}
            except (ValueError, TypeError):
                return {"error": "limit must be a valid integer"}
        
        # Get pods from Kubernetes
        pods_data = _k8s_provider.k8s_client.get_pods(
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector
        )
        
        # Apply limit if specified
        if limit and len(pods_data) > limit:
            pods_data = pods_data[:limit]
        
        # Format response
        return {
            "status": "success",
            "pods": pods_data,
            "count": len(pods_data),
            "namespace": namespace or "all",
            "filters": {
                "label_selector": label_selector,
                "field_selector": field_selector,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except KubernetesClientError as e:
        logger.error(f"Kubernetes client error in get_pods: {e}")
        return {
            "error": f"Kubernetes API error: {str(e)}",
            "error_type": "KubernetesClientError",
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_pods: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
@with_logging("get_services")
@with_error_handling("get_services")
def get_services(namespace: Optional[str] = None, label_selector: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve current service information from Kubernetes cluster.
    
    Args:
        namespace: Optional namespace to filter services. If None, includes all namespaces.
        label_selector: Optional label selector to filter services.
        
    Returns:
        Dictionary containing service information and metadata.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Get services from Kubernetes
        services_data = _k8s_provider.k8s_client.get_services(
            namespace=namespace,
            label_selector=label_selector
        )
        
        return {
            "status": "success",
            "services": services_data,
            "count": len(services_data),
            "namespace": namespace or "all",
            "timestamp": datetime.now().isoformat()
        }
        
    except KubernetesClientError as e:
        logger.error(f"Kubernetes client error in get_services: {e}")
        return {
            "error": f"Kubernetes API error: {str(e)}",
            "error_type": "KubernetesClientError",
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_services: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
@with_error_handling("get_deployments")
def get_deployments(namespace: Optional[str] = None, label_selector: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve current deployment information from Kubernetes cluster.
    
    Args:
        namespace: Optional namespace to filter deployments. If None, includes all namespaces.
        label_selector: Optional label selector to filter deployments.
        
    Returns:
        Dictionary containing deployment information and metadata.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Get deployments from Kubernetes
        deployments_data = _k8s_provider.k8s_client.get_deployments(
            namespace=namespace,
            label_selector=label_selector
        )
        
        return {
            "status": "success",
            "deployments": deployments_data,
            "count": len(deployments_data),
            "namespace": namespace or "all",
            "timestamp": datetime.now().isoformat()
        }
        
    except KubernetesClientError as e:
        logger.error(f"Kubernetes client error in get_deployments: {e}")
        return {
            "error": f"Kubernetes API error: {str(e)}",
            "error_type": "KubernetesClientError",
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_deployments: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
@with_error_handling("kubectl_get")
def kubectl_get(resource_type: str, name: Optional[str] = None, namespace: Optional[str] = None, 
               all_namespaces: bool = False, output_format: str = "summary") -> Dict[str, Any]:
    """
    Execute kubectl get equivalent commands for various Kubernetes resources.
    
    Args:
        resource_type: Type of resource (pods, services, deployments, events, nodes, etc.).
        name: Optional specific resource name to get.
        namespace: Optional namespace to filter resources.
        all_namespaces: If True, get resources from all namespaces.
        output_format: Output format (summary, detailed, yaml-like).
        
    Returns:
        Dictionary containing resource information similar to kubectl get output.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Validate resource type
        supported_resources = ["pods", "services", "deployments", "events", "nodes", "namespaces"]
        if resource_type.lower() not in supported_resources:
            return {
                "error": f"Unsupported resource type: {resource_type}",
                "supported_types": supported_resources
            }
        
        resource_type = resource_type.lower()
        
        # Handle different resource types
        if resource_type == "pods":
            if name:
                # Get specific pod
                pods = _k8s_provider.k8s_client.list_pods(namespace=namespace)
                pod = next((p for p in pods if p.get("name") == name), None)
                if not pod:
                    return {"error": f"Pod '{name}' not found in namespace '{namespace}'"}
                return {
                    "status": "success",
                    "resource_type": "pod",
                    "resource": pod,
                    "kubectl_equivalent": f"kubectl get pod {name} -n {namespace or 'default'}"
                }
            else:
                # List pods
                pods = _k8s_provider.k8s_client.list_pods(
                    namespace=None if all_namespaces else namespace
                )
                return {
                    "status": "success",
                    "resource_type": "pods",
                    "count": len(pods),
                    "resources": pods,
                    "kubectl_equivalent": "kubectl get pods --all-namespaces" if all_namespaces else f"kubectl get pods -n {namespace or 'default'}"
                }
                
        elif resource_type == "services":
            services = _k8s_provider.k8s_client.list_services(
                namespace=None if all_namespaces else namespace
            )
            if name:
                service = next((s for s in services if s.get("name") == name), None)
                if not service:
                    return {"error": f"Service '{name}' not found"}
                return {
                    "status": "success",
                    "resource_type": "service",
                    "resource": service,
                    "kubectl_equivalent": f"kubectl get service {name} -n {namespace or 'default'}"
                }
            return {
                "status": "success",
                "resource_type": "services",
                "count": len(services),
                "resources": services,
                "kubectl_equivalent": "kubectl get services --all-namespaces" if all_namespaces else f"kubectl get services -n {namespace or 'default'}"
            }
            
        elif resource_type == "deployments":
            deployments = _k8s_provider.k8s_client.list_deployments(
                namespace=None if all_namespaces else namespace
            )
            if name:
                deployment = next((d for d in deployments if d.get("name") == name), None)
                if not deployment:
                    return {"error": f"Deployment '{name}' not found"}
                return {
                    "status": "success",
                    "resource_type": "deployment", 
                    "resource": deployment,
                    "kubectl_equivalent": f"kubectl get deployment {name} -n {namespace or 'default'}"
                }
            return {
                "status": "success",
                "resource_type": "deployments",
                "count": len(deployments),
                "resources": deployments,
                "kubectl_equivalent": "kubectl get deployments --all-namespaces" if all_namespaces else f"kubectl get deployments -n {namespace or 'default'}"
            }
            
        elif resource_type == "events":
            events = _k8s_provider.k8s_client.list_events(
                namespace=None if all_namespaces else namespace
            )
            return {
                "status": "success",
                "resource_type": "events",
                "count": len(events),
                "resources": events,
                "kubectl_equivalent": "kubectl get events --all-namespaces" if all_namespaces else f"kubectl get events -n {namespace or 'default'}"
            }
            
        else:
            return {"error": f"Resource type '{resource_type}' not yet implemented"}
            
    except Exception as e:
        logger.error(f"Error in kubectl_get: {e}")
        return {
            "error": f"kubectl get failed: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
@with_error_handling("get_pod_logs")
def get_pod_logs(pod_name: str, namespace: str, lines: Optional[int] = 100, container: Optional[str] = None) -> Dict[str, Any]:
    """
    Get logs from a specific pod.
    
    Args:
        pod_name: Name of the pod to get logs from.
        namespace: Namespace of the pod.
        lines: Number of recent log lines to retrieve (default: 100).
        container: Optional container name for multi-container pods.
        
    Returns:
        Dictionary containing pod logs and metadata.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Validate inputs
        if not pod_name or not isinstance(pod_name, str):
            return {"error": "pod_name must be a non-empty string"}
            
        if not namespace or not isinstance(namespace, str):
            return {"error": "namespace must be a non-empty string"}
            
        if lines is not None:
            try:
                lines = int(lines)
                if lines <= 0:
                    return {"error": "lines must be a positive integer"}
            except (ValueError, TypeError):
                return {"error": "lines must be a valid integer"}
        
        # Get pod logs using the client
        log_lines = _k8s_provider.k8s_client.get_pod_logs(
            pod_name=pod_name,
            namespace=namespace,
            lines=lines or 100
        )
        
        return {
            "status": "success",
            "pod_name": pod_name,
            "namespace": namespace,
            "lines_requested": lines or 100,
            "lines_returned": len(log_lines),
            "logs": log_lines,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting pod logs: {e}")
        return {
            "error": f"Failed to get pod logs: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
@with_error_handling("get_events")
def get_events(namespace: Optional[str] = None, limit: Optional[int] = 50) -> Dict[str, Any]:
    """
    Retrieve recent events from Kubernetes cluster.
    
    Args:
        namespace: Optional namespace to filter events. If None, includes all namespaces.
        limit: Maximum number of events to return (default: 50).
        
    Returns:
        Dictionary containing event information and metadata.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Get events from Kubernetes
        events_data = _k8s_provider.k8s_client.get_events(
            namespace=namespace,
            limit=limit
        )
        
        return {
            "status": "success",
            "events": events_data,
            "count": len(events_data),
            "namespace": namespace or "all",
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except KubernetesClientError as e:
        logger.error(f"Kubernetes client error in get_events: {e}")
        return {
            "error": f"Kubernetes API error: {str(e)}",
            "error_type": "KubernetesClientError",
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Unexpected error in get_events: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


# =============================================================================
# ANALYSIS TOOLS
# =============================================================================

@tool
@with_error_handling("analyze_pod_health")
def analyze_pod_health(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze the health of pods in the cluster.
    
    Args:
        namespace: Optional namespace to analyze. If None, analyzes all namespaces.
        
    Returns:
        Dictionary containing pod health analysis and recommendations.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Get pods data
        pods_result = get_pods(namespace=namespace)
        if pods_result.get("status") != "success":
            return pods_result
            
        pods = pods_result["pods"]
        
        # Analyze pod health
        healthy_pods = []
        unhealthy_pods = []
        pending_pods = []
        
        for pod in pods:
            status = pod.get("status", {})
            phase = status.get("phase", "Unknown")
            
            if phase == "Running":
                # Check if all containers are ready
                container_statuses = status.get("containerStatuses", [])
                all_ready = all(cs.get("ready", False) for cs in container_statuses)
                
                if all_ready:
                    healthy_pods.append(pod)
                else:
                    unhealthy_pods.append(pod)
            elif phase == "Pending":
                pending_pods.append(pod)
            else:
                unhealthy_pods.append(pod)
        
        # Generate recommendations
        recommendations = []
        if unhealthy_pods:
            recommendations.append("Investigate unhealthy pods for container issues or resource constraints")
        if pending_pods:
            recommendations.append("Check pending pods for scheduling issues or resource availability")
        
        return {
            "status": "success",
            "analysis": {
                "total_pods": len(pods),
                "healthy_pods": len(healthy_pods),
                "unhealthy_pods": len(unhealthy_pods),
                "pending_pods": len(pending_pods),
                "health_percentage": (len(healthy_pods) / len(pods) * 100) if pods else 0
            },
            "unhealthy_pods": [{"name": p["metadata"]["name"], "namespace": p["metadata"]["namespace"], 
                              "phase": p["status"].get("phase")} for p in unhealthy_pods],
            "pending_pods": [{"name": p["metadata"]["name"], "namespace": p["metadata"]["namespace"]} 
                           for p in pending_pods],
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_pod_health: {e}")
        return {
            "error": f"Analysis error: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
@with_error_handling("generate_cluster_summary")
def generate_cluster_summary() -> Dict[str, Any]:
    """
    Generate a comprehensive summary of the cluster state.
    
    Returns:
        Dictionary containing cluster summary and key metrics.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        # Get all resource types
        pods_result = get_pods()
        services_result = get_services()
        deployments_result = get_deployments()
        events_result = get_events(limit=20)
        
        # Check for errors
        if any(result.get("status") != "success" for result in [pods_result, services_result, deployments_result, events_result]):
            return {"error": "Failed to retrieve cluster data"}
        
        # Analyze pods by namespace
        pods = pods_result["pods"]
        namespaces = {}
        for pod in pods:
            ns = pod["metadata"]["namespace"]
            if ns not in namespaces:
                namespaces[ns] = {"pods": 0, "running": 0, "pending": 0, "failed": 0}
            namespaces[ns]["pods"] += 1
            phase = pod["status"].get("phase", "Unknown")
            if phase == "Running":
                namespaces[ns]["running"] += 1
            elif phase == "Pending":
                namespaces[ns]["pending"] += 1
            elif phase in ["Failed", "Error"]:
                namespaces[ns]["failed"] += 1
        
        # Recent events analysis
        events = events_result["events"]
        warning_events = [e for e in events if e.get("type") == "Warning"]
        
        return {
            "status": "success",
            "cluster_summary": {
                "total_pods": len(pods),
                "total_services": len(services_result["services"]),
                "total_deployments": len(deployments_result["deployments"]),
                "total_namespaces": len(namespaces),
                "recent_warning_events": len(warning_events)
            },
            "namespaces": namespaces,
            "recent_warnings": [{"reason": e.get("reason"), "message": e.get("message")} 
                              for e in warning_events[:5]],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in generate_cluster_summary: {e}")
        return {
            "error": f"Summary generation error: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
def check_cluster_security() -> Dict[str, Any]:
    """
    Perform basic security analysis of the Kubernetes cluster.
    
    Returns:
        Dictionary containing security analysis results and recommendations.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        security_findings = {
            "timestamp": datetime.now().isoformat(),
            "security_issues": [],
            "recommendations": [],
            "severity_counts": {"high": 0, "medium": 0, "low": 0}
        }
        
        # Get pods and check for security issues
        pods_data = _k8s_provider.k8s_client.get_pods()
        
        for pod in pods_data:
            pod_name = pod.get('metadata', {}).get('name', 'unknown')
            namespace = pod.get('metadata', {}).get('namespace', 'default')
            
            # Check for privileged containers
            spec = pod.get('spec', {})
            containers = spec.get('containers', [])
            
            for container in containers:
                security_context = container.get('securityContext', {})
                
                # Check for privileged mode
                if security_context.get('privileged', False):
                    security_findings["security_issues"].append({
                        "type": "privileged_container",
                        "severity": "high",
                        "resource": f"pod/{pod_name}",
                        "namespace": namespace,
                        "message": f"Container {container.get('name')} is running in privileged mode"
                    })
                    security_findings["severity_counts"]["high"] += 1
                
                # Check for root user
                if security_context.get('runAsUser') == 0:
                    security_findings["security_issues"].append({
                        "type": "root_user",
                        "severity": "medium",
                        "resource": f"pod/{pod_name}",
                        "namespace": namespace,
                        "message": f"Container {container.get('name')} is running as root user"
                    })
                    security_findings["severity_counts"]["medium"] += 1
        
        # Generate recommendations
        if security_findings["severity_counts"]["high"] > 0:
            security_findings["recommendations"].append("Review and remove privileged containers where possible")
        if security_findings["severity_counts"]["medium"] > 0:
            security_findings["recommendations"].append("Consider using non-root users for containers")
        
        return {
            "status": "success",
            "security_analysis": security_findings
        }
        
    except Exception as e:
        logger.error(f"Error in check_cluster_security: {e}")
        return {
            "error": f"Security analysis failed: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
def identify_resource_bottlenecks() -> Dict[str, Any]:
    """
    Identify potential resource bottlenecks in the cluster.
    
    Returns:
        Dictionary containing bottleneck analysis and recommendations.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
            
        bottleneck_analysis = {
            "timestamp": datetime.now().isoformat(),
            "bottlenecks": [],
            "recommendations": [],
            "resource_pressure": {}
        }
        
        # Get nodes and pods data
        nodes_data = _k8s_provider.k8s_client.get_nodes()
        pods_data = _k8s_provider.k8s_client.get_pods()
        
        # Analyze node resource pressure
        for node in nodes_data:
            node_name = node.get('metadata', {}).get('name', 'unknown')
            conditions = node.get('status', {}).get('conditions', [])
            
            for condition in conditions:
                condition_type = condition.get('type')
                status = condition.get('status')
                
                if condition_type in ['MemoryPressure', 'DiskPressure', 'PIDPressure'] and status == 'True':
                    bottleneck_analysis["bottlenecks"].append({
                        "type": "node_pressure",
                        "severity": "high",
                        "resource": f"node/{node_name}",
                        "message": f"Node experiencing {condition_type}",
                        "condition": condition_type
                    })
        
        # Analyze pending pods (potential resource constraints)
        pending_pods = [pod for pod in pods_data if pod.get('status', {}).get('phase') == 'Pending']
        
        if pending_pods:
            bottleneck_analysis["bottlenecks"].append({
                "type": "pending_pods",
                "severity": "medium",
                "count": len(pending_pods),
                "message": f"{len(pending_pods)} pods are pending - possible resource constraints"
            })
            bottleneck_analysis["recommendations"].append("Check cluster capacity and consider scaling nodes")
        
        # Generate recommendations based on findings
        if any(b["type"] == "node_pressure" for b in bottleneck_analysis["bottlenecks"]):
            bottleneck_analysis["recommendations"].append("Monitor node resource usage and consider adding capacity")
        
        return {
            "status": "success",
            "bottleneck_analysis": bottleneck_analysis
        }
        
    except Exception as e:
        logger.error(f"Error in identify_resource_bottlenecks: {e}")
        return {
            "error": f"Bottleneck analysis failed: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
def format_kubernetes_resources(resources: Dict[str, Any], format_type: str = "summary") -> Dict[str, Any]:
    """
    Format Kubernetes resources for better readability and analysis.
    
    Args:
        resources: Dictionary containing Kubernetes resources data
        format_type: Type of formatting ("summary", "detailed", "table")
        
    Returns:
        Dictionary containing formatted resource information.
    """
    try:
        formatted_output = {
            "timestamp": datetime.now().isoformat(),
            "format_type": format_type,
            "formatted_data": {}
        }
        
        if format_type == "summary":
            # Create summary format
            if "pods" in resources:
                pods = resources["pods"]
                pod_summary = {
                    "total": len(pods),
                    "by_status": {},
                    "by_namespace": {}
                }
                
                for pod in pods:
                    status = pod.get('status', {}).get('phase', 'Unknown')
                    namespace = pod.get('metadata', {}).get('namespace', 'default')
                    
                    pod_summary["by_status"][status] = pod_summary["by_status"].get(status, 0) + 1
                    pod_summary["by_namespace"][namespace] = pod_summary["by_namespace"].get(namespace, 0) + 1
                
                formatted_output["formatted_data"]["pods"] = pod_summary
        
        elif format_type == "table":
            # Create table format (simplified)
            if "pods" in resources:
                pods = resources["pods"]
                table_data = []
                
                for pod in pods:
                    table_data.append({
                        "name": pod.get('metadata', {}).get('name', 'unknown'),
                        "namespace": pod.get('metadata', {}).get('namespace', 'default'),
                        "status": pod.get('status', {}).get('phase', 'Unknown'),
                        "ready": len([c for c in pod.get('status', {}).get('containerStatuses', []) if c.get('ready', False)])
                    })
                
                formatted_output["formatted_data"]["pods_table"] = table_data
        
        return {
            "status": "success",
            "formatted_output": formatted_output
        }
        
    except Exception as e:
        logger.error(f"Error in format_kubernetes_resources: {e}")
        return {
            "error": f"Resource formatting failed: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
def validate_kubernetes_manifest(manifest_yaml: str) -> Dict[str, Any]:
    """
    Validate a Kubernetes manifest for common issues and best practices.
    
    Args:
        manifest_yaml: YAML string containing the Kubernetes manifest
        
    Returns:
        Dictionary containing validation results and recommendations.
    """
    try:
        import yaml
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "is_valid": True,
            "issues": [],
            "recommendations": [],
            "warnings": []
        }
        
        # Parse YAML
        try:
            manifest = yaml.safe_load(manifest_yaml)
        except yaml.YAMLError as e:
            validation_results["is_valid"] = False
            validation_results["issues"].append(f"Invalid YAML syntax: {str(e)}")
            return {"status": "success", "validation": validation_results}
        
        # Basic validation checks
        if not isinstance(manifest, dict):
            validation_results["is_valid"] = False
            validation_results["issues"].append("Manifest must be a valid Kubernetes object")
            return {"status": "success", "validation": validation_results}
        
        # Check required fields
        required_fields = ['apiVersion', 'kind', 'metadata']
        for field in required_fields:
            if field not in manifest:
                validation_results["is_valid"] = False
                validation_results["issues"].append(f"Missing required field: {field}")
        
        # Check metadata
        metadata = manifest.get('metadata', {})
        if not metadata.get('name'):
            validation_results["is_valid"] = False
            validation_results["issues"].append("Missing metadata.name")
        
        # Pod-specific validations
        if manifest.get('kind') == 'Pod':
            spec = manifest.get('spec', {})
            containers = spec.get('containers', [])
            
            if not containers:
                validation_results["is_valid"] = False
                validation_results["issues"].append("Pod must have at least one container")
            
            for container in containers:
                if not container.get('image'):
                    validation_results["issues"].append(f"Container {container.get('name', 'unnamed')} missing image")
                
                # Security recommendations
                security_context = container.get('securityContext', {})
                if security_context.get('privileged'):
                    validation_results["warnings"].append(f"Container {container.get('name')} runs in privileged mode")
                
                if not security_context.get('runAsNonRoot'):
                    validation_results["recommendations"].append(f"Consider setting runAsNonRoot for container {container.get('name')}")
        
        return {
            "status": "success",
            "validation": validation_results
        }
        
    except Exception as e:
        logger.error(f"Error in validate_kubernetes_manifest: {e}")
        return {
            "error": f"Manifest validation failed: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }


@tool
def summarize_events(namespace: Optional[str] = None, event_types: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
    """
    Summarize and analyze Kubernetes events for patterns and issues.
    
    Args:
        namespace: Optional namespace to filter events
        event_types: Optional list of event types to include (e.g., ["Warning", "Normal"])
        limit: Maximum number of events to analyze
        
    Returns:
        Dictionary containing event summary and analysis.
    """
    try:
        if not _k8s_provider:
            return {"error": "Kubernetes tools not initialized"}
        
        # Get events
        events_data = _k8s_provider.k8s_client.get_events(namespace=namespace, limit=limit)
        
        # Filter by event types if specified
        if event_types:
            events_data = [e for e in events_data if e.get('type') in event_types]
        
        event_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_events": len(events_data),
            "event_counts": {},
            "frequent_reasons": {},
            "recent_warnings": [],
            "patterns": []
        }
        
        # Analyze event types
        for event in events_data:
            event_type = event.get('type', 'Unknown')
            reason = event.get('reason', 'Unknown')
            
            event_summary["event_counts"][event_type] = event_summary["event_counts"].get(event_type, 0) + 1
            event_summary["frequent_reasons"][reason] = event_summary["frequent_reasons"].get(reason, 0) + 1
            
            # Collect recent warnings
            if event_type == 'Warning' and len(event_summary["recent_warnings"]) < 10:
                event_summary["recent_warnings"].append({
                    "reason": reason,
                    "message": event.get('message', ''),
                    "object": event.get('involvedObject', {}).get('name', 'unknown'),
                    "timestamp": event.get('firstTimestamp', '')
                })
        
        # Identify patterns
        warning_count = event_summary["event_counts"].get('Warning', 0)
        if warning_count > 10:
            event_summary["patterns"].append(f"High number of warning events: {warning_count}")
        
        # Most frequent issues
        most_frequent = sorted(event_summary["frequent_reasons"].items(), key=lambda x: x[1], reverse=True)[:5]
        event_summary["most_frequent_issues"] = [{"reason": reason, "count": count} for reason, count in most_frequent]
        
        return {
            "status": "success",
            "event_summary": event_summary
        }
        
    except Exception as e:
        logger.error(f"Error in summarize_events: {e}")
        return {
            "error": f"Event summarization failed: {str(e)}",
            "error_type": type(e).__name__,
            "status": "error"
        }
    def _get_fallback_data(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Get fallback data for a tool when the primary execution fails.
        
        This method attempts to provide fallback data from cache or other sources
        when the primary tool execution fails.
        
        Args:
            tool_name: Name of the tool that failed.
            params: Parameters that were passed to the tool.
            
        Returns:
            Fallback data if available, None otherwise.
        """
        try:
            from src.observability.error_handler import FallbackMechanism
            
            # Log the fallback attempt
            logger.info(f"Attempting to get fallback data for tool {tool_name}", params=str(params))
            
            # Check if we have cached data for this tool and parameters
            # In a real implementation, you would check a cache here
            
            # For demonstration purposes, provide some minimal fallback data for certain tools
            if tool_name == "get_pods":
                namespace = params.get("namespace", "default")
                return {
                    "status": "fallback",
                    "message": "Using fallback data for pods",
                    "pods": [
                        {
                            "name": "fallback-pod-1",
                            "namespace": namespace,
                            "status": "Unknown",
                            "ready": False,
                            "restart_count": 0,
                            "node_name": "unknown",
                            "containers": [],
                            "labels": {},
                            "annotations": {},
                            "fallback_data": True
                        }
                    ]
                }
            elif tool_name == "get_deployments":
                namespace = params.get("namespace", "default")
                return {
                    "status": "fallback",
                    "message": "Using fallback data for deployments",
                    "deployments": [
                        {
                            "name": "fallback-deployment-1",
                            "namespace": namespace,
                            "replicas": 0,
                            "ready_replicas": 0,
                            "available_replicas": 0,
                            "updated_replicas": 0,
                            "unavailable_replicas": 0,
                            "strategy": "Unknown",
                            "selector": {},
                            "labels": {},
                            "annotations": {},
                            "fallback_data": True
                        }
                    ]
                }
            elif tool_name == "get_services":
                namespace = params.get("namespace", "default")
                return {
                    "status": "fallback",
                    "message": "Using fallback data for services",
                    "services": [
                        {
                            "name": "fallback-service-1",
                            "namespace": namespace,
                            "type": "ClusterIP",
                            "cluster_ip": "None",
                            "ports": [],
                            "selector": {},
                            "labels": {},
                            "fallback_data": True
                        }
                    ]
                }
            elif tool_name == "get_events":
                namespace = params.get("namespace", "default")
                return {
                    "status": "fallback",
                    "message": "Using fallback data for events",
                    "events": [
                        {
                            "name": "fallback-event-1",
                            "namespace": namespace,
                            "type": "Warning",
                            "reason": "FallbackData",
                            "message": "Using fallback data due to API error",
                            "involved_object": {
                                "kind": "Pod",
                                "name": "fallback-pod-1",
                                "namespace": namespace
                            },
                            "first_timestamp": "unknown",
                            "last_timestamp": "unknown",
                            "count": 1,
                            "fallback_data": True
                        }
                    ]
                }
            elif tool_name == "analyze_cluster_health":
                # Use the FallbackMechanism for cluster analysis
                return FallbackMechanism.get_fallback_analysis({
                    "tool": tool_name,
                    "params": str(params),
                    "timestamp": datetime.now().isoformat()
                })
            elif tool_name == "get_cluster_info":
                # Use the FallbackMechanism for basic cluster info
                return FallbackMechanism.get_basic_cluster_info()
            
            # No fallback data available for this tool
            return None
            
        except Exception as e:
            # Don't let fallback failures affect the tool execution
            logger.warning(f"Failed to get fallback data for tool {tool_name}: {str(e)}")
            return None