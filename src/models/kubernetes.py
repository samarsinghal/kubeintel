"""Data models for Kubernetes resources."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class ContainerInfo:
    """Information about a container in a pod."""
    name: str
    image: str
    ready: bool = False
    restart_count: int = 0
    state: str = "Unknown"


@dataclass_json
@dataclass
class PodInfo:
    """Information about a Kubernetes pod."""
    name: str
    namespace: str
    status: str  # Running, Pending, Failed, etc.
    ready: bool = False
    restart_count: int = 0
    node_name: Optional[str] = None
    containers: List[ContainerInfo] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if the pod is in a healthy state."""
        return self.status == "Running" and self.ready and self.restart_count < 5
    
    @property
    def has_high_restarts(self) -> bool:
        """Check if the pod has a high restart count."""
        return self.restart_count >= 5
    
    def get_container_by_name(self, name: str) -> Optional[ContainerInfo]:
        """Get container information by name."""
        for container in self.containers:
            if container.name == name:
                return container
        return None


@dataclass_json
@dataclass
class ServicePort:
    """Information about a service port."""
    name: Optional[str] = None
    port: int = 80
    target_port: Optional[int] = None
    protocol: str = "TCP"
    node_port: Optional[int] = None


@dataclass_json
@dataclass
class ServiceInfo:
    """Information about a Kubernetes service."""
    name: str
    namespace: str
    type: str = "ClusterIP"  # ClusterIP, NodePort, LoadBalancer
    cluster_ip: Optional[str] = None
    ports: List[ServicePort] = field(default_factory=list)
    selector: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    @property
    def is_headless(self) -> bool:
        """Check if this is a headless service."""
        return self.cluster_ip == "None"
    
    def get_port_by_name(self, name: str) -> Optional[ServicePort]:
        """Get port information by name."""
        for port in self.ports:
            if port.name == name:
                return port
        return None


@dataclass_json
@dataclass
class InvolvedObject:
    """Information about the object involved in an event."""
    kind: str
    name: str
    namespace: Optional[str] = None


@dataclass_json
@dataclass
class EventInfo:
    """Information about a Kubernetes event."""
    name: str
    namespace: str
    type: str  # Normal, Warning
    reason: str
    message: str
    involved_object: InvolvedObject
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    count: int = 1
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning event."""
        return self.type == "Warning"
    
    @property
    def is_error(self) -> bool:
        """Check if this event indicates an error."""
        error_reasons = [
            "Failed", "FailedScheduling", "FailedMount", "FailedAttachVolume",
            "FailedSync", "BackOff", "Unhealthy", "ProbeWarning"
        ]
        return self.reason in error_reasons or self.is_warning


@dataclass_json
@dataclass
class Finding:
    """Information about an analysis finding."""
    type: str  # issue, warning, info
    resource: str
    message: str
    context: str = ""
    recommendations: List[str] = field(default_factory=list)
    severity: int = 1  # 1-5 scale


@dataclass_json
@dataclass
class ClusterData:
    """Aggregated data from a Kubernetes cluster."""
    pods: List[PodInfo] = field(default_factory=list)
    services: List[ServiceInfo] = field(default_factory=list)
    events: List[EventInfo] = field(default_factory=list)
    logs: Dict[str, List[str]] = field(default_factory=dict)  # pod_name -> log_lines
    timestamp: datetime = field(default_factory=datetime.now)
    namespace_filter: Optional[str] = None
    
    @property
    def total_pods(self) -> int:
        """Get total number of pods."""
        return len(self.pods)
    
    @property
    def healthy_pods(self) -> int:
        """Get number of healthy pods."""
        return sum(1 for pod in self.pods if pod.is_healthy)
    
    @property
    def unhealthy_pods(self) -> int:
        """Get number of unhealthy pods."""
        return self.total_pods - self.healthy_pods
    
    @property
    def total_services(self) -> int:
        """Get total number of services."""
        return len(self.services)
    
    @property
    def warning_events(self) -> List[EventInfo]:
        """Get all warning events."""
        return [event for event in self.events if event.is_warning]
    
    @property
    def error_events(self) -> List[EventInfo]:
        """Get all error events."""
        return [event for event in self.events if event.is_error]
    
    def get_pods_by_namespace(self, namespace: str) -> List[PodInfo]:
        """Get pods filtered by namespace."""
        return [pod for pod in self.pods if pod.namespace == namespace]
    
    def get_services_by_namespace(self, namespace: str) -> List[ServiceInfo]:
        """Get services filtered by namespace."""
        return [service for service in self.services if service.namespace == namespace]
    
    def get_events_by_namespace(self, namespace: str) -> List[EventInfo]:
        """Get events filtered by namespace."""
        return [event for event in self.events if event.namespace == namespace]
    
    def get_pod_by_name(self, name: str, namespace: str) -> Optional[PodInfo]:
        """Get a specific pod by name and namespace."""
        for pod in self.pods:
            if pod.name == name and pod.namespace == namespace:
                return pod
        return None
    
    def get_service_by_name(self, name: str, namespace: str) -> Optional[ServiceInfo]:
        """Get a specific service by name and namespace."""
        for service in self.services:
            if service.name == name and service.namespace == namespace:
                return service
        return None
    
    def get_pods_for_service(self, service: ServiceInfo) -> List[PodInfo]:
        """Get pods that match a service's selector."""
        if not service.selector:
            return []
        
        matching_pods = []
        for pod in self.pods:
            if pod.namespace == service.namespace:
                # Check if pod labels match service selector
                if all(pod.labels.get(key) == value for key, value in service.selector.items()):
                    matching_pods.append(pod)
        
        return matching_pods
    
    def get_events_for_pod(self, pod: PodInfo) -> List[EventInfo]:
        """Get events related to a specific pod."""
        return [
            event for event in self.events
            if (event.involved_object.kind == "Pod" and
                event.involved_object.name == pod.name and
                event.involved_object.namespace == pod.namespace)
        ]
    
    def get_namespaces(self) -> List[str]:
        """Get list of all namespaces present in the data."""
        namespaces = set()
        for pod in self.pods:
            namespaces.add(pod.namespace)
        for service in self.services:
            namespaces.add(service.namespace)
        return sorted(list(namespaces))
    
    def validate(self) -> List[str]:
        """Validate the cluster data and return any validation errors."""
        errors = []
        
        # Check for required fields
        if not isinstance(self.pods, list):
            errors.append("pods must be a list")
        if not isinstance(self.services, list):
            errors.append("services must be a list")
        if not isinstance(self.events, list):
            errors.append("events must be a list")
        if not isinstance(self.logs, dict):
            errors.append("logs must be a dictionary")
        
        # Validate individual pods
        for i, pod in enumerate(self.pods):
            if not pod.name:
                errors.append(f"Pod at index {i} missing name")
            if not pod.namespace:
                errors.append(f"Pod at index {i} missing namespace")
        
        # Validate individual services
        for i, service in enumerate(self.services):
            if not service.name:
                errors.append(f"Service at index {i} missing name")
            if not service.namespace:
                errors.append(f"Service at index {i} missing namespace")
        
        return errors