"""
Tests for Kubernetes deployment tools for AWS Strands integration.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesDeploymentTools(unittest.TestCase):
    """Test cases for Kubernetes deployment tools."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample deployment data for testing
        self.sample_deployments = [
            {
                "name": "deployment-1",
                "namespace": "default",
                "replicas": 3,
                "available_replicas": 3,
                "ready_replicas": 3,
                "updated_replicas": 3,
                "unavailable_replicas": 0,
                "strategy": "RollingUpdate",
                "selector": {
                    "app": "web"
                },
                "labels": {
                    "app": "web",
                    "tier": "frontend"
                },
                "annotations": {},
                "containers": [
                    {
                        "name": "container-1",
                        "image": "nginx:latest",
                        "ports": [{"container_port": 80, "protocol": "TCP", "name": "http"}],
                        "resources": {
                            "limits": {"cpu": "500m", "memory": "512Mi"},
                            "requests": {"cpu": "250m", "memory": "256Mi"}
                        },
                        "liveness_probe": True,
                        "readiness_probe": True
                    }
                ]
            },
            {
                "name": "deployment-2",
                "namespace": "default",
                "replicas": 2,
                "available_replicas": 1,
                "ready_replicas": 1,
                "updated_replicas": 1,
                "unavailable_replicas": 1,
                "strategy": "RollingUpdate",
                "selector": {
                    "app": "cache"
                },
                "labels": {
                    "app": "cache",
                    "tier": "backend"
                },
                "annotations": {},
                "containers": [
                    {
                        "name": "container-2",
                        "image": "redis:latest",
                        "ports": [{"container_port": 6379, "protocol": "TCP", "name": "redis"}],
                        "resources": {},
                        "liveness_probe": False,
                        "readiness_probe": False
                    }
                ]
            },
            {
                "name": "deployment-3",
                "namespace": "kube-system",
                "replicas": 1,
                "available_replicas": 1,
                "ready_replicas": 1,
                "updated_replicas": 1,
                "unavailable_replicas": 0,
                "strategy": "Recreate",
                "selector": {
                    "k8s-app": "kube-dns"
                },
                "labels": {
                    "k8s-app": "kube-dns"
                },
                "annotations": {},
                "containers": [
                    {
                        "name": "container-3",
                        "image": "k8s.gcr.io/kube-dns:1.21.0",
                        "ports": [],
                        "resources": {},
                        "liveness_probe": True,
                        "readiness_probe": True
                    }
                ]
            }
        ]
        
        # Configure the mock to return sample data
        self.mock_k8s_client.list_deployments.return_value = self.sample_deployments
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_all_namespaces(self, mock_client_class):
        """Test get_deployments with no namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments()
        
        # Verify the result
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["namespace"], "all")
        self.assertEqual(result["summary"]["healthy"], 2)
        self.assertEqual(result["summary"]["scaling"], 1)
        self.assertEqual(result["summary"]["zero_replicas"], 0)
        self.assertEqual(len(result["deployments"]), 3)
        self.assertIn("health_assessment", result)
        self.assertIn("availability_percentage", result["summary"])
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_deployments.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_with_namespace(self, mock_client_class):
        """Test get_deployments with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Filter the sample data for the mock response
        filtered_deployments = [d for d in self.sample_deployments if d["namespace"] == "default"]
        self.mock_k8s_client.list_deployments.return_value = filtered_deployments
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments(namespace="default")
        
        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["summary"]["healthy"], 1)
        self.assertEqual(result["summary"]["scaling"], 1)
        self.assertEqual(len(result["deployments"]), 2)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_deployments.assert_called_once_with("default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_with_label_selector(self, mock_client_class):
        """Test get_deployments with label selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments(label_selector="app=web")
        
        # Verify the result
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["filters_applied"]["label_selector"], "app=web")
        self.assertEqual(result["summary"]["healthy"], 1)
        self.assertEqual(result["summary"]["scaling"], 0)
        self.assertEqual(len(result["deployments"]), 1)
        self.assertEqual(result["deployments"][0]["name"], "deployment-1")
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_deployments.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_with_field_selector(self, mock_client_class):
        """Test get_deployments with field selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments(field_selector="metadata.name=deployment-1")
        
        # Verify the result
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["filters_applied"]["field_selector"], "metadata.name=deployment-1")
        self.assertEqual(result["summary"]["healthy"], 1)
        self.assertEqual(result["summary"]["scaling"], 0)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_deployments.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_with_limit(self, mock_client_class):
        """Test get_deployments with limit."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments(limit=2)
        
        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["filters_applied"]["limit"], 2)
        self.assertEqual(len(result["deployments"]), 2)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_deployments.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_health_assessment(self, mock_client_class):
        """Test get_deployments health assessment."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create deployment with scaling issues
        scaling_deployment = {
            "name": "deployment-4",
            "namespace": "default",
            "replicas": 5,
            "available_replicas": 2,
            "ready_replicas": 2,
            "updated_replicas": 2,
            "unavailable_replicas": 3,
            "strategy": "RollingUpdate",
            "selector": {},
            "labels": {},
            "annotations": {},
            "containers": []
        }
        
        # Add the scaling deployment to the sample deployments
        test_deployments = self.sample_deployments + [scaling_deployment]
        self.mock_k8s_client.list_deployments.return_value = test_deployments
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments()
        
        # Verify the health assessment
        self.assertIn("health_assessment", result)
        self.assertIn("status", result["health_assessment"])
        self.assertIn("issues", result["health_assessment"])
        
        # Check that unavailable replicas issue is detected
        issues = result["health_assessment"]["issues"]
        unavailable_issue = next((issue for issue in issues if issue["type"] == "unavailable_replicas"), None)
        self.assertIsNotNone(unavailable_issue)
        
        # Check that the affected deployments include our test deployment
        affected_deployments = [d["deployment"] for d in unavailable_issue["affected_deployments"]]
        self.assertIn("default/deployment-4", affected_deployments)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_deployments_error_handling(self, mock_client_class):
        """Test get_deployments error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.list_deployments.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_deployments()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)


if __name__ == "__main__":
    unittest.main()