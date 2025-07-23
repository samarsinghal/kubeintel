"""Tests for data models."""

import pytest
from datetime import datetime
from src.models.kubernetes import (
    ContainerInfo, PodInfo, ServiceInfo, ServicePort, 
    EventInfo, InvolvedObject, ClusterData
)


class TestContainerInfo:
    """Test cases for ContainerInfo model."""
    
    def test_container_info_creation(self):
        """Test creating a ContainerInfo instance."""
        container = ContainerInfo(
            name="nginx",
            image="nginx:latest",
            ready=True,
            restart_count=2,
            state="Running"
        )
        
        assert container.name == "nginx"
        assert container.image == "nginx:latest"
        assert container.ready is True
        assert container.restart_count == 2
        assert container.state == "Running"
    
    def test_container_info_defaults(self):
        """Test ContainerInfo with default values."""
        container = ContainerInfo(name="test", image="test:latest")
        
        assert container.ready is False
        assert container.restart_count == 0
        assert container.state == "Unknown"


class TestPodInfo:
    """Test cases for PodInfo model."""
    
    def test_pod_info_creation(self):
        """Test creating a PodInfo instance."""
        container = ContainerInfo(name="nginx", image="nginx:latest")
        pod = PodInfo(
            name="test-pod",
            namespace="default",
            status="Running",
            ready=True,
            containers=[container]
        )
        
        assert pod.name == "test-pod"
        assert pod.namespace == "default"
        assert pod.status == "Running"
        assert pod.ready is True
        assert len(pod.containers) == 1
        assert pod.containers[0].name == "nginx"
    
    def test_pod_is_healthy(self):
        """Test pod health check."""
        # Healthy pod
        healthy_pod = PodInfo(
            name="healthy-pod",
            namespace="default",
            status="Running",
            ready=True,
            restart_count=2
        )
        assert healthy_pod.is_healthy is True
        
        # Unhealthy pod - not running
        unhealthy_pod1 = PodInfo(
            name="unhealthy-pod1",
            namespace="default",
            status="Failed",
            ready=False
        )
        assert unhealthy_pod1.is_healthy is False
        
        # Unhealthy pod - high restart count
        unhealthy_pod2 = PodInfo(
            name="unhealthy-pod2",
            namespace="default",
            status="Running",
            ready=True,
            restart_count=10
        )
        assert unhealthy_pod2.is_healthy is False
    
    def test_pod_has_high_restarts(self):
        """Test high restart count detection."""
        low_restart_pod = PodInfo(
            name="low-restart",
            namespace="default",
            status="Running",
            restart_count=3
        )
        assert low_restart_pod.has_high_restarts is False
        
        high_restart_pod = PodInfo(
            name="high-restart",
            namespace="default",
            status="Running",
            restart_count=5
        )
        assert high_restart_pod.has_high_restarts is True
    
    def test_get_container_by_name(self):
        """Test getting container by name."""
        container1 = ContainerInfo(name="nginx", image="nginx:latest")
        container2 = ContainerInfo(name="sidecar", image="sidecar:latest")
        pod = PodInfo(
            name="test-pod",
            namespace="default",
            status="Running",
            containers=[container1, container2]
        )
        
        found_container = pod.get_container_by_name("nginx")
        assert found_container is not None
        assert found_container.name == "nginx"
        
        not_found = pod.get_container_by_name("nonexistent")
        assert not_found is None


class TestServiceInfo:
    """Test cases for ServiceInfo model."""
    
    def test_service_info_creation(self):
        """Test creating a ServiceInfo instance."""
        port = ServicePort(name="http", port=80, target_port=8080)
        service = ServiceInfo(
            name="test-service",
            namespace="default",
            type="ClusterIP",
            cluster_ip="10.0.0.1",
            ports=[port],
            selector={"app": "test"}
        )
        
        assert service.name == "test-service"
        assert service.namespace == "default"
        assert service.type == "ClusterIP"
        assert service.cluster_ip == "10.0.0.1"
        assert len(service.ports) == 1
        assert service.selector == {"app": "test"}
    
    def test_service_is_headless(self):
        """Test headless service detection."""
        headless_service = ServiceInfo(
            name="headless",
            namespace="default",
            cluster_ip="None"
        )
        assert headless_service.is_headless is True
        
        regular_service = ServiceInfo(
            name="regular",
            namespace="default",
            cluster_ip="10.0.0.1"
        )
        assert regular_service.is_headless is False
    
    def test_get_port_by_name(self):
        """Test getting port by name."""
        port1 = ServicePort(name="http", port=80)
        port2 = ServicePort(name="https", port=443)
        service = ServiceInfo(
            name="test-service",
            namespace="default",
            ports=[port1, port2]
        )
        
        found_port = service.get_port_by_name("http")
        assert found_port is not None
        assert found_port.port == 80
        
        not_found = service.get_port_by_name("nonexistent")
        assert not_found is None


