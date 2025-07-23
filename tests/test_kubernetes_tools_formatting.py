"""
Tests for Kubernetes resource formatting tool.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strands.kubernetes_tools import KubernetesTools
from src.k8s.client import KubernetesClientError


class TestKubernetesToolsFormatting(unittest.TestCase):
    """Test cases for Kubernetes resource formatting tool."""
    
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
                        "state": "Running",
                        "resources": {
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            },
                            "limits": {
                                "cpu": "200m",
                                "memory": "256Mi"
                            }
                        }
                    }
                ],
                "labels": {
                    "app": "web",
                    "tier": "frontend"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "pod-2",
                "namespace": "default",
                "status": "Pending",
                "ready": False,
                "restart_count": 3,
                "node_name": "node-2",
                "containers": [
                    {
                        "name": "container-2",
                        "image": "app:v1",
                        "ready": False,
                        "restart_count": 3,
                        "state": "Waiting: ContainerCreating",
                        "resources": {}
                    }
                ],
                "labels": {
                    "app": "api",
                    "tier": "backend"
                },
                "created_at": "2023-01-02T00:00:00Z"
            }
        ]
        
        # Sample deployment data for testing
        self.sample_deployments = [
            {
                "name": "deployment-1",
                "namespace": "default",
                "replicas": 3,
                "ready_replicas": 3,
                "available_replicas": 3,
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
                "created_at": "2023-01-01T00:00:00Z",
                "containers": [
                    {
                        "name": "web",
                        "image": "nginx:latest",
                        "resources": {
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            },
                            "limits": {
                                "cpu": "200m",
                                "memory": "256Mi"
                            }
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
                "ready_replicas": 1,
                "available_replicas": 1,
                "updated_replicas": 1,
                "unavailable_replicas": 1,
                "strategy": "Recreate",
                "selector": {
                    "app": "api"
                },
                "labels": {
                    "app": "api",
                    "tier": "backend"
                },
                "created_at": "2023-01-02T00:00:00Z",
                "containers": [
                    {
                        "name": "api",
                        "image": "app:v1",
                        "resources": {},
                        "liveness_probe": False,
                        "readiness_probe": False
                    }
                ]
            }
        ]
        
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
                        "protocol": "TCP"
                    }
                ],
                "selector": {
                    "app": "web"
                },
                "labels": {
                    "app": "web"
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
                    "app": "api"
                },
                "created_at": "2023-01-02T00:00:00Z"
            }
        ]
        
        # Sample event data for testing
        self.sample_events = [
            {
                "name": "pod-1.16b2f50d5df35106",
                "namespace": "default",
                "type": "Normal",
                "reason": "Started",
                "message": "Started container container-1",
                "involved_object": {
                    "kind": "Pod",
                    "name": "pod-1",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-01T00:00:00Z",
                "last_timestamp": "2023-01-01T00:00:00Z",
                "count": 1
            },
            {
                "name": "pod-2.16b2f50d5df35107",
                "namespace": "default",
                "type": "Warning",
                "reason": "Failed",
                "message": "Error: ImagePullBackOff",
                "involved_object": {
                    "kind": "Pod",
                    "name": "pod-2",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-02T00:00:00Z",
                "last_timestamp": "2023-01-02T00:01:00Z",
                "count": 3
            }
        ]
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_summary_pods(self, mock_client_class):
        """Test format_kubernetes_resources with summary format for pods."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.format_kubernetes_resources(self.sample_pods, "summary")
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertIn("SUMMARY OF PODS", result)
        self.assertIn("default/pod-1", result)
        self.assertIn("default/pod-2", result)
        self.assertIn("Running", result)
        self.assertIn("Pending", result)
        self.assertIn("node-1", result)
        self.assertIn("node-2", result)
        
        # Check for restart indicator
        self.assertIn("🔄 3", result)  # pod-2 has 3 restarts
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_summary_deployments(self, mock_client_class):
        """Test format_kubernetes_resources with summary format for deployments."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.format_kubernetes_resources(self.sample_deployments, "summary")
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertIn("SUMMARY OF DEPLOYMENTS", result)
        self.assertIn("default/deployment-1", result)
        self.assertIn("default/deployment-2", result)
        self.assertIn("3/3 ready", result)
        self.assertIn("1/2 ready", result)
        self.assertIn("RollingUpdate", result)
        self.assertIn("Recreate", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_detailed_pods(self, mock_client_class):
        """Test format_kubernetes_resources with detailed format for pods."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.format_kubernetes_resources(self.sample_pods, "detailed")
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertIn("DETAILED VIEW OF PODS", result)
        self.assertIn("Pod: default/pod-1", result)
        self.assertIn("Status: Running", result)
        self.assertIn("Ready: Yes", result)
        self.assertIn("Node: node-1", result)
        self.assertIn("Restart Count: 0", result)
        
        # Check for container details
        self.assertIn("Containers:", result)
        self.assertIn("container-1", result)
        self.assertIn("Image: nginx:latest", result)
        self.assertIn("State: Running", result)
        
        # Check for resource details
        self.assertIn("Resources:", result)
        self.assertIn("cpu: 100m", result)
        self.assertIn("memory: 128Mi", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_table_services(self, mock_client_class):
        """Test format_kubernetes_resources with table format for services."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.format_kubernetes_resources(self.sample_services, "table")
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertIn("NAMESPACE", result)
        self.assertIn("NAME", result)
        self.assertIn("TYPE", result)
        self.assertIn("CLUSTER-IP", result)
        self.assertIn("PORTS", result)
        
        # Check for service details
        self.assertIn("default", result)
        self.assertIn("service-1", result)
        self.assertIn("service-2", result)
        self.assertIn("ClusterIP", result)
        self.assertIn("NodePort", result)
        self.assertIn("10.0.0.1", result)
        self.assertIn("10.0.0.2", result)
        self.assertIn("80->8080/TCP", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_yaml(self, mock_client_class):
        """Test format_kubernetes_resources with YAML format."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.format_kubernetes_resources(self.sample_events, "yaml")
        
        # Verify the result
        self.assertIsInstance(result, str)
        
        # Check if it contains YAML content or the import error message
        if "YAML formatting not available" not in result:
            self.assertIn("name: pod-1.16b2f50d5df35106", result)
            self.assertIn("namespace: default", result)
            self.assertIn("type: Normal", result)
            self.assertIn("reason: Started", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_json(self, mock_client_class):
        """Test format_kubernetes_resources with JSON format."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.format_kubernetes_resources(self.sample_events, "json")
        
        # Verify the result
        self.assertIsInstance(result, str)
        
        # Parse the JSON and verify
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "pod-1.16b2f50d5df35106")
        self.assertEqual(parsed[0]["type"], "Normal")
        self.assertEqual(parsed[1]["name"], "pod-2.16b2f50d5df35107")
        self.assertEqual(parsed[1]["type"], "Warning")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_invalid_format(self, mock_client_class):
        """Test format_kubernetes_resources with invalid format type."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with invalid format
        result = tools.format_kubernetes_resources(self.sample_pods, "invalid_format")
        
        # Verify the result contains an error
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Unsupported format type", result["error"])
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_format_kubernetes_resources_invalid_inputs(self, mock_client_class):
        """Test format_kubernetes_resources with invalid inputs."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Test with non-list resources
        result = tools.format_kubernetes_resources("not a list", "summary")
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("resources must be a list", result["error"])
        
        # Test with non-string format_type
        result = tools.format_kubernetes_resources(self.sample_pods, 123)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("format_type must be a string", result["error"])
        
        # Test with empty resources list
        result = tools.format_kubernetes_resources([], "summary")
        self.assertEqual(result, "No resources to format.")


if __name__ == "__main__":
    unittest.main()