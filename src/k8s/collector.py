"""Data collector service for gathering Kubernetes cluster information."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from src.k8s.client import KubernetesClient, KubernetesClientError
from src.models.kubernetes import (
    ClusterData, PodInfo, ServiceInfo, EventInfo, ContainerInfo,
    ServicePort, InvolvedObject
)

logger = structlog.get_logger(__name__)


class DataCollectorError(Exception):
    """Base exception for data collector errors."""
    pass


class DataCollector:
    """Service for collecting data from Kubernetes cluster."""
    
    def __init__(self, kubernetes_client: KubernetesClient, max_log_lines: int = 100):
        """
        Initialize the data collector.
        
        Args:
            kubernetes_client: Kubernetes API client
            max_log_lines: Maximum number of log lines to collect per pod
        """
        self.k8s_client = kubernetes_client
        self.max_log_lines = max_log_lines
    
    async def collect_cluster_data(
        self, 
        namespace: Optional[str] = None,
        include_logs: bool = True,
        max_events: int = 100
    ) -> ClusterData:
        """
        Collect comprehensive cluster data.
        
        Args:
            namespace: Namespace to filter data (None for all namespaces)
            include_logs: Whether to collect pod logs
            max_events: Maximum number of events to collect
            
        Returns:
            ClusterData object with collected information
        """
        logger.info("Starting cluster data collection", namespace=namespace, include_logs=include_logs)
        
        try:
            # Collect data concurrently for better performance
            pods_task = asyncio.create_task(self._collect_pods(namespace))
            services_task = asyncio.create_task(self._collect_services(namespace))
            events_task = asyncio.create_task(self._collect_events(namespace, max_events))
            
            # Wait for all data collection tasks to complete
            pods, services, events = await asyncio.gather(
                pods_task, services_task, events_task,
                return_exceptions=True
            )
            
            # Handle any exceptions from data collection
            if isinstance(pods, Exception):
                logger.error("Failed to collect pods", error=str(pods))
                pods = []
            if isinstance(services, Exception):
                logger.error("Failed to collect services", error=str(services))
                services = []
            if isinstance(events, Exception):
                logger.error("Failed to collect events", error=str(events))
                events = []
            
            # Collect logs if requested
            logs = {}
            if include_logs and pods:
                logs = await self._collect_logs(pods, namespace)
            
            cluster_data = ClusterData(
                pods=pods,
                services=services,
                events=events,
                logs=logs,
                timestamp=datetime.now(),
                namespace_filter=namespace
            )
            
            logger.info(
                "Cluster data collection completed",
                pods=len(pods),
                services=len(services),
                events=len(events),
                logs=len(logs),
                namespace=namespace
            )
            
            return cluster_data
            
        except Exception as e:
            logger.error("Failed to collect cluster data", error=str(e))
            raise DataCollectorError(f"Failed to collect cluster data: {e}")
    
    async def _collect_pods(self, namespace: Optional[str] = None) -> List[PodInfo]:
        """Collect pod information from the cluster."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            raw_pods = await loop.run_in_executor(
                None, self.k8s_client.list_pods, namespace
            )
            
            pods = []
            for raw_pod in raw_pods:
                pod = self._convert_to_pod_info(raw_pod)
                pods.append(pod)
            
            logger.debug("Collected pods", count=len(pods), namespace=namespace)
            return pods
            
        except KubernetesClientError as e:
            logger.error("Failed to collect pods", error=str(e), namespace=namespace)
            raise DataCollectorError(f"Failed to collect pods: {e}")
    
    async def _collect_services(self, namespace: Optional[str] = None) -> List[ServiceInfo]:
        """Collect service information from the cluster."""
        try:
            loop = asyncio.get_event_loop()
            raw_services = await loop.run_in_executor(
                None, self.k8s_client.list_services, namespace
            )
            
            services = []
            for raw_service in raw_services:
                service = self._convert_to_service_info(raw_service)
                services.append(service)
            
            logger.debug("Collected services", count=len(services), namespace=namespace)
            return services
            
        except KubernetesClientError as e:
            logger.error("Failed to collect services", error=str(e), namespace=namespace)
            raise DataCollectorError(f"Failed to collect services: {e}")
    
    async def _collect_events(self, namespace: Optional[str] = None, max_events: int = 100) -> List[EventInfo]:
        """Collect event information from the cluster."""
        try:
            loop = asyncio.get_event_loop()
            raw_events = await loop.run_in_executor(
                None, self.k8s_client.list_events, namespace, 1  # Last 1 hour
            )
            
            # Limit the number of events
            if len(raw_events) > max_events:
                raw_events = raw_events[:max_events]
            
            events = []
            for raw_event in raw_events:
                event = self._convert_to_event_info(raw_event)
                events.append(event)
            
            logger.debug("Collected events", count=len(events), namespace=namespace)
            return events
            
        except KubernetesClientError as e:
            logger.error("Failed to collect events", error=str(e), namespace=namespace)
            raise DataCollectorError(f"Failed to collect events: {e}")
    
    async def _collect_logs(self, pods: List[PodInfo], namespace: Optional[str] = None) -> Dict[str, List[str]]:
        """Collect logs from pods."""
        logs = {}
        
        # Limit concurrent log collection to avoid overwhelming the API
        semaphore = asyncio.Semaphore(5)
        
        async def collect_pod_logs(pod: PodInfo) -> None:
            async with semaphore:
                try:
                    loop = asyncio.get_event_loop()
                    log_lines = await loop.run_in_executor(
                        None, 
                        self.k8s_client.get_pod_logs,
                        pod.name,
                        pod.namespace,
                        self.max_log_lines
                    )
                    if log_lines:
                        logs[f"{pod.namespace}/{pod.name}"] = log_lines
                except Exception as e:
                    logger.warning(
                        "Failed to collect logs for pod",
                        pod=pod.name,
                        namespace=pod.namespace,
                        error=str(e)
                    )
        
        # Collect logs concurrently
        tasks = [collect_pod_logs(pod) for pod in pods]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.debug("Collected logs", pod_count=len(logs))
        return logs
    
    def _convert_to_pod_info(self, raw_pod: Dict[str, Any]) -> PodInfo:
        """Convert raw pod data to PodInfo model."""
        containers = []
        for raw_container in raw_pod.get("containers", []):
            container = ContainerInfo(
                name=raw_container["name"],
                image=raw_container["image"],
                ready=raw_container.get("ready", False),
                restart_count=raw_container.get("restart_count", 0),
                state=raw_container.get("state", "Unknown")
            )
            containers.append(container)
        
        return PodInfo(
            name=raw_pod["name"],
            namespace=raw_pod["namespace"],
            status=raw_pod["status"],
            ready=raw_pod.get("ready", False),
            restart_count=raw_pod.get("restart_count", 0),
            node_name=raw_pod.get("node_name"),
            containers=containers,
            labels=raw_pod.get("labels", {}),
            annotations=raw_pod.get("annotations", {}),
            created_at=raw_pod.get("created_at")
        )
    
    def _convert_to_service_info(self, raw_service: Dict[str, Any]) -> ServiceInfo:
        """Convert raw service data to ServiceInfo model."""
        ports = []
        for raw_port in raw_service.get("ports", []):
            port = ServicePort(
                name=raw_port.get("name"),
                port=raw_port["port"],
                target_port=raw_port.get("target_port"),
                protocol=raw_port.get("protocol", "TCP"),
                node_port=raw_port.get("node_port")
            )
            ports.append(port)
        
        return ServiceInfo(
            name=raw_service["name"],
            namespace=raw_service["namespace"],
            type=raw_service.get("type", "ClusterIP"),
            cluster_ip=raw_service.get("cluster_ip"),
            ports=ports,
            selector=raw_service.get("selector", {}),
            labels=raw_service.get("labels", {}),
            created_at=raw_service.get("created_at")
        )
    
    def _convert_to_event_info(self, raw_event: Dict[str, Any]) -> EventInfo:
        """Convert raw event data to EventInfo model."""
        involved_obj_data = raw_event.get("involved_object", {})
        involved_object = InvolvedObject(
            kind=involved_obj_data.get("kind", "Unknown"),
            name=involved_obj_data.get("name", "Unknown"),
            namespace=involved_obj_data.get("namespace")
        )
        
        return EventInfo(
            name=raw_event["name"],
            namespace=raw_event["namespace"],
            type=raw_event.get("type", "Normal"),
            reason=raw_event.get("reason", "Unknown"),
            message=raw_event.get("message", ""),
            involved_object=involved_object,
            first_timestamp=raw_event.get("first_timestamp"),
            last_timestamp=raw_event.get("last_timestamp"),
            count=raw_event.get("count", 1)
        )
    
    async def collect_specific_pod_data(self, pod_name: str, namespace: str) -> Optional[PodInfo]:
        """
        Collect data for a specific pod.
        
        Args:
            pod_name: Name of the pod
            namespace: Namespace of the pod
            
        Returns:
            PodInfo object or None if not found
        """
        try:
            cluster_data = await self.collect_cluster_data(namespace=namespace, include_logs=False)
            return cluster_data.get_pod_by_name(pod_name, namespace)
        except Exception as e:
            logger.error("Failed to collect specific pod data", pod=pod_name, namespace=namespace, error=str(e))
            return None
    
    async def collect_namespace_summary(self, namespace: str) -> Dict[str, Any]:
        """
        Collect summary information for a specific namespace.
        
        Args:
            namespace: Namespace to summarize
            
        Returns:
            Dictionary with namespace summary
        """
        try:
            cluster_data = await self.collect_cluster_data(namespace=namespace, include_logs=False)
            
            summary = {
                "namespace": namespace,
                "total_pods": len(cluster_data.pods),
                "healthy_pods": cluster_data.healthy_pods,
                "unhealthy_pods": cluster_data.unhealthy_pods,
                "total_services": len(cluster_data.services),
                "warning_events": len(cluster_data.warning_events),
                "error_events": len(cluster_data.error_events),
                "timestamp": cluster_data.timestamp
            }
            
            logger.info("Collected namespace summary", namespace=namespace, summary=summary)
            return summary
            
        except Exception as e:
            logger.error("Failed to collect namespace summary", namespace=namespace, error=str(e))
            raise DataCollectorError(f"Failed to collect namespace summary: {e}")
    
    async def test_connection(self) -> bool:
        """
        Test connection to Kubernetes API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return self.k8s_client.health_check()
        except Exception as e:
            logger.error("Data collector connection test failed", error=str(e))
            return False

    def health_check(self) -> bool:
        """
        Check if the data collector is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            return self.k8s_client.health_check()
        except Exception as e:
            logger.error("Data collector health check failed", error=str(e))
            return False