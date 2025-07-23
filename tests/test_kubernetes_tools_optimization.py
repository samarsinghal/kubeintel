"""
Tests for Kubernetes optimization recommendations tool.
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


class TestKubernetesToolsOptimization(unittest.TestCase):
    """Test cases for Kubernetes optimization recommendations tool."""
    
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
                        "usage": 0.3  # Low usage compared to request
                    },
                    "memory": {
                        "requests": 4 * 1024 * 1024 * 1024,  # 4Gi
                        "limits": 6 * 1024 * 1024 * 1024,  # 6Gi
                        "usage": 1 * 1024 * 1024 * 1024  # 1Gi - Low usage compared to request
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
                        "usage": 5.8  # High usage compared to request
                    },
                    "memory": {
                        "requests": 12 * 1024 * 1024 * 1024,  # 12Gi
                        "limits": 13 * 1024 * 1024 * 1024,  # 13Gi
                        "usage": 11 * 1024 * 1024 * 1024  # 11Gi - High usage compared to request
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
                        "usage": 6.1
                    },
                    "memory": {
                        "requests": 16 * 1024 * 1024 * 1024,  # 16Gi
                        "limits": 19 * 1024 * 1024 * 1024,  # 19Gi
                        "usage": 12 * 1024 * 1024 * 1024  # 12Gi
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
                    "usage": 7.8
                },
                "memory": {
                    "capacity": 32 * 1024 * 1024 * 1024,  # 32Gi
                    "allocatable": 28 * 1024 * 1024 * 1024,  # 28Gi
                    "requests": 20 * 1024 * 1024 * 1024,  # 20Gi
                    "limits": 25 * 1024 * 1024 * 1024,  # 25Gi
                    "usage": 15.5 * 1024 * 1024 * 1024  # 15.5Gi
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
        
        # Sample pods data with more details
        self.sample_pods = [
            {
                "name": "pod-1",
                "namespace": "default",
                "status": "Running",
                "node_name": "node-1",
                "restart_count": 0,
                "containers": [
                    {
                        "name": "container-1",
                        "image": "nginx:latest",
                        "ready": True,
                        "restart_count": 0,
                        "state": "Running",
                        "resources": {
                            "requests": {
                                "cpu": "2",
                                "memory": "4Gi"
                            },
                            "limits": {
                                "cpu": "3",
                                "memory": "6Gi"
                            }
                        },
                        "liveness_probe": False,
                        "readiness_probe": False
                    }
                ],
                "volumes": [
                    {
                        "name": "data",
                        "host_path": {
                            "path": "/data"
                        }
                    }
                ],
                "host_network": True,
                "security_context": {}
            },
            {
                "name": "pod-2",
                "namespace": "default",
                "status": "Running",
                "node_name": "node-2",
                "restart_count": 7,
                "containers": [
                    {
                        "name": "container-2",
                        "image": "app:v1",
                        "ready": True,
                        "restart_count": 7,
                        "state": "Running",
                        "resources": {
                            "requests": {
                                "cpu": "6.5",
                                "memory": "12Gi"
                            },
                            "limits": {
                                "cpu": "7",
                                "memory": "13Gi"
                            }
                        },
                        "liveness_probe": True,
                        "readiness_probe": True
                    }
                ],
                "security_context": {
                    "run_as_non_root": True
                }
            },
            {
                "name": "pod-3",
                "namespace": "kube-system",
                "status": "Running",
                "node_name": "node-1",
                "restart_count": 0,
                "containers": [
                    {
                        "name": "container-3",
                        "image": "system:v1",
                        "ready": True,
                        "restart_count": 0,
                        "state": "Running",
                        "resources": {
                            "requests": {
                                "cpu": "2.5",
                                "memory": "4Gi"
                            },
                            "limits": {
                                "cpu": "3",
                                "memory": "6Gi"
                            }
                        },
                        "security_context": {
                            "privileged": True
                        }
                    }
                ]
            }
        ]
        
        # Sample deployments data
        self.sample_deployments = [
            {
                "name": "deployment-1",
                "namespace": "default",
                "replicas": 1,
                "available_replicas": 1,
                "ready_replicas": 1,
                "updated_replicas": 1,
                "unavailable_replicas": 0,
                "strategy": "RollingUpdate",
                "selector": {
                    "app": "app-1"
                },
                "labels": {
                    "app": "app-1"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "deployment-2",
                "namespace": "default",
                "replicas": 3,
                "available_replicas": 3,
                "ready_replicas": 3,
                "updated_replicas": 3,
                "unavailable_replicas": 0,
                "strategy": "RollingUpdate",
                "selector": {
                    "app": "app-2"
                },
                "labels": {
                    "app": "app-2"
                },
                "created_at": "2023-01-01T00:00:00Z"
            }
        ]
        
        # Sample services data
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
                    "app": "app-1"
                },
                "labels": {
                    "app": "app-1"
                },
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "name": "service-2",
                "namespace": "default",
                "type": "ClusterIP",
                "cluster_ip": "10.0.0.2",
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "target_port": 8080,
                        "protocol": "TCP"
                    }
                ],
                "selector": {},  # No selector
                "labels": {
                    "app": "app-2"
                },
                "created_at": "2023-01-01T00:00:00Z"
            }
        ]
        
        # Sample events data
        self.sample_events = [
            {
                "name": "pod-2.16b2f50d5df35106",
                "namespace": "default",
                "type": "Warning",
                "reason": "Evicted",
                "message": "Pod was evicted due to memory pressure",
                "involved_object": {
                    "kind": "Pod",
                    "name": "pod-2",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-01T00:00:00Z",
                "last_timestamp": "2023-01-01T00:00:00Z",
                "count": 1
            }
        ]
        
        # Configure the mock to return sample data
        self.mock_k8s_client.get_resource_metrics.return_value = self.sample_metrics
        self.mock_k8s_client.list_pods.return_value = self.sample_pods
        self.mock_k8s_client.list_deployments.return_value = self.sample_deployments
        self.mock_k8s_client.list_services.return_value = self.sample_services
        self.mock_k8s_client.list_events.return_value = self.sample_events
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations(self, mock_client_class):
        """Test generate_optimization_recommendations with normal data."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.generate_optimization_recommendations()
        
        # Verify the result structure
        self.assertIn("status", result)
        self.assertIn("message", result)
        self.assertIn("total_recommendations", result)
        self.assertIn("recommendations", result)
        
        # Check recommendations structure
        self.assertIn("resource_recommendations", result["recommendations"])
        self.assertIn("reliability_recommendations", result["recommendations"])
        self.assertIn("performance_recommendations", result["recommendations"])
        self.assertIn("security_recommendations", result["recommendations"])
        self.assertIn("cost_recommendations", result["recommendations"])
        
        # With our sample data, we should have some recommendations
        self.assertTrue(result["total_recommendations"] > 0)
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_resource_metrics.assert_called_once_with(None)
        self.mock_k8s_client.list_pods.assert_called_once_with(None)
        self.mock_k8s_client.list_deployments.assert_called_once_with(None)
        self.mock_k8s_client.list_services.assert_called_once_with(None)
        self.mock_k8s_client.list_events.assert_called_once_with(None, since_hours=24)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations_with_namespace(self, mock_client_class):
        """Test generate_optimization_recommendations with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with namespace filter
        result = tools.generate_optimization_recommendations(namespace="default")
        
        # Verify the namespace filter was applied
        self.assertIn("namespace", result)
        self.assertEqual(result["namespace"], "default")
        
        # Verify the client was called correctly with namespace
        self.mock_k8s_client.get_resource_metrics.assert_called_once_with("default")
        self.mock_k8s_client.list_pods.assert_called_once_with("default")
        self.mock_k8s_client.list_deployments.assert_called_once_with("default")
        self.mock_k8s_client.list_services.assert_called_once_with("default")
        self.mock_k8s_client.list_events.assert_called_once_with("default", since_hours=24)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations_resource_recommendations(self, mock_client_class):
        """Test resource optimization recommendations."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.generate_optimization_recommendations()
        
        # Check for resource recommendations
        resource_recommendations = result["recommendations"]["resource_recommendations"]
        self.assertTrue(len(resource_recommendations) > 0)
        
        # Check for specific resource recommendations
        resource_rec_types = [rec["type"] for rec in resource_recommendations]
        
        # We should have recommendations for over-provisioned resources
        self.assertIn("cpu_over_provisioned", resource_rec_types)
        self.assertIn("memory_over_provisioned", resource_rec_types)
        
        # We should have recommendations for missing resource requests/limits
        self.assertIn("missing_resource_requests", resource_rec_types)
        self.assertIn("missing_resource_limits", resource_rec_types)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations_reliability_recommendations(self, mock_client_class):
        """Test reliability optimization recommendations."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.generate_optimization_recommendations()
        
        # Check for reliability recommendations
        reliability_recommendations = result["recommendations"]["reliability_recommendations"]
        self.assertTrue(len(reliability_recommendations) > 0)
        
        # Check for specific reliability recommendations
        reliability_rec_types = [rec["type"] for rec in reliability_recommendations]
        
        # We should have recommendations for single-replica deployments
        self.assertIn("single_replica_deployment", reliability_rec_types)
        
        # We should have recommendations for missing probes
        self.assertIn("missing_readiness_probe", reliability_rec_types)
        self.assertIn("missing_liveness_probe", reliability_rec_types)
        
        # We should have recommendations for frequent restarts
        self.assertIn("frequent_restarts", reliability_rec_types)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations_security_recommendations(self, mock_client_class):
        """Test security optimization recommendations."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.generate_optimization_recommendations()
        
        # Check for security recommendations
        security_recommendations = result["recommendations"]["security_recommendations"]
        self.assertTrue(len(security_recommendations) > 0)
        
        # Check for specific security recommendations
        security_rec_types = [rec["type"] for rec in security_recommendations]
        
        # We should have recommendations for security issues
        self.assertIn("running_as_root", security_rec_types)
        self.assertIn("privileged_container", security_rec_types)
        self.assertIn("host_path_volume", security_rec_types)
        self.assertIn("host_network", security_rec_types)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations_error_handling(self, mock_client_class):
        """Test generate_optimization_recommendations error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.get_resource_metrics.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.generate_optimization_recommendations()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_generate_optimization_recommendations_invalid_inputs(self, mock_client_class):
        """Test generate_optimization_recommendations with invalid inputs."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Test with invalid namespace
        result = tools.generate_optimization_recommendations(namespace=123)
        self.assertIn("error", result)
        self.assertIn("namespace must be a string", result["error"])


if __name__ == "__main__":
    unittest.main()