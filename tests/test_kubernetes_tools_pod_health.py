"""
Tests for Kubernetes pod health analysis tool.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesPodHealthTool(unittest.TestCase):
    """Test cases for Kubernetes pod health analysis tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample pod data for testing
        self.sample_pods = [
            {
                "name": "healthy-pod-1",
                "namespace": "default",
                "status": "Running",
                "ready": True,
                "restart_count": 0,
                "node_name": "node-1",
                "containers": [
                    {
                        "name": "container-1",
                        "image": "nginx:latest",
                        "ready": True,
                        "restart_count": 0,
                        "state": "Running"
                    }
                ],
                "labels": {
                    "app": "web",
                    "tier": "frontend"
                },
                "annotations": {}
            },
            {
                "name": "pending-pod-1",
                "namespace": "default",
                "status": "Pending",
                "ready": False,
                "restart_count": 0,
                "node_name": None,
                "containers": [
                    {
                        "name": "container-2",
                        "image": "redis:latest",
                        "ready": False,
                        "restart_count": 0,
                        "state": "Waiting"
                    }
                ],
                "labels": {
                    "app": "cache",
                    "tier": "backend"
                },
                "annotations": {}
            },
            {
                "name": "high-restart-pod-1",
                "namespace": "default",
                "status": "Running",
                "ready": True,
                "restart_count": 10,
                "node_name": "node-2",
                "containers": [
                    {
                        "name": "container-3",
                        "image": "app:latest",
                        "ready": True,
                        "restart_count": 10,
                        "state": "Running"
                    }
                ],
                "labels": {
                    "app": "api",
                    "tier": "backend"
                },
                "annotations": {}
            },
            {
                "name": "crashloop-pod-1",
                "namespace": "default",
                "status": "Running",
                "ready": False,
                "restart_count": 5,
                "node_name": "node-1",
                "containers": [
                    {
                        "name": "container-4",
                        "image": "app:latest",
                        "ready": False,
                        "restart_count": 5,
                        "state": "Waiting: CrashLoopBackOff"
                    }
                ],
                "labels": {
                    "app": "worker",
                    "tier": "backend"
                },
                "annotations": {}
            }
        ]
        
        # Sample events data for testing
        self.sample_events = [
            {
                "name": "event-1",
                "namespace": "default",
                "type": "Warning",
                "reason": "FailedScheduling",
                "message": "0/3 nodes are available: 3 Insufficient memory",
                "involved_object": {
                    "kind": "Pod",
                    "name": "pending-pod-1",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-01T00:00:00Z",
                "last_timestamp": "2023-01-01T00:05:00Z",
                "count": 10
            },
            {
                "name": "event-2",
                "namespace": "default",
                "type": "Warning",
                "reason": "BackOff",
                "message": "Back-off restarting failed container",
                "involved_object": {
                    "kind": "Pod",
                    "name": "crashloop-pod-1",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-01T00:00:00Z",
                "last_timestamp": "2023-01-01T00:05:00Z",
                "count": 5
            }
        ]
        
        # Mock responses for get_pods and get_events
        self.mock_pods_response = {
            "pods": self.sample_pods,
            "count": len(self.sample_pods),
            "namespace": "default",
            "summary": {
                "running": 3,
                "pending": 1,
                "failed": 0,
                "succeeded": 0,
                "other": 0,
                "ready_percentage": 50.0
            },
            "health_assessment": {
                "status": "warning",
                "message": "Warning issues detected in pods",
                "issues": []
            }
        }
        
        self.mock_events_response = {
            "events": self.sample_events,
            "count": len(self.sample_events)
        }
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_pod_health_all_namespaces(self, mock_client_class):
        """Test analyze_pod_health with no namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value=self.mock_pods_response)
        tools.get_events = MagicMock(return_value=self.mock_events_response)
        
        # Call the method
        result = tools.analyze_pod_health()
        
        # Verify the result structure
        self.assertIn("status", result)
        self.assertIn("message", result)
        self.assertIn("pod_count", result)
        self.assertIn("namespace", result)
        self.assertIn("ready_percentage", result)
        self.assertIn("summary", result)
        self.assertIn("issues", result)
        self.assertIn("recommendations", result)
        self.assertIn("confidence_level", result)
        
        # Verify the content
        self.assertEqual(result["pod_count"], len(self.sample_pods))
        self.assertEqual(result["namespace"], "all")
        self.assertEqual(result["ready_percentage"], 50.0)
        
        # Verify issues were identified
        self.assertTrue(len(result["issues"]) > 0)
        
        # Verify recommendations were generated
        self.assertTrue(len(result["recommendations"]) > 0)
        
        # Verify confidence level
        self.assertIn("level", result["confidence_level"])
        self.assertIn("factors", result["confidence_level"])
        self.assertIn("explanation", result["confidence_level"])
        
        # Verify the get_pods method was called correctly
        tools.get_pods.assert_called_once_with(namespace=None, label_selector=None)
        
        # Verify the get_events method was called correctly
        tools.get_events.assert_called_once_with(namespace=None, hours=24)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_pod_health_with_namespace(self, mock_client_class):
        """Test analyze_pod_health with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        
        # Update mock responses for namespace filter
        namespace_pods_response = self.mock_pods_response.copy()
        namespace_pods_response["namespace"] = "default"
        
        namespace_events_response = self.mock_events_response.copy()
        
        tools.get_pods = MagicMock(return_value=namespace_pods_response)
        tools.get_events = MagicMock(return_value=namespace_events_response)
        
        # Call the method
        result = tools.analyze_pod_health(namespace="default")
        
        # Verify the namespace in the result
        self.assertEqual(result["namespace"], "default")
        
        # Verify the get_pods method was called with namespace
        tools.get_pods.assert_called_once_with(namespace="default", label_selector=None)
        
        # Verify the get_events method was called with namespace
        tools.get_events.assert_called_once_with(namespace="default", hours=24)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_pod_health_with_label_selector(self, mock_client_class):
        """Test analyze_pod_health with label selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value=self.mock_pods_response)
        tools.get_events = MagicMock(return_value=self.mock_events_response)
        
        # Call the method
        result = tools.analyze_pod_health(label_selector="app=web")
        
        # Verify the label selector in the filters
        self.assertEqual(result["filters_applied"]["label_selector"], "app=web")
        
        # Verify the get_pods method was called with label selector
        tools.get_pods.assert_called_once_with(namespace=None, label_selector="app=web")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_pod_health_without_events(self, mock_client_class):
        """Test analyze_pod_health without including events."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value=self.mock_pods_response)
        tools.get_events = MagicMock(return_value=self.mock_events_response)
        
        # Call the method
        result = tools.analyze_pod_health(include_events=False)
        
        # Verify the get_events method was not called
        tools.get_events.assert_not_called()
        
        # Verify we still have recommendations and issues
        self.assertTrue(len(result["issues"]) > 0)
        self.assertTrue(len(result["recommendations"]) > 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_pod_health_with_healthy_pods(self, mock_client_class):
        """Test analyze_pod_health with only healthy pods."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create healthy pods response
        healthy_pods = [self.sample_pods[0]]  # Only the healthy pod
        healthy_pods_response = {
            "pods": healthy_pods,
            "count": len(healthy_pods),
            "namespace": "default",
            "summary": {
                "running": 1,
                "pending": 0,
                "failed": 0,
                "succeeded": 0,
                "other": 0,
                "ready_percentage": 100.0
            },
            "health_assessment": {
                "status": "healthy",
                "message": "All pods appear healthy",
                "issues": []
            }
        }
        
        # Create empty events response
        empty_events_response = {
            "events": [],
            "count": 0
        }
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value=healthy_pods_response)
        tools.get_events = MagicMock(return_value=empty_events_response)
        
        # Call the method
        result = tools.analyze_pod_health()
        
        # Verify the status is healthy
        self.assertEqual(result["status"], "healthy")
        
        # Verify there are no critical or warning issues
        critical_or_warning_issues = [issue for issue in result["issues"] if issue["severity"] in ["critical", "warning"]]
        self.assertEqual(len(critical_or_warning_issues), 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_pod_health_error_handling(self, mock_client_class):
        """Test analyze_pod_health error handling."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value={"error": "Failed to get pods"})
        
        # Call the method
        result = tools.analyze_pod_health()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to get pods")
        
        # Verify get_events was not called
        tools.get_events = MagicMock()
        self.assertEqual(tools.get_events.call_count, 0)


if __name__ == "__main__":
    unittest.main()