class TestEventInfo:
    """Test cases for EventInfo model."""
    
    def test_event_info_creation(self):
        """Test creating an EventInfo instance."""
        involved_obj = InvolvedObject(kind="Pod", name="test-pod", namespace="default")
        event = EventInfo(
            name="test-event",
            namespace="default",
            type="Warning",
            reason="Failed",
            message="Pod failed to start",
            involved_object=involved_obj
        )
        
        assert event.name == "test-event"
        assert event.type == "Warning"
        assert event.reason == "Failed"
        assert event.involved_object.kind == "Pod"
    
    def test_event_is_warning(self):
        """Test warning event detection."""
        warning_event = EventInfo(
            name="warning",
            namespace="default",
            type="Warning",
            reason="Failed",
            message="Something failed",
            involved_object=InvolvedObject(kind="Pod", name="test")
        )
        assert warning_event.is_warning is True
        
        normal_event = EventInfo(
            name="normal",
            namespace="default",
            type="Normal",
            reason="Started",
            message="Pod started",
            involved_object=InvolvedObject(kind="Pod", name="test")
        )
        assert normal_event.is_warning is False
    
    def test_event_is_error(self):
        """Test error event detection."""
        error_event = EventInfo(
            name="error",
            namespace="default",
            type="Warning",
            reason="Failed",
            message="Something failed",
            involved_object=InvolvedObject(kind="Pod", name="test")
        )
        assert error_event.is_error is True
        
        normal_event = EventInfo(
            name="normal",
            namespace="default",
            type="Normal",
            reason="Started",
            message="Pod started",
            involved_object=InvolvedObject(kind="Pod", name="test")
        )
        assert normal_event.is_error is False


class TestClusterData:
    """Test cases for ClusterData model."""
    
    def test_cluster_data_creation(self):
        """Test creating a ClusterData instance."""
        pod = PodInfo(name="test-pod", namespace="default", status="Running")
        service = ServiceInfo(name="test-service", namespace="default")
        event = EventInfo(
            name="test-event",
            namespace="default",
            type="Normal",
            reason="Started",
            message="Pod started",
            involved_object=InvolvedObject(kind="Pod", name="test-pod")
        )
        
        cluster_data = ClusterData(
            pods=[pod],
            services=[service],
            events=[event],
            logs={"test-pod": ["log line 1", "log line 2"]}
        )
        
        assert len(cluster_data.pods) == 1
        assert len(cluster_data.services) == 1
        assert len(cluster_data.events) == 1
        assert "test-pod" in cluster_data.logs
    
    def test_cluster_data_properties(self):
        """Test ClusterData computed properties."""
        healthy_pod = PodInfo(
            name="healthy", namespace="default", 
            status="Running", ready=True, restart_count=1
        )
        unhealthy_pod = PodInfo(
            name="unhealthy", namespace="default", 
            status="Failed", ready=False
        )
        
        cluster_data = ClusterData(pods=[healthy_pod, unhealthy_pod])
        
        assert cluster_data.total_pods == 2
        assert cluster_data.healthy_pods == 1
        assert cluster_data.unhealthy_pods == 1
    
    def test_cluster_data_filtering(self):
        """Test ClusterData filtering methods."""
        pod1 = PodInfo(name="pod1", namespace="default", status="Running")
        pod2 = PodInfo(name="pod2", namespace="kube-system", status="Running")
        service1 = ServiceInfo(name="svc1", namespace="default")
        service2 = ServiceInfo(name="svc2", namespace="kube-system")
        
        cluster_data = ClusterData(pods=[pod1, pod2], services=[service1, service2])
        
        default_pods = cluster_data.get_pods_by_namespace("default")
        assert len(default_pods) == 1
        assert default_pods[0].name == "pod1"
        
        default_services = cluster_data.get_services_by_namespace("default")
        assert len(default_services) == 1
        assert default_services[0].name == "svc1"
    
    def test_get_pods_for_service(self):
        """Test getting pods that match a service selector."""
        pod1 = PodInfo(
            name="matching-pod", 
            namespace="default", 
            status="Running",
            labels={"app": "test", "version": "v1"}
        )
        pod2 = PodInfo(
            name="non-matching-pod", 
            namespace="default", 
            status="Running",
            labels={"app": "other"}
        )
        service = ServiceInfo(
            name="test-service",
            namespace="default",
            selector={"app": "test"}
        )
        
        cluster_data = ClusterData(pods=[pod1, pod2], services=[service])
        matching_pods = cluster_data.get_pods_for_service(service)
        
        assert len(matching_pods) == 1
        assert matching_pods[0].name == "matching-pod"
    
    def test_cluster_data_validation(self):
        """Test ClusterData validation."""
        # Valid data
        valid_data = ClusterData()
        errors = valid_data.validate()
        assert len(errors) == 0
        
        # Invalid data - missing pod name
        invalid_pod = PodInfo(name="", namespace="default", status="Running")
        invalid_data = ClusterData(pods=[invalid_pod])
        errors = invalid_data.validate()
        assert len(errors) > 0
        assert any("missing name" in error for error in errors)