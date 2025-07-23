"""
Tests for Kubernetes resource metrics tools.
"""

import unittest
from unittest.mock import MagicMock, patch
import json

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesToolsMetrics(unittest.TestCase):
    """Test cases for Kubernetes resource metrics tools."""
    
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
    def test_get_resource_metrics_all_namespaces(self, mock_client_class):
        """Test get_resource_metrics with no namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_resource_metrics()
        
        # Verify the result
        self.assertIn("nodes", result)
        self.assertIn("pods", result)
        self.assertIn("namespaces", result)
        self.assertIn("cluster_totals", result)
        self.assertIn("summary", result)
        self.assertIn("analysis", result)
        
        # Check summary data
        self.assertEqual(result["summary"]["node_count"], 2)
        self.assertEqual(result["summary"]["pod_count"], 3)
        self.assertEqual(result["summary"]["namespace_count"], 2)
        self.assertEqual(result["summary"]["cpu_request_percentage"], 73.3)
        self.assertEqual(result["summary"]["memory_request_percentage"], 71.4)
        
        # Check analysis
        self.assertIn("status", result["analysis"])
        self.assertIn("message", result["analysis"])
        self.assertIn("issues", result["analysis"])
        self.assertIn("recommendations", result["analysis"])
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_resource_metrics.assert_called_once_with(None)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_resource_metrics_with_namespace(self, mock_client_class):
        """Test get_resource_metrics with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create filtered metrics for the mock response
        filtered_metrics = self.sample_metrics.copy()
        filtered_metrics["namespace_filter"] = "default"
        self.mock_k8s_client.get_resource_metrics.return_value = filtered_metrics
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_resource_metrics(namespace="default")
        
        # Verify the result
        self.assertIn("namespace_filter", result)
        self.assertEqual(result["namespace_filter"], "default")
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_resource_metrics.assert_called_once_with("default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_resource_metrics_high_utilization(self, mock_client_class):
        """Test get_resource_metrics with high utilization."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create high utilization metrics for the mock response
        high_util_metrics = self.sample_metrics.copy()
        high_util_metrics["summary"]["cpu_request_percentage"] = 95.0
        high_util_metrics["summary"]["memory_request_percentage"] = 92.0
        self.mock_k8s_client.get_resource_metrics.return_value = high_util_metrics
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_resource_metrics()
        
        # Verify the analysis shows critical status
        self.assertEqual(result["analysis"]["status"], "critical")
        self.assertTrue(any(issue["type"] == "high_cpu_utilization" for issue in result["analysis"]["issues"]))
        self.assertTrue(any(issue["type"] == "high_memory_utilization" for issue in result["analysis"]["issues"]))
        self.assertTrue(len(result["analysis"]["recommendations"]) > 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_get_resource_metrics_error_handling(self, mock_client_class):
        """Test get_resource_metrics error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.get_resource_metrics.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.get_resource_metrics()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)


if __name__ == "__main__":
    unittest.main()