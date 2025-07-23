"""Tests for the Kubernetes client wrapper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from kubernetes.client.rest import ApiException

from src.k8s.client import KubernetesClient, KubernetesClientError


class TestKubernetesClient:
    """Test cases for KubernetesClient."""
    
    @patch('src.kubernetes.client.config')
    @patch('src.kubernetes.client.client')
    def test_init_in_cluster(self, mock_client, mock_config):
        """Test initialization with in-cluster configuration."""
        # Setup
        mock_core_v1 = Mock()
        mock_apps_v1 = Mock()
        mock_client.CoreV1Api.return_value = mock_core_v1
        mock_client.AppsV1Api.return_value = mock_apps_v1
        
        # Execute
        k8s_client = KubernetesClient(config_type="in-cluster")
        
        # Verify
        mock_config.load_incluster_config.assert_called_once()
        mock_client.CoreV1Api.assert_called_once()
        mock_client.AppsV1Api.assert_called_once()
        assert k8s_client._core_v1 == mock_core_v1
        assert k8s_client._apps_v1 == mock_apps_v1
    
    @patch('src.kubernetes.client.config')
    @patch('src.kubernetes.client.client')
    def test_init_kubeconfig(self, mock_client, mock_config):
        """Test initialization with kubeconfig file."""
        # Setup
        kubeconfig_path = "/path/to/kubeconfig"
        
        # Execute
        k8s_client = KubernetesClient(config_type="kubeconfig", kubeconfig_path=kubeconfig_path)
        
        # Verify
        mock_config.load_kube_config.assert_called_once_with(config_file=kubeconfig_path)
    
    @patch('src.kubernetes.client.config')
    def test_init_failure(self, mock_config):
        """Test initialization failure handling."""
        # Setup
        mock_config.load_incluster_config.side_effect = Exception("Config error")
        
        # Execute & Verify
        with pytest.raises(KubernetesClientError, match="Failed to initialize Kubernetes client"):
            KubernetesClient()
    
    def test_list_pods_success(self):
        """Test successful pod listing."""
        # Setup
        k8s_client = self._create_mock_client()
        mock_pod = self._create_mock_pod()
        k8s_client._core_v1.list_pod_for_all_namespaces.return_value.items = [mock_pod]
        
        # Execute
        pods = k8s_client.list_pods()
        
        # Verify
        assert len(pods) == 1
        pod = pods[0]
        assert pod["name"] == "test-pod"
        assert pod["namespace"] == "default"
        assert pod["status"] == "Running"
        assert isinstance(pod["containers"], list)
    
    def test_list_pods_namespace_filter(self):
        """Test pod listing with namespace filter."""
        # Setup
        k8s_client = self._create_mock_client()
        mock_pod = self._create_mock_pod()
        k8s_client._core_v1.list_namespaced_pod.return_value.items = [mock_pod]
        
        # Execute
        pods = k8s_client.list_pods(namespace="test-namespace")
        
        # Verify
        k8s_client._core_v1.list_namespaced_pod.assert_called_once_with(namespace="test-namespace")
        assert len(pods) == 1
    
    def test_list_pods_api_exception(self):
        """Test pod listing with API exception."""
        # Setup
        k8s_client = self._create_mock_client()
        k8s_client._core_v1.list_pod_for_all_namespaces.side_effect = ApiException("API Error")
        
        # Execute & Verify
        with pytest.raises(KubernetesClientError, match="Failed to list pods"):
            k8s_client.list_pods()
    
    def test_list_services_success(self):
        """Test successful service listing."""
        # Setup
        k8s_client = self._create_mock_client()
        mock_service = self._create_mock_service()
        k8s_client._core_v1.list_service_for_all_namespaces.return_value.items = [mock_service]
        
        # Execute
        services = k8s_client.list_services()
        
        # Verify
        assert len(services) == 1
        service = services[0]
        assert service["name"] == "test-service"
        assert service["namespace"] == "default"
        assert service["type"] == "ClusterIP"
    
    def test_list_events_success(self):
        """Test successful event listing."""
        # Setup
        k8s_client = self._create_mock_client()
        mock_event = self._create_mock_event()
        k8s_client._core_v1.list_event_for_all_namespaces.return_value.items = [mock_event]
        
        # Execute
        events = k8s_client.list_events()
        
        # Verify
        assert len(events) == 1
        event = events[0]
        assert event["name"] == "test-event"
        assert event["type"] == "Warning"
        assert event["reason"] == "Failed"
    
    def test_list_events_time_filter(self):
        """Test event listing with time filtering."""
        # Setup
        k8s_client = self._create_mock_client()
        
        # Create old event (should be filtered out)
        old_event = self._create_mock_event()
        old_event.first_timestamp = datetime.now() - timedelta(hours=2)
        
        # Create recent event (should be included)
        recent_event = self._create_mock_event()
        recent_event.first_timestamp = datetime.now() - timedelta(minutes=30)
        recent_event.metadata.name = "recent-event"
        
        k8s_client._core_v1.list_event_for_all_namespaces.return_value.items = [old_event, recent_event]
        
        # Execute
        events = k8s_client.list_events(since_hours=1)
        
        # Verify
        assert len(events) == 1
        assert events[0]["name"] == "recent-event"
    
    def test_get_pod_logs_success(self):
        """Test successful pod log retrieval."""
        # Setup
        k8s_client = self._create_mock_client()
        log_content = "line1\nline2\nline3"
        k8s_client._core_v1.read_namespaced_pod_log.return_value = log_content
        
        # Execute
        logs = k8s_client.get_pod_logs("test-pod", "default")
        
        # Verify
        assert logs == ["line1", "line2", "line3"]
        k8s_client._core_v1.read_namespaced_pod_log.assert_called_once_with(
            name="test-pod",
            namespace="default",
            tail_lines=100
        )
    
    def test_get_pod_logs_not_found(self):
        """Test pod log retrieval when pod is not found."""
        # Setup
        k8s_client = self._create_mock_client()
        api_exception = ApiException("Not found")
        api_exception.status = 404
        k8s_client._core_v1.read_namespaced_pod_log.side_effect = api_exception
        
        # Execute
        logs = k8s_client.get_pod_logs("nonexistent-pod", "default")
        
        # Verify
        assert logs == []
    
    def test_get_pod_logs_api_error(self):
        """Test pod log retrieval with API error."""
        # Setup
        k8s_client = self._create_mock_client()
        api_exception = ApiException("Server error")
        api_exception.status = 500
        k8s_client._core_v1.read_namespaced_pod_log.side_effect = api_exception
        
        # Execute & Verify
        with pytest.raises(KubernetesClientError, match="Failed to get pod logs"):
            k8s_client.get_pod_logs("test-pod", "default")
    
    def test_health_check_success(self):
        """Test successful health check."""
        # Setup
        k8s_client = self._create_mock_client()
        k8s_client._core_v1.get_api_resources.return_value = Mock()
        
        # Execute
        result = k8s_client.health_check()
        
        # Verify
        assert result is True
    
    def test_health_check_failure(self):
        """Test failed health check."""
        # Setup
        k8s_client = self._create_mock_client()
        k8s_client._core_v1.get_api_resources.side_effect = Exception("Connection error")
        
        # Execute
        result = k8s_client.health_check()
        
        # Verify
        assert result is False
    
    def _create_mock_client(self) -> KubernetesClient:
        """Create a mock KubernetesClient for testing."""
        with patch('src.kubernetes.client.config'), \
             patch('src.kubernetes.client.client'):
            client = KubernetesClient()
            client._core_v1 = Mock()
            client._apps_v1 = Mock()
            return client
    
    def _create_mock_pod(self):
        """Create a mock pod object."""
        pod = Mock()
        pod.metadata.name = "test-pod"
        pod.metadata.namespace = "default"
        pod.metadata.creation_timestamp = datetime.now()
        pod.metadata.labels = {"app": "test"}
        pod.metadata.annotations = {}
        pod.status.phase = "Running"
        pod.status.conditions = [Mock(type="Ready", status="True")]
        pod.spec.node_name = "node-1"
        pod.spec.containers = [Mock(name="container-1", image="nginx:latest")]
        
        # Mock container status
        container_status = Mock()
        container_status.name = "container-1"
        container_status.ready = True
        container_status.restart_count = 0
        container_status.state = Mock()
        container_status.state.running = Mock()
        container_status.state.waiting = None
        container_status.state.terminated = None
        pod.status.container_statuses = [container_status]
        
        return pod
    
    def _create_mock_service(self):
        """Create a mock service object."""
        service = Mock()
        service.metadata.name = "test-service"
        service.metadata.namespace = "default"
        service.metadata.creation_timestamp = datetime.now()
        service.metadata.labels = {"app": "test"}
        service.spec.type = "ClusterIP"
        service.spec.cluster_ip = "10.0.0.1"
        service.spec.selector = {"app": "test"}
        
        # Mock port
        port = Mock()
        port.name = "http"
        port.port = 80
        port.target_port = 8080
        port.protocol = "TCP"
        port.node_port = None
        service.spec.ports = [port]
        
        return service
    
    def _create_mock_event(self):
        """Create a mock event object."""
        event = Mock()
        event.metadata.name = "test-event"
        event.metadata.namespace = "default"
        event.type = "Warning"
        event.reason = "Failed"
        event.message = "Pod failed to start"
        event.first_timestamp = datetime.now() - timedelta(minutes=5)
        event.last_timestamp = datetime.now() - timedelta(minutes=5)
        event.count = 1
        
        # Mock involved object
        event.involved_object = Mock()
        event.involved_object.kind = "Pod"
        event.involved_object.name = "test-pod"
        event.involved_object.namespace = "default"
        
        return event