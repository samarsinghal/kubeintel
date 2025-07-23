"""Tests for the data collector service."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.k8s.collector import DataCollector, DataCollectorError
from src.k8s.client import KubernetesClient, KubernetesClientError
from src.models.kubernetes import ClusterData, PodInfo, ServiceInfo, EventInfo


class TestDataCollector:
    """Test cases for DataCollector."""
    
    @pytest.fixture
    def mock_k8s_client(self):
        """Create a mock Kubernetes client."""
        client = Mock(spec=KubernetesClient)
        client.health_check.return_value = True
        return client
    
    @pytest.fixture
    def data_collector(self, mock_k8s_client):
        """Create a DataCollector instance with mock client."""
        return DataCollector(mock_k8s_client, max_log_lines=50)
    
    @pytest.mark.asyncio
    async def test_collect_cluster_data_success(self, data_collector, mock_k8s_client):
        """Test successful cluster data collection."""
        # Setup mock responses
        mock_k8s_client.list_pods.return_value = [
            {
                "name": "test-pod",
                "namespace": "default",
                "status": "Running",
                "ready": True,
                "restart_count": 0,
                "containers": [
                    {
                        "name": "nginx",
                        "image": "nginx:latest",
                        "ready": True,
                        "restart_count": 0,
                        "state": "Running"
                    }
                ],
                "labels": {"app": "test"},
                "annotations": {},
                "created_at": datetime.now()
            }
        ]
        
        mock_k8s_client.list_services.return_value = [
            {
                "name": "test-service",
                "namespace": "default",
                "type": "ClusterIP",
                "cluster_ip": "10.0.0.1",
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "target_port": 8080,
                        "protocol": "TCP"
                    }
                ],
                "selector": {"app": "test"},
                "labels": {},
                "created_at": datetime.now()
            }
        ]
        
        mock_k8s_client.list_events.return_value = [
            {
                "name": "test-event",
                "namespace": "default",
                "type": "Normal",
                "reason": "Started",
                "message": "Pod started successfully",
                "involved_object": {
                    "kind": "Pod",
                    "name": "test-pod",
                    "namespace": "default"
                },
                "first_timestamp": datetime.now(),
                "last_timestamp": datetime.now(),
                "count": 1
            }
        ]
        
        mock_k8s_client.get_pod_logs.return_value = [
            "2023-01-01 10:00:00 INFO Starting application",
            "2023-01-01 10:00:01 INFO Application ready"
        ]
        
        # Execute
        cluster_data = await data_collector.collect_cluster_data(include_logs=True)
        
        # Verify
        assert isinstance(cluster_data, ClusterData)
        assert len(cluster_data.pods) == 1
        assert len(cluster_data.services) == 1
        assert len(cluster_data.events) == 1
        assert len(cluster_data.logs) == 1
        
        # Verify pod data
        pod = cluster_data.pods[0]
        assert pod.name == "test-pod"
        assert pod.namespace == "default"
        assert pod.status == "Running"
        assert len(pod.containers) == 1
        
        # Verify service data
        service = cluster_data.services[0]
        assert service.name == "test-service"
        assert service.namespace == "default"
        assert len(service.ports) == 1
        
        # Verify event data
        event = cluster_data.events[0]
        assert event.name == "test-event"
        assert event.type == "Normal"
        
        # Verify logs
        assert "default/test-pod" in cluster_data.logs
    
    @pytest.mark.asyncio
    async def test_collect_cluster_data_namespace_filter(self, data_collector, mock_k8s_client):
        """Test cluster data collection with namespace filter."""
        mock_k8s_client.list_pods.return_value = []
        mock_k8s_client.list_services.return_value = []
        mock_k8s_client.list_events.return_value = []
        
        # Execute
        cluster_data = await data_collector.collect_cluster_data(
            namespace="test-namespace",
            include_logs=False
        )
        
        # Verify namespace filter was applied
        mock_k8s_client.list_pods.assert_called_once_with("test-namespace")
        mock_k8s_client.list_services.assert_called_once_with("test-namespace")
        mock_k8s_client.list_events.assert_called_once_with("test-namespace", 1)
        
        assert cluster_data.namespace_filter == "test-namespace"
    
    @pytest.mark.asyncio
    async def test_collect_cluster_data_without_logs(self, data_collector, mock_k8s_client):
        """Test cluster data collection without logs."""
        mock_k8s_client.list_pods.return_value = []
        mock_k8s_client.list_services.return_value = []
        mock_k8s_client.list_events.return_value = []
        
        # Execute
        cluster_data = await data_collector.collect_cluster_data(include_logs=False)
        
        # Verify
        assert len(cluster_data.logs) == 0
        mock_k8s_client.get_pod_logs.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_collect_cluster_data_partial_failure(self, data_collector, mock_k8s_client):
        """Test cluster data collection with partial failures."""
        # Setup - pods collection fails, but services and events succeed
        mock_k8s_client.list_pods.side_effect = KubernetesClientError("Failed to list pods")
        mock_k8s_client.list_services.return_value = []
        mock_k8s_client.list_events.return_value = []
        
        # Execute
        cluster_data = await data_collector.collect_cluster_data(include_logs=False)
        
        # Verify - should continue with empty pods list
        assert len(cluster_data.pods) == 0
        assert len(cluster_data.services) == 0
        assert len(cluster_data.events) == 0
    
    @pytest.mark.asyncio
    async def test_collect_logs_with_failures(self, data_collector, mock_k8s_client):
        """Test log collection with some failures."""
        pods = [
            PodInfo(name="pod1", namespace="default", status="Running"),
            PodInfo(name="pod2", namespace="default", status="Running")
        ]
        
        # Setup - first pod logs succeed, second fails
        def mock_get_logs(pod_name, namespace, lines):
            if pod_name == "pod1":
                return ["log line 1", "log line 2"]
            else:
                raise KubernetesClientError("Failed to get logs")
        
        mock_k8s_client.get_pod_logs.side_effect = mock_get_logs
        
        # Execute
        logs = await data_collector._collect_logs(pods)
        
        # Verify - should have logs for pod1 only
        assert len(logs) == 1
        assert "default/pod1" in logs
        assert "default/pod2" not in logs
    
    @pytest.mark.asyncio
    async def test_collect_specific_pod_data(self, data_collector, mock_k8s_client):
        """Test collecting data for a specific pod."""
        mock_k8s_client.list_pods.return_value = [
            {
                "name": "target-pod",
                "namespace": "default",
                "status": "Running",
                "ready": True,
                "containers": [],
                "labels": {},
                "annotations": {}
            }
        ]
        mock_k8s_client.list_services.return_value = []
        mock_k8s_client.list_events.return_value = []
        
        # Execute
        pod_info = await data_collector.collect_specific_pod_data("target-pod", "default")
        
        # Verify
        assert pod_info is not None
        assert pod_info.name == "target-pod"
        assert pod_info.namespace == "default"
    
    @pytest.mark.asyncio
    async def test_collect_specific_pod_data_not_found(self, data_collector, mock_k8s_client):
        """Test collecting data for a non-existent pod."""
        mock_k8s_client.list_pods.return_value = []
        mock_k8s_client.list_services.return_value = []
        mock_k8s_client.list_events.return_value = []
        
        # Execute
        pod_info = await data_collector.collect_specific_pod_data("nonexistent-pod", "default")
        
        # Verify
        assert pod_info is None
    
    @pytest.mark.asyncio
    async def test_collect_namespace_summary(self, data_collector, mock_k8s_client):
        """Test collecting namespace summary."""
        # Setup mock data with healthy and unhealthy pods
        mock_k8s_client.list_pods.return_value = [
            {
                "name": "healthy-pod",
                "namespace": "test-ns",
                "status": "Running",
                "ready": True,
                "restart_count": 1,
                "containers": [],
                "labels": {},
                "annotations": {}
            },
            {
                "name": "unhealthy-pod",
                "namespace": "test-ns",
                "status": "Failed",
                "ready": False,
                "restart_count": 0,
                "containers": [],
                "labels": {},
                "annotations": {}
            }
        ]
        
        mock_k8s_client.list_services.return_value = [
            {
                "name": "test-service",
                "namespace": "test-ns",
                "type": "ClusterIP",
                "ports": [],
                "selector": {},
                "labels": {}
            }
        ]
        
        mock_k8s_client.list_events.return_value = [
            {
                "name": "warning-event",
                "namespace": "test-ns",
                "type": "Warning",
                "reason": "Failed",
                "message": "Something failed",
                "involved_object": {"kind": "Pod", "name": "test-pod"},
                "count": 1
            }
        ]
        
        # Execute
        summary = await data_collector.collect_namespace_summary("test-ns")
        
        # Verify
        assert summary["namespace"] == "test-ns"
        assert summary["total_pods"] == 2
        assert summary["healthy_pods"] == 1
        assert summary["unhealthy_pods"] == 1
        assert summary["total_services"] == 1
        assert summary["warning_events"] == 1
        assert summary["error_events"] == 1  # Warning events are also error events
    
    def test_health_check_success(self, data_collector, mock_k8s_client):
        """Test successful health check."""
        mock_k8s_client.health_check.return_value = True
        
        result = data_collector.health_check()
        
        assert result is True
        mock_k8s_client.health_check.assert_called_once()
    
    def test_health_check_failure(self, data_collector, mock_k8s_client):
        """Test failed health check."""
        mock_k8s_client.health_check.return_value = False
        
        result = data_collector.health_check()
        
        assert result is False
    
    def test_health_check_exception(self, data_collector, mock_k8s_client):
        """Test health check with exception."""
        mock_k8s_client.health_check.side_effect = Exception("Connection error")
        
        result = data_collector.health_check()
        
        assert result is False
    
    def test_convert_to_pod_info(self, data_collector):
        """Test conversion of raw pod data to PodInfo."""
        raw_pod = {
            "name": "test-pod",
            "namespace": "default",
            "status": "Running",
            "ready": True,
            "restart_count": 2,
            "node_name": "node-1",
            "containers": [
                {
                    "name": "nginx",
                    "image": "nginx:latest",
                    "ready": True,
                    "restart_count": 1,
                    "state": "Running"
                }
            ],
            "labels": {"app": "test"},
            "annotations": {"version": "1.0"},
            "created_at": datetime.now()
        }
        
        pod_info = data_collector._convert_to_pod_info(raw_pod)
        
        assert pod_info.name == "test-pod"
        assert pod_info.namespace == "default"
        assert pod_info.status == "Running"
        assert pod_info.ready is True
        assert pod_info.restart_count == 2
        assert pod_info.node_name == "node-1"
        assert len(pod_info.containers) == 1
        assert pod_info.containers[0].name == "nginx"
        assert pod_info.labels == {"app": "test"}
        assert pod_info.annotations == {"version": "1.0"}
    
    def test_convert_to_service_info(self, data_collector):
        """Test conversion of raw service data to ServiceInfo."""
        raw_service = {
            "name": "test-service",
            "namespace": "default",
            "type": "LoadBalancer",
            "cluster_ip": "10.0.0.1",
            "ports": [
                {
                    "name": "http",
                    "port": 80,
                    "target_port": 8080,
                    "protocol": "TCP",
                    "node_port": 30080
                }
            ],
            "selector": {"app": "test"},
            "labels": {"version": "1.0"},
            "created_at": datetime.now()
        }
        
        service_info = data_collector._convert_to_service_info(raw_service)
        
        assert service_info.name == "test-service"
        assert service_info.namespace == "default"
        assert service_info.type == "LoadBalancer"
        assert service_info.cluster_ip == "10.0.0.1"
        assert len(service_info.ports) == 1
        assert service_info.ports[0].name == "http"
        assert service_info.ports[0].port == 80
        assert service_info.selector == {"app": "test"}
        assert service_info.labels == {"version": "1.0"}
    
    def test_convert_to_event_info(self, data_collector):
        """Test conversion of raw event data to EventInfo."""
        raw_event = {
            "name": "test-event",
            "namespace": "default",
            "type": "Warning",
            "reason": "Failed",
            "message": "Pod failed to start",
            "involved_object": {
                "kind": "Pod",
                "name": "test-pod",
                "namespace": "default"
            },
            "first_timestamp": datetime.now(),
            "last_timestamp": datetime.now(),
            "count": 3
        }
        
        event_info = data_collector._convert_to_event_info(raw_event)
        
        assert event_info.name == "test-event"
        assert event_info.namespace == "default"
        assert event_info.type == "Warning"
        assert event_info.reason == "Failed"
        assert event_info.message == "Pod failed to start"
        assert event_info.involved_object.kind == "Pod"
        assert event_info.involved_object.name == "test-pod"
        assert event_info.count == 3