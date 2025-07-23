"""
Tests for Kubernetes service tools for AWS Strands integration.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesServiceTools(unittest.TestCase):
    """Test cases for Kubernetes service tools."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample service data for testing
        self.sample_services = [
            {
                "name": "service-1",
                "namespace": "default",
                "type": "ClusterIP",
                "cluster_ip": "10.0.0.1",
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "target_port": 8080,
                        "protocol": "TCP",
                        "node_port": None
                    }
                ],
                "selector": {
                    "app": "web"
                },
                "labels": {
                    "app": "web",
                    "tier": "frontend"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "service-2",
                "namespace": "default",
                "type": "NodePort",
                "cluster_ip": "10.0.0.2",
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "target_port": 8080,
                        "protocol": "TCP",
                        "node_port": 30080
                    }
                ],
                "selector": {
                    "app": "api"
                },
                "labels": {
                    "app": "api",
                    "tier": "backend"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "service-3",
                "namespace": "kube-system",
                "type": "ClusterIP",
                "cluster_ip": "10.0.0.3",
                "ports": [
                    {
                        "name": "dns",
                        "port": 53,
                        "target_port": 53,
                        "protocol": "UDP",
                        "node_port": None
                    }
                ],
                "selector": {
                    "k8s-app": "kube-dns"
                },
                "labels": {
                    "k8s-app": "kube-dns"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "service-4",
                "namespace": "default",
                "type": "LoadBalancer",
                "cluster_ip": "10.0.0.4",
                "external_ip": "203.0.113.1",
                "ports": [
                    {
                        "name": "https",
                        "port": 443,
                        "target_port": 8443,
                        "protocol": "TCP",
                        "node_port": 30443
                    }
                ],
                "selector": {
                    "app": "web"
                },
                "labels": {
                    "app": "web",
                    "tier": "frontend"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "service-5",
                "namespace": "default",
                "type": "LoadBalancer",
                "cluster_ip": "10.0.0.5",
                "external_ip": None,  # Pending LoadBalancer
                "ports": [
                    {
                        "name": "https",
                        "port": 443,
                        "target_port": 8443,
                        "protocol": "TCP",
                        "node_port": 30444
                    }
                ],
                "selector": {
                    "app": "api"
                },
                "labels": {
                    "app": "api",
                    "tier": "backend"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "service-6",
                "namespace": "default",
                "type": "ClusterIP",
                "cluster_ip": "10.0.0.6",
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "target_port": 8080,
                        "protocol": "TCP",
                        "node_port": None
                    }
                ],
                "selector": {},  # No selector
                "labels": {
                    "app": "headless"
                },
                "created_at": "2023-01-01T00:00:00Z"
            }
        ]
        
        # Configure the mock to return sample data
        self.mock_k8s_client.list_services.return_value = self.sample_services
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_all_namespaces(self, mock_client_class):
        """Test get_services with no namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services()
        
        # Verify the result
        self.assertEqual(result["count"], 6)
        self.assertEqual(result["namespace"], "all")
        self.assertEqual(result["summary"]["clusterip"], 3)
        self.assertEqual(result["summary"]["nodeport"], 1)
        self.assertEqual(result["summary"]["loadbalancer"], 2)
        self.assertEqual(result["summary"]["externalname"], 0)
        self.assertEqual(len(result["services"]), 6)
        self.assertIn("health_assessment", result)
        self.assertIn("exposed_percentage", result["summary"])
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_services.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_with_namespace(self, mock_client_class):
        """Test get_services with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Filter the sample data for the mock response
        filtered_services = [s for s in self.sample_services if s["namespace"] == "default"]
        self.mock_k8s_client.list_services.return_value = filtered_services
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services(namespace="default")
        
        # Verify the result
        self.assertEqual(result["count"], 5)
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["summary"]["clusterip"], 2)
        self.assertEqual(result["summary"]["nodeport"], 1)
        self.assertEqual(result["summary"]["loadbalancer"], 2)
        self.assertEqual(len(result["services"]), 5)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_services.assert_called_once_with("default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_with_label_selector(self, mock_client_class):
        """Test get_services with label selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services(label_selector="app=web")
        
        # Verify the result
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["filters_applied"]["label_selector"], "app=web")
        self.assertEqual(len(result["services"]), 2)
        self.assertEqual(result["services"][0]["name"], "service-1")
        self.assertEqual(result["services"][1]["name"], "service-4")
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_services.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_with_field_selector(self, mock_client_class):
        """Test get_services with field selector."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services(field_selector="metadata.name=service-1")
        
        # Verify the result
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["filters_applied"]["field_selector"], "metadata.name=service-1")
        self.assertEqual(len(result["services"]), 1)
        self.assertEqual(result["services"][0]["name"], "service-1")
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_services.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_with_limit(self, mock_client_class):
        """Test get_services with limit."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services(limit=3)
        
        # Verify the result
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["filters_applied"]["limit"], 3)
        self.assertEqual(len(result["services"]), 3)
        
        # Verify the client was called correctly
        self.mock_k8s_client.list_services.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_health_assessment(self, mock_client_class):
        """Test get_services health assessment."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services()
        
        # Verify the health assessment
        self.assertIn("health_assessment", result)
        self.assertIn("status", result["health_assessment"])
        self.assertIn("issues", result["health_assessment"])
        
        # Check that pending LoadBalancer issue is detected
        issues = result["health_assessment"]["issues"]
        pending_lb_issue = next((issue for issue in issues if issue["type"] == "pending_loadbalancer"), None)
        self.assertIsNotNone(pending_lb_issue)
        self.assertIn("default/service-5", pending_lb_issue["affected_services"])
        
        # Check that no selector issue is detected
        no_selector_issue = next((issue for issue in issues if issue["type"] == "no_selector"), None)
        self.assertIsNotNone(no_selector_issue)
        self.assertIn("default/service-6", no_selector_issue["affected_services"])
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_services_error_handling(self, mock_client_class):
        """Test get_services error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.list_services.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_services()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)


if __name__ == "__main__":
    unittest.main()