"""
Tests for Kubernetes pod tools for AWS Strands integration.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesPodTools(unittest.TestCase):
    """Test cases for Kubernetes pod tools."""
    
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
                "name": "pod-1",
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
                "name": "pod-2",
                "namespace": "default",
                "status": "Pending",
                "ready": False,
                "restart_count": 0,
                "node_name": "node-1",
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
                "name": "pod-3",
                "namespace": "kube-system",
                "status": "Running",
                "ready": True,
                "restart_count": 2,
                "node_name": "node-2",
                "containers": [
                    {
                        "name": "container-3",
                        "image": "k8s.gcr.io/kube-proxy:v1.21.0",
                        "ready": True,
                        "restart_count": 2,
                        "state": "Running"
                    }
                ],
                "labels": {
                    "k8s-app": "kube-proxy"
                },
                "annotations": {}
            }
        ]
        
        # Configure the mock to return sample data
        self.mock_k8s_client.list_pods.return_value = self.sample_pods
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_all_namespaces(self, mock_client_class):
        """Test get_pods with no namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods()
        
        # Verify the result
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["namespace"], "all")
        self.assertEqual(result["summary"]["running"], 2)
        self.assertEqual(result["summary"]["pending"], 1)
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertEqual(len(result["pods"]), 3)
        self.assertIn("health_assessment", result)
        self.assertIn("ready_percentage", result["summary"])
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_pods.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_with_namespace(self, mock_client_class):
        """Test get_pods with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Filter the sample data for the mock response
        filtered_pods = [pod for pod in self.sample_pods if pod["namespace"] == "default"]
        self.mock_k8s_client.list_pods.return_value = filtered_pods
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods(namespace="default")
        
        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["summary"]["running"], 1)
        self.assertEqual(result["summary"]["pending"], 1)
        self.assertEqual(len(result["pods"]), 2)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_pods.assert_called_once_with("default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_with_label_selector(self, mock_client_class):
        """Test get_pods with label selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods(label_selector="app=web")
        
        # Verify the result
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["filters_applied"]["label_selector"], "app=web")
        self.assertEqual(result["summary"]["running"], 1)
        self.assertEqual(result["summary"]["pending"], 0)
        self.assertEqual(len(result["pods"]), 1)
        self.assertEqual(result["pods"][0]["name"], "pod-1")
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_pods.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_with_field_selector(self, mock_client_class):
        """Test get_pods with field selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods(field_selector="status.phase=Running")
        
        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["filters_applied"]["field_selector"], "status.phase=Running")
        self.assertEqual(result["summary"]["running"], 2)
        self.assertEqual(result["summary"]["pending"], 0)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_pods.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_with_limit(self, mock_client_class):
        """Test get_pods with limit."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods(limit=2)
        
        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["filters_applied"]["limit"], 2)
        self.assertEqual(len(result["pods"]), 2)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_pods.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_health_assessment(self, mock_client_class):
        """Test get_pods health assessment."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create pod with high restart count
        high_restart_pod = {
            "name": "pod-4",
            "namespace": "default",
            "status": "Running",
            "ready": True,
            "restart_count": 10,
            "node_name": "node-1",
            "containers": [],
            "labels": {},
            "annotations": {}
        }
        
        # Add the high restart pod to the sample pods
        test_pods = self.sample_pods + [high_restart_pod]
        self.mock_k8s_client.list_pods.return_value = test_pods
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods()
        
        # Verify the health assessment
        self.assertIn("health_assessment", result)
        self.assertIn("status", result["health_assessment"])
        self.assertIn("issues", result["health_assessment"])
        
        # Check that high restart issue is detected
        issues = result["health_assessment"]["issues"]
        high_restart_issue = next((issue for issue in issues if issue["type"] == "high_restarts"), None)
        self.assertIsNotNone(high_restart_issue)
        self.assertIn("pod-4", high_restart_issue["affected_pods"])
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_pods_error_handling(self, mock_client_class):
        """Test get_pods error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.list_pods.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_pods()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)


if __name__ == "__main__":
    unittest.main()