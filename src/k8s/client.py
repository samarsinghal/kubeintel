"""Kubernetes API client wrapper for the monitoring agent."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import structlog
import json

logger = structlog.get_logger(__name__)


class KubernetesClientError(Exception):
    """Base exception for Kubernetes client errors."""
    pass


class KubernetesClient:
    """Wrapper for Kubernetes API client with error handling and convenience methods."""
    
    def __init__(self, config_type: str = "in-cluster", kubeconfig_path: Optional[str] = None):
        """
        Initialize Kubernetes client.
        
        Args:
            config_type: Type of configuration ("in-cluster" or "kubeconfig")
            kubeconfig_path: Path to kubeconfig file (if config_type is "kubeconfig")
        """
        self.config_type = config_type
        self.kubeconfig_path = kubeconfig_path
        self._core_v1 = None
        self._apps_v1 = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the Kubernetes client based on configuration type."""
        try:
            if self.config_type == "in-cluster":
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            else:
                config.load_kube_config(config_file=self.kubeconfig_path)
                logger.info("Loaded kubeconfig", path=self.kubeconfig_path)
            
            self._core_v1 = client.CoreV1Api()
            self._apps_v1 = client.AppsV1Api()
            
        except Exception as e:
            logger.error("Failed to initialize Kubernetes client", error=str(e))
            raise KubernetesClientError(f"Failed to initialize Kubernetes client: {e}")
    
    def list_pods(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List pods in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter pods (None for all namespaces)
            
        Returns:
            List of pod information dictionaries
        """
        try:
            if namespace:
                pods = self._core_v1.list_namespaced_pod(namespace=namespace)
            else:
                pods = self._core_v1.list_pod_for_all_namespaces()
            
            pod_list = []
            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "ready": self._is_pod_ready(pod),
                    "restart_count": self._get_restart_count(pod),
                    "created_at": pod.metadata.creation_timestamp,
                    "node_name": pod.spec.node_name,
                    "containers": self._extract_container_info(pod),
                    "labels": pod.metadata.labels or {},
                    "annotations": pod.metadata.annotations or {}
                }
                pod_list.append(pod_info)
            
            logger.info("Listed pods", count=len(pod_list), namespace=namespace)
            return pod_list
            
        except ApiException as e:
            logger.error("Failed to list pods", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list pods: {e}")
    
    def list_services(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List services in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter services (None for all namespaces)
            
        Returns:
            List of service information dictionaries
        """
        try:
            if namespace:
                services = self._core_v1.list_namespaced_service(namespace=namespace)
            else:
                services = self._core_v1.list_service_for_all_namespaces()
            
            service_list = []
            for service in services.items:
                service_info = {
                    "name": service.metadata.name,
                    "namespace": service.metadata.namespace,
                    "type": service.spec.type,
                    "cluster_ip": service.spec.cluster_ip,
                    "ports": self._extract_service_ports(service),
                    "selector": service.spec.selector or {},
                    "labels": service.metadata.labels or {},
                    "created_at": service.metadata.creation_timestamp
                }
                service_list.append(service_info)
            
            logger.info("Listed services", count=len(service_list), namespace=namespace)
            return service_list
            
        except ApiException as e:
            logger.error("Failed to list services", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list services: {e}")
            
    def list_deployments(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List deployments in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter deployments (None for all namespaces)
            
        Returns:
            List of deployment information dictionaries
        """
        try:
            if namespace:
                deployments = self._apps_v1.list_namespaced_deployment(namespace=namespace)
            else:
                deployments = self._apps_v1.list_deployment_for_all_namespaces()
            
            deployment_list = []
            for deployment in deployments.items:
                deployment_info = {
                    "name": deployment.metadata.name,
                    "namespace": deployment.metadata.namespace,
                    "replicas": deployment.spec.replicas,
                    "available_replicas": deployment.status.available_replicas or 0,
                    "ready_replicas": deployment.status.ready_replicas or 0,
                    "updated_replicas": deployment.status.updated_replicas or 0,
                    "unavailable_replicas": deployment.status.unavailable_replicas or 0,
                    "strategy": deployment.spec.strategy.type,
                    "selector": deployment.spec.selector.match_labels if deployment.spec.selector else {},
                    "labels": deployment.metadata.labels or {},
                    "annotations": deployment.metadata.annotations or {},
                    "created_at": deployment.metadata.creation_timestamp,
                    "containers": self._extract_deployment_containers(deployment)
                }
                deployment_list.append(deployment_info)
            
            logger.info("Listed deployments", count=len(deployment_list), namespace=namespace)
            return deployment_list
            
        except ApiException as e:
            logger.error("Failed to list deployments", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list deployments: {e}")
    
    def list_events(self, namespace: Optional[str] = None, since_hours: int = 1) -> List[Dict[str, Any]]:
        """
        List recent events in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter events (None for all namespaces)
            since_hours: How many hours back to look for events
            
        Returns:
            List of event information dictionaries
        """
        try:
            if namespace:
                events = self._core_v1.list_namespaced_event(namespace=namespace)
            else:
                events = self._core_v1.list_event_for_all_namespaces()
            
            # Filter events by time
            cutoff_time = datetime.now() - timedelta(hours=since_hours)
            
            event_list = []
            for event in events.items:
                if event.first_timestamp and event.first_timestamp.replace(tzinfo=None) > cutoff_time:
                    event_info = {
                        "name": event.metadata.name,
                        "namespace": event.metadata.namespace,
                        "type": event.type,
                        "reason": event.reason,
                        "message": event.message,
                        "involved_object": {
                            "kind": event.involved_object.kind,
                            "name": event.involved_object.name,
                            "namespace": event.involved_object.namespace
                        },
                        "first_timestamp": event.first_timestamp,
                        "last_timestamp": event.last_timestamp,
                        "count": event.count
                    }
                    event_list.append(event_info)
            
            # Sort by timestamp (most recent first)
            event_list.sort(key=lambda x: x["last_timestamp"] or x["first_timestamp"], reverse=True)
            
            logger.info("Listed events", count=len(event_list), namespace=namespace, since_hours=since_hours)
            return event_list
            
        except ApiException as e:
            logger.error("Failed to list events", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list events: {e}")
    
    def get_pod_logs(self, pod_name: str, namespace: str, lines: int = 100) -> List[str]:
        """
        Get logs from a specific pod.
        
        Args:
            pod_name: Name of the pod
            namespace: Namespace of the pod
            lines: Number of log lines to retrieve
            
        Returns:
            List of log lines
        """
        try:
            # First, try to get logs without specifying container (works for single-container pods)
            log_response = self._core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=lines
            )
            
            log_lines = log_response.split('\n') if log_response else []
            logger.info("Retrieved pod logs", pod=pod_name, namespace=namespace, lines=len(log_lines))
            return log_lines
            
        except ApiException as e:
            if e.status == 400 and "container name must be specified" in str(e):
                # Multi-container pod - get logs from the first container
                try:
                    pod = self._core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                    if pod.spec.containers:
                        container_name = pod.spec.containers[0].name
                        log_response = self._core_v1.read_namespaced_pod_log(
                            name=pod_name,
                            namespace=namespace,
                            container=container_name,
                            tail_lines=lines
                        )
                        log_lines = log_response.split('\n') if log_response else []
                        logger.info("Retrieved pod logs", pod=pod_name, namespace=namespace, 
                                  container=container_name, lines=len(log_lines))
                        return log_lines
                except ApiException as inner_e:
                    logger.warning("Failed to get logs from multi-container pod", 
                                 pod=pod_name, namespace=namespace, error=str(inner_e))
                    return []
            elif e.status == 404:
                logger.warning("Pod not found for logs", pod=pod_name, namespace=namespace)
                return []
            else:
                logger.warning("Failed to get pod logs", error=str(e), pod=pod_name, namespace=namespace)
                return []  # Return empty list instead of raising exception
    
    def health_check(self) -> bool:
        """
        Check if the Kubernetes API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            self._core_v1.get_api_resources()
            logger.info("Kubernetes API health check passed")
            return True
        except Exception as e:
            logger.error("Kubernetes API health check failed", error=str(e))
            return False
    
    def _is_pod_ready(self, pod) -> bool:
        """Check if a pod is ready based on its conditions."""
        if not pod.status.conditions:
            return False
        
        for condition in pod.status.conditions:
            if condition.type == "Ready":
                return condition.status == "True"
        return False
    
    def _get_restart_count(self, pod) -> int:
        """Get the total restart count for all containers in a pod."""
        if not pod.status.container_statuses:
            return 0
        
        return sum(container.restart_count for container in pod.status.container_statuses)
    
    def _extract_container_info(self, pod) -> List[Dict[str, Any]]:
        """Extract container information from a pod."""
        containers = []
        
        if pod.spec.containers:
            for container in pod.spec.containers:
                container_info = {
                    "name": container.name,
                    "image": container.image,
                    "ready": False,
                    "restart_count": 0,
                    "state": "Unknown"
                }
                
                # Get container status if available
                if pod.status.container_statuses:
                    for status in pod.status.container_statuses:
                        if status.name == container.name:
                            container_info["ready"] = status.ready
                            container_info["restart_count"] = status.restart_count
                            if status.state:
                                if status.state.running:
                                    container_info["state"] = "Running"
                                elif status.state.waiting:
                                    container_info["state"] = f"Waiting: {status.state.waiting.reason}"
                                elif status.state.terminated:
                                    container_info["state"] = f"Terminated: {status.state.terminated.reason}"
                            break
                
                containers.append(container_info)
        
        return containers
    
    def _extract_service_ports(self, service) -> List[Dict[str, Any]]:
        """Extract port information from a service."""
        ports = []
        
        if service.spec.ports:
            for port in service.spec.ports:
                port_info = {
                    "name": port.name,
                    "port": port.port,
                    "target_port": port.target_port,
                    "protocol": port.protocol,
                    "node_port": port.node_port
                }
                ports.append(port_info)
        
        return ports
        
    def _extract_deployment_containers(self, deployment) -> List[Dict[str, Any]]:
        """Extract container information from a deployment."""
        containers = []
        
        if deployment.spec.template.spec.containers:
            for container in deployment.spec.template.spec.containers:
                container_info = {
                    "name": container.name,
                    "image": container.image,
                    "ports": [],
                    "resources": {},
                    "liveness_probe": bool(container.liveness_probe),
                    "readiness_probe": bool(container.readiness_probe)
                }
                
                # Extract container ports
                if container.ports:
                    for port in container.ports:
                        port_info = {
                            "container_port": port.container_port,
                            "protocol": port.protocol,
                            "name": port.name
                        }
                        container_info["ports"].append(port_info)
                
                # Extract resource requirements
                if container.resources:
                    if container.resources.limits:
                        container_info["resources"]["limits"] = {
                            "cpu": container.resources.limits.get("cpu"),
                            "memory": container.resources.limits.get("memory")
                        }
                    
                    if container.resources.requests:
                        container_info["resources"]["requests"] = {
                            "cpu": container.resources.requests.get("cpu"),
                            "memory": container.resources.requests.get("memory")
                        }
                
                containers.append(container_info)
        
        return containers
        
    def get_resource_metrics(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get resource utilization metrics for the cluster or a specific namespace.
        
        Args:
            namespace: Optional namespace to filter metrics. If None, includes all namespaces.
            
        Returns:
            Dictionary containing resource metrics information.
        """
        try:
            # Initialize metrics data structure
            metrics = {
                "nodes": {},
                "pods": {},
                "namespaces": {},
                "cluster_totals": {
                    "cpu": {
                        "capacity": 0,
                        "allocatable": 0,
                        "requests": 0,
                        "limits": 0,
                        "usage": 0
                    },
                    "memory": {
                        "capacity": 0,
                        "allocatable": 0,
                        "requests": 0,
                        "limits": 0,
                        "usage": 0
                    }
                }
            }
            
            # Get nodes information
            try:
                nodes = self._core_v1.list_node()
                for node in nodes.items:
                    node_name = node.metadata.name
                    
                    # Extract capacity and allocatable resources
                    cpu_capacity = self._parse_cpu_value(node.status.capacity.get("cpu", "0"))
                    memory_capacity = self._parse_memory_value(node.status.capacity.get("memory", "0"))
                    cpu_allocatable = self._parse_cpu_value(node.status.allocatable.get("cpu", "0"))
                    memory_allocatable = self._parse_memory_value(node.status.allocatable.get("memory", "0"))
                    
                    # Add to cluster totals
                    metrics["cluster_totals"]["cpu"]["capacity"] += cpu_capacity
                    metrics["cluster_totals"]["memory"]["capacity"] += memory_capacity
                    metrics["cluster_totals"]["cpu"]["allocatable"] += cpu_allocatable
                    metrics["cluster_totals"]["memory"]["allocatable"] += memory_allocatable
                    
                    # Store node metrics
                    metrics["nodes"][node_name] = {
                        "cpu": {
                            "capacity": cpu_capacity,
                            "allocatable": cpu_allocatable,
                            "requests": 0,
                            "limits": 0,
                            "usage": 0
                        },
                        "memory": {
                            "capacity": memory_capacity,
                            "allocatable": memory_allocatable,
                            "requests": 0,
                            "limits": 0,
                            "usage": 0
                        },
                        "conditions": self._extract_node_conditions(node),
                        "pods": []
                    }
            except ApiException as e:
                logger.warning("Failed to get node metrics", error=str(e))
            
            # Get pods information to calculate resource requests and limits
            try:
                if namespace:
                    pods = self._core_v1.list_namespaced_pod(namespace=namespace)
                else:
                    pods = self._core_v1.list_pod_for_all_namespaces()
                
                # Initialize namespace metrics
                namespace_set = set()
                
                for pod in pods.items:
                    pod_namespace = pod.metadata.namespace
                    pod_name = pod.metadata.name
                    node_name = pod.spec.node_name
                    
                    # Add namespace to set
                    namespace_set.add(pod_namespace)
                    
                    # Initialize namespace metrics if not exists
                    if pod_namespace not in metrics["namespaces"]:
                        metrics["namespaces"][pod_namespace] = {
                            "cpu": {
                                "requests": 0,
                                "limits": 0,
                                "usage": 0
                            },
                            "memory": {
                                "requests": 0,
                                "limits": 0,
                                "usage": 0
                            },
                            "pod_count": 0
                        }
                    
                    # Increment pod count for namespace
                    metrics["namespaces"][pod_namespace]["pod_count"] += 1
                    
                    # Initialize pod metrics
                    pod_metrics = {
                        "name": pod_name,
                        "namespace": pod_namespace,
                        "node": node_name,
                        "status": pod.status.phase,
                        "cpu": {
                            "requests": 0,
                            "limits": 0,
                            "usage": 0
                        },
                        "memory": {
                            "requests": 0,
                            "limits": 0,
                            "usage": 0
                        },
                        "containers": []
                    }
                    
                    # Calculate container resource requests and limits
                    for container in pod.spec.containers:
                        container_metrics = {
                            "name": container.name,
                            "cpu": {
                                "requests": 0,
                                "limits": 0,
                                "usage": 0
                            },
                            "memory": {
                                "requests": 0,
                                "limits": 0,
                                "usage": 0
                            }
                        }
                        
                        if container.resources:
                            # CPU requests
                            if container.resources.requests and "cpu" in container.resources.requests:
                                cpu_request = self._parse_cpu_value(container.resources.requests["cpu"])
                                container_metrics["cpu"]["requests"] = cpu_request
                                pod_metrics["cpu"]["requests"] += cpu_request
                                
                                # Add to namespace totals
                                metrics["namespaces"][pod_namespace]["cpu"]["requests"] += cpu_request
                                
                                # Add to cluster totals
                                metrics["cluster_totals"]["cpu"]["requests"] += cpu_request
                                
                                # Add to node totals if pod is assigned to a node
                                if node_name and node_name in metrics["nodes"]:
                                    metrics["nodes"][node_name]["cpu"]["requests"] += cpu_request
                            
                            # CPU limits
                            if container.resources.limits and "cpu" in container.resources.limits:
                                cpu_limit = self._parse_cpu_value(container.resources.limits["cpu"])
                                container_metrics["cpu"]["limits"] = cpu_limit
                                pod_metrics["cpu"]["limits"] += cpu_limit
                                
                                # Add to namespace totals
                                metrics["namespaces"][pod_namespace]["cpu"]["limits"] += cpu_limit
                                
                                # Add to cluster totals
                                metrics["cluster_totals"]["cpu"]["limits"] += cpu_limit
                                
                                # Add to node totals if pod is assigned to a node
                                if node_name and node_name in metrics["nodes"]:
                                    metrics["nodes"][node_name]["cpu"]["limits"] += cpu_limit
                            
                            # Memory requests
                            if container.resources.requests and "memory" in container.resources.requests:
                                memory_request = self._parse_memory_value(container.resources.requests["memory"])
                                container_metrics["memory"]["requests"] = memory_request
                                pod_metrics["memory"]["requests"] += memory_request
                                
                                # Add to namespace totals
                                metrics["namespaces"][pod_namespace]["memory"]["requests"] += memory_request
                                
                                # Add to cluster totals
                                metrics["cluster_totals"]["memory"]["requests"] += memory_request
                                
                                # Add to node totals if pod is assigned to a node
                                if node_name and node_name in metrics["nodes"]:
                                    metrics["nodes"][node_name]["memory"]["requests"] += memory_request
                            
                            # Memory limits
                            if container.resources.limits and "memory" in container.resources.limits:
                                memory_limit = self._parse_memory_value(container.resources.limits["memory"])
                                container_metrics["memory"]["limits"] = memory_limit
                                pod_metrics["memory"]["limits"] += memory_limit
                                
                                # Add to namespace totals
                                metrics["namespaces"][pod_namespace]["memory"]["limits"] += memory_limit
                                
                                # Add to cluster totals
                                metrics["cluster_totals"]["memory"]["limits"] += memory_limit
                                
                                # Add to node totals if pod is assigned to a node
                                if node_name and node_name in metrics["nodes"]:
                                    metrics["nodes"][node_name]["memory"]["limits"] += memory_limit
                        
                        pod_metrics["containers"].append(container_metrics)
                    
                    # Add pod to metrics
                    metrics["pods"][f"{pod_namespace}/{pod_name}"] = pod_metrics
                    
                    # Add pod to node's pod list if assigned to a node
                    if node_name and node_name in metrics["nodes"]:
                        metrics["nodes"][node_name]["pods"].append(f"{pod_namespace}/{pod_name}")
            
            except ApiException as e:
                logger.warning("Failed to get pod metrics", error=str(e))
            
            # Calculate summary metrics
            metrics["summary"] = {
                "node_count": len(metrics["nodes"]),
                "pod_count": len(metrics["pods"]),
                "namespace_count": len(metrics["namespaces"]),
                "cpu_request_percentage": self._calculate_percentage(
                    metrics["cluster_totals"]["cpu"]["requests"],
                    metrics["cluster_totals"]["cpu"]["allocatable"]
                ),
                "memory_request_percentage": self._calculate_percentage(
                    metrics["cluster_totals"]["memory"]["requests"],
                    metrics["cluster_totals"]["memory"]["allocatable"]
                ),
                "cpu_limit_percentage": self._calculate_percentage(
                    metrics["cluster_totals"]["cpu"]["limits"],
                    metrics["cluster_totals"]["cpu"]["allocatable"]
                ),
                "memory_limit_percentage": self._calculate_percentage(
                    metrics["cluster_totals"]["memory"]["limits"],
                    metrics["cluster_totals"]["memory"]["allocatable"]
                )
            }
            
            # Add namespace filter information if provided
            if namespace:
                metrics["namespace_filter"] = namespace
            
            logger.info("Retrieved resource metrics", 
                      node_count=metrics["summary"]["node_count"],
                      pod_count=metrics["summary"]["pod_count"],
                      namespace_count=metrics["summary"]["namespace_count"])
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get resource metrics", error=str(e))
            raise KubernetesClientError(f"Failed to get resource metrics: {e}")
    
    def _parse_cpu_value(self, cpu_str: str) -> float:
        """
        Parse CPU value from Kubernetes resource string.
        
        Args:
            cpu_str: CPU value as string (e.g., "100m", "0.1", "1")
            
        Returns:
            CPU value in cores as float
        """
        if not cpu_str:
            return 0.0
        
        try:
            if cpu_str.endswith("m"):
                return float(cpu_str[:-1]) / 1000.0
            return float(cpu_str)
        except (ValueError, TypeError):
            logger.warning("Failed to parse CPU value", value=cpu_str)
            return 0.0
    
    def _parse_memory_value(self, memory_str: str) -> int:
        """
        Parse memory value from Kubernetes resource string to bytes.
        
        Args:
            memory_str: Memory value as string (e.g., "100Mi", "1Gi")
            
        Returns:
            Memory value in bytes as integer
        """
        if not memory_str:
            return 0
        
        try:
            # Remove binary suffix
            if memory_str.endswith("Ki"):
                return int(float(memory_str[:-2]) * 1024)
            elif memory_str.endswith("Mi"):
                return int(float(memory_str[:-2]) * 1024 * 1024)
            elif memory_str.endswith("Gi"):
                return int(float(memory_str[:-2]) * 1024 * 1024 * 1024)
            elif memory_str.endswith("Ti"):
                return int(float(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024)
            # Remove decimal suffix
            elif memory_str.endswith("K"):
                return int(float(memory_str[:-1]) * 1000)
            elif memory_str.endswith("M"):
                return int(float(memory_str[:-1]) * 1000 * 1000)
            elif memory_str.endswith("G"):
                return int(float(memory_str[:-1]) * 1000 * 1000 * 1000)
            elif memory_str.endswith("T"):
                return int(float(memory_str[:-1]) * 1000 * 1000 * 1000 * 1000)
            # Handle bytes
            elif memory_str.endswith("k"):
                return int(float(memory_str[:-1]) * 1000)
            elif memory_str.endswith("m"):
                return int(float(memory_str[:-1]) * 1000 * 1000)
            elif memory_str.endswith("g"):
                return int(float(memory_str[:-1]) * 1000 * 1000 * 1000)
            elif memory_str.endswith("t"):
                return int(float(memory_str[:-1]) * 1000 * 1000 * 1000 * 1000)
            else:
                return int(float(memory_str))
        except (ValueError, TypeError):
            logger.warning("Failed to parse memory value", value=memory_str)
            return 0
    
    def _calculate_percentage(self, value: float, total: float) -> float:
        """
        Calculate percentage safely.
        
        Args:
            value: The value
            total: The total
            
        Returns:
            Percentage as float (0-100)
        """
        if total == 0:
            return 0.0
        return round((value / total) * 100, 1)
        
    def list_service_accounts(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List service accounts in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter service accounts (None for all namespaces)
            
        Returns:
            List of service account information dictionaries
        """
        try:
            if namespace:
                service_accounts = self._core_v1.list_namespaced_service_account(namespace=namespace)
            else:
                service_accounts = self._core_v1.list_service_account_for_all_namespaces()
            
            sa_list = []
            for sa in service_accounts.items:
                sa_info = {
                    "name": sa.metadata.name,
                    "namespace": sa.metadata.namespace,
                    "secrets": [secret.name for secret in sa.secrets] if sa.secrets else [],
                    "automount_service_account_token": sa.automount_service_account_token,
                    "labels": sa.metadata.labels or {},
                    "annotations": sa.metadata.annotations or {},
                    "created_at": sa.metadata.creation_timestamp
                }
                sa_list.append(sa_info)
            
            logger.info("Listed service accounts", count=len(sa_list), namespace=namespace)
            return sa_list
            
        except ApiException as e:
            logger.error("Failed to list service accounts", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list service accounts: {e}")
    
    def list_roles(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List roles in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter roles (None for all namespaces)
            
        Returns:
            List of role information dictionaries
        """
        try:
            rbac_api = client.RbacAuthorizationV1Api()
            
            roles_list = []
            
            # Get namespaced roles
            if namespace:
                roles = rbac_api.list_namespaced_role(namespace=namespace)
                for role in roles.items:
                    role_info = self._extract_role_info(role, is_cluster_role=False)
                    roles_list.append(role_info)
            else:
                roles = rbac_api.list_role_for_all_namespaces()
                for role in roles.items:
                    role_info = self._extract_role_info(role, is_cluster_role=False)
                    roles_list.append(role_info)
            
            # Get cluster roles
            cluster_roles = rbac_api.list_cluster_role()
            for role in cluster_roles.items:
                role_info = self._extract_role_info(role, is_cluster_role=True)
                roles_list.append(role_info)
            
            logger.info("Listed roles", count=len(roles_list), namespace=namespace)
            return roles_list
            
        except ApiException as e:
            logger.error("Failed to list roles", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list roles: {e}")
    
    def _extract_role_info(self, role, is_cluster_role: bool = False) -> Dict[str, Any]:
        """Extract information from a role or cluster role."""
        rules = []
        for rule in role.rules:
            rule_info = {
                "api_groups": rule.api_groups,
                "resources": rule.resources,
                "verbs": rule.verbs,
                "resource_names": rule.resource_names
            }
            rules.append(rule_info)
        
        return {
            "name": role.metadata.name,
            "namespace": None if is_cluster_role else role.metadata.namespace,
            "is_cluster_role": is_cluster_role,
            "rules": rules,
            "labels": role.metadata.labels or {},
            "annotations": role.metadata.annotations or {},
            "created_at": role.metadata.creation_timestamp
        }
    
    def list_role_bindings(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List role bindings in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter role bindings (None for all namespaces)
            
        Returns:
            List of role binding information dictionaries
        """
        try:
            rbac_api = client.RbacAuthorizationV1Api()
            
            bindings_list = []
            
            # Get namespaced role bindings
            if namespace:
                bindings = rbac_api.list_namespaced_role_binding(namespace=namespace)
                for binding in bindings.items:
                    binding_info = self._extract_binding_info(binding, is_cluster_binding=False)
                    bindings_list.append(binding_info)
            else:
                bindings = rbac_api.list_role_binding_for_all_namespaces()
                for binding in bindings.items:
                    binding_info = self._extract_binding_info(binding, is_cluster_binding=False)
                    bindings_list.append(binding_info)
            
            # Get cluster role bindings
            cluster_bindings = rbac_api.list_cluster_role_binding()
            for binding in cluster_bindings.items:
                binding_info = self._extract_binding_info(binding, is_cluster_binding=True)
                bindings_list.append(binding_info)
            
            logger.info("Listed role bindings", count=len(bindings_list), namespace=namespace)
            return bindings_list
            
        except ApiException as e:
            logger.error("Failed to list role bindings", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list role bindings: {e}")
    
    def _extract_binding_info(self, binding, is_cluster_binding: bool = False) -> Dict[str, Any]:
        """Extract information from a role binding or cluster role binding."""
        subjects = []
        if binding.subjects:
            for subject in binding.subjects:
                subject_info = {
                    "kind": subject.kind,
                    "name": subject.name,
                    "namespace": subject.namespace
                }
                subjects.append(subject_info)
        
        return {
            "name": binding.metadata.name,
            "namespace": None if is_cluster_binding else binding.metadata.namespace,
            "is_cluster_binding": is_cluster_binding,
            "role_ref": {
                "kind": binding.role_ref.kind,
                "name": binding.role_ref.name,
                "api_group": binding.role_ref.api_group
            },
            "subjects": subjects,
            "labels": binding.metadata.labels or {},
            "annotations": binding.metadata.annotations or {},
            "created_at": binding.metadata.creation_timestamp
        }
    
    def list_network_policies(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List network policies in the cluster or specific namespace.
        
        Args:
            namespace: Namespace to filter network policies (None for all namespaces)
            
        Returns:
            List of network policy information dictionaries
        """
        try:
            networking_api = client.NetworkingV1Api()
            
            if namespace:
                policies = networking_api.list_namespaced_network_policy(namespace=namespace)
            else:
                policies = networking_api.list_network_policy_for_all_namespaces()
            
            policy_list = []
            for policy in policies.items:
                policy_info = {
                    "name": policy.metadata.name,
                    "namespace": policy.metadata.namespace,
                    "pod_selector": policy.spec.pod_selector.match_labels if policy.spec.pod_selector else {},
                    "policy_types": policy.spec.policy_types if policy.spec.policy_types else [],
                    "ingress_rules": self._extract_network_policy_rules(policy.spec.ingress) if policy.spec.ingress else [],
                    "egress_rules": self._extract_network_policy_rules(policy.spec.egress) if policy.spec.egress else [],
                    "labels": policy.metadata.labels or {},
                    "annotations": policy.metadata.annotations or {},
                    "created_at": policy.metadata.creation_timestamp
                }
                policy_list.append(policy_info)
            
            logger.info("Listed network policies", count=len(policy_list), namespace=namespace)
            return policy_list
            
        except ApiException as e:
            logger.error("Failed to list network policies", error=str(e), namespace=namespace)
            raise KubernetesClientError(f"Failed to list network policies: {e}")
    
    def _extract_network_policy_rules(self, rules) -> List[Dict[str, Any]]:
        """Extract information from network policy rules."""
        extracted_rules = []
        
        for rule in rules:
            rule_info = {}
            
            # Extract ports
            if rule.ports:
                rule_info["ports"] = []
                for port in rule.ports:
                    port_info = {
                        "port": port.port,
                        "protocol": port.protocol
                    }
                    rule_info["ports"].append(port_info)
            
            # Extract from
            if rule.from_:
                rule_info["from"] = []
                for from_item in rule.from_:
                    from_info = {}
                    
                    if from_item.ip_block:
                        from_info["ip_block"] = {
                            "cidr": from_item.ip_block.cidr,
                            "except": from_item.ip_block.except_ if from_item.ip_block.except_ else []
                        }
                    
                    if from_item.namespace_selector:
                        from_info["namespace_selector"] = from_item.namespace_selector.match_labels or {}
                    
                    if from_item.pod_selector:
                        from_info["pod_selector"] = from_item.pod_selector.match_labels or {}
                    
                    rule_info["from"].append(from_info)
            
            # Extract to
            if hasattr(rule, 'to') and rule.to:
                rule_info["to"] = []
                for to_item in rule.to:
                    to_info = {}
                    
                    if to_item.ip_block:
                        to_info["ip_block"] = {
                            "cidr": to_item.ip_block.cidr,
                            "except": to_item.ip_block.except_ if to_item.ip_block.except_ else []
                        }
                    
                    if to_item.namespace_selector:
                        to_info["namespace_selector"] = to_item.namespace_selector.match_labels or {}
                    
                    if to_item.pod_selector:
                        to_info["pod_selector"] = to_item.pod_selector.match_labels or {}
                    
                    rule_info["to"].append(to_info)
            
            extracted_rules.append(rule_info)
        
        return extracted_rules
    
    def _extract_node_conditions(self, node) -> Dict[str, Any]:
        """
        Extract node conditions.
        
        Args:
            node: Kubernetes node object
            
        Returns:
            Dictionary of node conditions
        """
        conditions = {}
        
        if node.status.conditions:
            for condition in node.status.conditions:
                conditions[condition.type] = {
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                    "last_transition_time": condition.last_transition_time
                }
        
        return conditions
        
    def get_deployment(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific deployment by name and namespace.
        
        Args:
            name: Name of the deployment
            namespace: Namespace of the deployment
            
        Returns:
            Deployment information dictionary or None if not found
        """
        try:
            deployment = self._apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
            
            deployment_info = {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "available_replicas": deployment.status.available_replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "updated_replicas": deployment.status.updated_replicas or 0,
                "unavailable_replicas": deployment.status.unavailable_replicas or 0,
                "strategy": deployment.spec.strategy.type,
                "selector": deployment.spec.selector.match_labels if deployment.spec.selector else {},
                "labels": deployment.metadata.labels or {},
                "annotations": deployment.metadata.annotations or {},
                "created_at": deployment.metadata.creation_timestamp,
                "containers": self._extract_deployment_containers(deployment)
            }
            
            logger.info("Retrieved deployment", name=name, namespace=namespace)
            return deployment_info
            
        except ApiException as e:
            if e.status == 404:
                logger.warning("Deployment not found", name=name, namespace=namespace)
                return None
            else:
                logger.error("Failed to get deployment", error=str(e), name=name, namespace=namespace)
                raise KubernetesClientError(f"Failed to get deployment: {e}")
        except Exception as e:
            logger.error("Unexpected error getting deployment", error=str(e), name=name, namespace=namespace)
            raise KubernetesClientError(f"Unexpected error getting deployment: {e}")
            
    def list_replicasets_for_deployment(self, deployment_name: str, namespace: str) -> List[Dict[str, Any]]:
        """
        List ReplicaSets for a specific deployment.
        
        Args:
            deployment_name: Name of the deployment
            namespace: Namespace of the deployment
            
        Returns:
            List of ReplicaSet information dictionaries
        """
        try:
            # Get all replicasets in the namespace
            replicasets = self._apps_v1.list_namespaced_replica_set(namespace=namespace)
            
            # Filter for replicasets owned by the deployment
            deployment_replicasets = []
            for rs in replicasets.items:
                # Check if this replicaset is owned by the deployment
                if rs.metadata.owner_references:
                    for owner in rs.metadata.owner_references:
                        if owner.kind == "Deployment" and owner.name == deployment_name:
                            # Extract revision from annotations
                            revision = None
                            if rs.metadata.annotations and "deployment.kubernetes.io/revision" in rs.metadata.annotations:
                                try:
                                    revision = int(rs.metadata.annotations["deployment.kubernetes.io/revision"])
                                except (ValueError, TypeError):
                                    revision = None
                            
                            rs_info = {
                                "name": rs.metadata.name,
                                "namespace": rs.metadata.namespace,
                                "replicas": rs.spec.replicas,
                                "ready_replicas": rs.status.ready_replicas or 0,
                                "available_replicas": rs.status.available_replicas or 0,
                                "revision": revision,
                                "created_at": rs.metadata.creation_timestamp,
                                "containers": []
                            }
                            
                            # Extract container information
                            if rs.spec.template and rs.spec.template.spec and rs.spec.template.spec.containers:
                                for container in rs.spec.template.spec.containers:
                                    container_info = {
                                        "name": container.name,
                                        "image": container.image
                                    }
                                    rs_info["containers"].append(container_info)
                            
                            deployment_replicasets.append(rs_info)
                            break
            
            # Sort by revision (descending)
            deployment_replicasets.sort(key=lambda x: x.get("revision", 0) or 0, reverse=True)
            
            logger.info("Listed replicasets for deployment", 
                      deployment=deployment_name, 
                      namespace=namespace, 
                      count=len(deployment_replicasets))
            return deployment_replicasets
            
        except ApiException as e:
            logger.error("Failed to list replicasets", error=str(e), deployment=deployment_name, namespace=namespace)
            raise KubernetesClientError(f"Failed to list replicasets: {e}")
        except Exception as e:
            logger.error("Unexpected error listing replicasets", error=str(e), deployment=deployment_name, namespace=namespace)
            raise KubernetesClientError(f"Unexpected error listing replicasets: {e}")