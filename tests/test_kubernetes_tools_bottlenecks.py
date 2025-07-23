"""
Tests for Kubernetes resource bottleneck analysis tool.
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


class TestKubernetesToolsBottlenecks(unittest.TestCase):
    """Test cases for Kubernetes resource bottleneck analysis tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample metrics data for testing
        self.sample_metrics = {
            "nodes": {
                "node-1": {
                    "cpu": {
                        "capacity": 8,
                        "allocatable": 7.5,
                        "requests": 4.5,
                        "limits": 6.0,
                        "usage": 3.2
                    },
                    "memory": {
                        "capacity": 16 * 1024 * 1024 * 1024,  # 16Gi
                        "allocatable": 14 * 1024 * 1024 * 1024,  # 14Gi
                        "requests": 8 * 1024 * 1024 * 1024,  # 8Gi
                        "limits": 12 * 1024 * 1024 * 1024,  # 12Gi
                        "usage": 7 * 1024 * 1024 * 1024  # 7Gi
                    },
                    "conditions": {
                        "Ready": {
                            "status": "True",
                            "reason": "KubeletReady",
                            "message": "kubelet is posting ready status"
                        }
                    },
                    "pods": ["default/pod-1", "kube-system/pod-3"]
                },
                "node-2": {
                    "cpu": {
                        "capacity": 8,
                        "allocatable": 7.5,
                        "requests": 6.5,
                        "limits": 7.0,
                        "usage": 5.8
                    },
                    "memory": {
                        "capacity": 16 * 1024 * 1024 * 1024,  # 16Gi
                        "allocatable": 14 * 1024 * 1024 * 1024,  # 14Gi
                        "requests": 12 * 1024 * 1024 * 1024,  # 12Gi
                        "limits": 13 * 1024 * 1024 * 1024,  # 13Gi
                        "usage": 11 * 1024 * 1024 * 1024  # 11Gi
                    },
                    "conditions": {
                        "Ready": {
                            "status": "True",
                            "reason": "KubeletReady",
                            "message": "kubelet is posting ready status"
                        }
                    },
                    "pods": ["default/pod-2"]
                }
            },
            "pods": {
                "default/pod-1": {
                    "name": "pod-1",
                    "namespace": "default",
                    "node": "node-1",
                    "status": "Running",
                    "cpu": {
                        "requests": 2.0,
                        "limits": 3.0,
                        "usage": 1.5
                    },
                    "memory": {
                        "requests": 4 * 1024 * 1024 * 1024,  # 4Gi
                        "limits": 6 * 1024 * 1024 * 1024,  # 6Gi
                        "usage": 3.5 * 1024 * 1024 * 1024  # 3.5Gi
                    },
                    "containers": []
                },
                "default/pod-2": {
                    "name": "pod-2",
                    "namespace": "default",
                    "node": "node-2",
                    "status": "Running",
                    "cpu": {
                        "requests": 6.5,
                        "limits": 7.0,
                        "usage": 5.8
                    },
                    "memory": {
                        "requests": 12 * 1024 * 1024 * 1024,  # 12Gi
                        "limits": 13 * 1024 * 1024 * 1024,  # 13Gi
                        "usage": 11 * 1024 * 1024 * 1024  # 11Gi
                    },
                    "containers": []
                },
                "kube-system/pod-3": {
                    "name": "pod-3",
                    "namespace": "kube-system",
                    "node": "node-1",
                    "status": "Running",
                    "cpu": {
                        "requests": 2.5,
                        "limits": 3.0,
                        "usage": 1.7
                    },
                    "memory": {
                        "requests": 4 * 1024 * 1024 * 1024,  # 4Gi
                        "limits": 6 * 1024 * 1024 * 1024,  # 6Gi
                        "usage": 3.5 * 1024 * 1024 * 1024  # 3.5Gi
                    },
                    "containers": []
                }
            },
            "namespaces": {
                "default": {
                    "cpu": {
                        "requests": 8.5,
                        "limits": 10.0,
                        "usage": 7.3
                    },
                    "memory": {
                        "requests": 16 * 1024 * 1024 * 1024,  # 16Gi
                        "limits": 19 * 1024 * 1024 * 1024,  # 19Gi
                        "usage": 14.5 * 1024 * 1024 * 1024  # 14.5Gi
                    },
                    "pod_count": 2
                },
                "kube-system": {
                    "cpu": {
                        "requests": 2.5,
                        "limits": 3.0,
                        "usage": 1.7
                    },
                    "memory": {
                        "requests": 4 * 1024 * 1024 * 1024,  # 4Gi
                        "limits": 6 * 1024 * 1024 * 1024,  # 6Gi
                        "usage": 3.5 * 1024 * 1024 * 1024  # 3.5Gi
                    },
                    "pod_count": 1
                }
            },
            "cluster_totals": {
                "cpu": {
                    "capacity": 16,
                    "allocatable": 15,
                    "requests": 11,
                    "limits": 13,
                    "usage": 9
                },
                "memory": {
                    "capacity": 32 * 1024 * 1024 * 1024,  # 32Gi
                    "allocatable": 28 * 1024 * 1024 * 1024,  # 28Gi
                    "requests": 20 * 1024 * 1024 * 1024,  # 20Gi
                    "limits": 25 * 1024 * 1024 * 1024,  # 25Gi
                    "usage": 18 * 1024 * 1024 * 1024  # 18Gi
                }
            },
            "summary": {
                "node_count": 2,
                "pod_count": 3,
                "namespace_count": 2,
                "cpu_request_percentage": 73.3,
                "memory_request_percentage": 71.4,
                "cpu_limit_percentage": 86.7,
                "memory_limit_percentage": 89.3
            }
        }
        
        # Configure the mock to return sample data
        self.mock_k8s_client.get_resource_metrics.return_value = self.sample_metrics
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_identify_resource_bottlenecks_normal(self, mock_client_class):
        """Test identify_resource_bottlenecks with normal utilization."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with default threshold (80%)
        result = tools.identify_resource_bottlenecks()
        
        # Verify the result structure
        self.assertIn("status", result)
        self.assertIn("message", result)
        self.assertIn("bottleneck_count", result)
        self.assertIn("bottlenecks", result)
        self.assertIn("recommendations", result)
        self.assertIn("threshold_percentage", result)
        
        # Check bottlenecks structure
        self.assertIn("cpu", result["bottlenecks"])
        self.assertIn("memory", result["bottlenecks"])
        self.assertIn("disk", result["bottlenecks"])
        self.assertIn("network", result["bottlenecks"])
        self.assertIn("pods", result["bottlenecks"])
        
        # With our sample data and 80% threshold, we should have some bottlenecks
        # CPU limits are at 86.7% and memory limits are at 89.3%
        self.assertTrue(len(result["bottlenecks"]["cpu"]) > 0 or len(result["bottlenecks"]["memory"]) > 0)
        
        # Check that recommendations are provided
        self.assertTrue(len(result["recommendations"]) > 0)
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_resource_metrics.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_identify_resource_bottlenecks_high_threshold(self, mock_client_class):
        """Test identify_resource_bottlenecks with high threshold."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with high threshold (95%)
        result = tools.identify_resource_bottlenecks(threshold_percentage=95)
        
        # With our sample data and 95% threshold, we should have no bottlenecks
        self.assertEqual(result["bottleneck_count"], 0)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(len(result["bottlenecks"]["cpu"]), 0)
        self.assertEqual(len(result["bottlenecks"]["memory"]), 0)
        
        # Verify the threshold was applied
        self.assertEqual(result["threshold_percentage"], 95)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_identify_resource_bottlenecks_critical(self, mock_client_class):
        """Test identify_resource_bottlenecks with critical utilization."""
        # Configure the mock with high utilization data
        high_util_metrics = self.sample_metrics.copy()
        high_util_metrics["summary"]["cpu_request_percentage"] = 95.0
        high_util_metrics["summary"]["memory_request_percentage"] = 92.0
        high_util_metrics["cluster_totals"]["cpu"]["requests"] = 14.25  # 95% of 15
        high_util_metrics["cluster_totals"]["memory"]["requests"] = 25.76 * 1024 * 1024 * 1024  # 92% of 28Gi
        
        self.mock_k8s_client.get_resource_metrics.return_value = high_util_metrics
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.identify_resource_bottlenecks()
        
        # Verify critical status
        self.assertEqual(result["status"], "critical")
        self.assertTrue("Critical resource bottlenecks detected" in result["message"])
        
        # Check that we have CPU and memory bottlenecks
        self.assertTrue(len(result["bottlenecks"]["cpu"]) > 0)
        self.assertTrue(len(result["bottlenecks"]["memory"]) > 0)
        
        # Check that high priority recommendations are provided
        high_priority_recs = [r for r in result["recommendations"] if r["priority"] == "high"]
        self.assertTrue(len(high_priority_recs) > 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_identify_resource_bottlenecks_with_namespace(self, mock_client_class):
        """Test identify_resource_bottlenecks with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create filtered metrics for the mock response
        filtered_metrics = self.sample_metrics.copy()
        filtered_metrics["namespace_filter"] = "default"
        self.mock_k8s_client.get_resource_metrics.return_value = filtered_metrics
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with namespace filter
        result = tools.identify_resource_bottlenecks(namespace="default")
        
        # Verify the namespace filter was applied
        self.assertIn("namespace", result)
        self.assertEqual(result["namespace"], "default")
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_resource_metrics.assert_called_once_with("default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_identify_resource_bottlenecks_error_handling(self, mock_client_class):
        """Test identify_resource_bottlenecks error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.get_resource_metrics.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.identify_resource_bottlenecks()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_identify_resource_bottlenecks_invalid_inputs(self, mock_client_class):
        """Test identify_resource_bottlenecks with invalid inputs."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Test with invalid namespace
        result = tools.identify_resource_bottlenecks(namespace=123)
        self.assertIn("error", result)
        self.assertIn("namespace must be a string", result["error"])
        
        # Test with invalid threshold
        result = tools.identify_resource_bottlenecks(threshold_percentage="invalid")
        self.assertIn("error", result)
        self.assertIn("threshold_percentage must be a valid integer", result["error"])
        
        # Test with out-of-range threshold
        result = tools.identify_resource_bottlenecks(threshold_percentage=101)
        self.assertIn("error", result)
        self.assertIn("threshold_percentage must be between 0 and 100", result["error"])


if __name__ == "__main__":
    unittest.main()