"""
Tests for Kubernetes manifest validation tool.
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


class TestKubernetesToolsManifestValidation(unittest.TestCase):
    """Test cases for Kubernetes manifest validation tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample valid pod manifest
        self.valid_pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "test-pod",
                "namespace": "default",
                "labels": {
                    "app": "test"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
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
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/",
                                "port": 80
                            }
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/",
                                "port": 80
                            }
                        }
                    }
                ],
                "securityContext": {
                    "runAsNonRoot": True
                },
                "serviceAccountName": "default"
            }
        }
        
        # Sample valid deployment manifest
        self.valid_deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "test-deployment",
                "namespace": "default",
                "labels": {
                    "app": "test"
                }
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "matchLabels": {
                        "app": "test"
                    }
                },
                "strategy": {
                    "type": "RollingUpdate"
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "test"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "test-container",
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
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": "/",
                                        "port": 80
                                    }
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": "/",
                                        "port": 80
                                    }
                                }
                            }
                        ],
                        "securityContext": {
                            "runAsNonRoot": True
                        },
                        "serviceAccountName": "default"
                    }
                }
            }
        }
        
        # Sample valid service manifest
        self.valid_service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "test-service",
                "namespace": "default",
                "labels": {
                    "app": "test"
                }
            },
            "spec": {
                "selector": {
                    "app": "test"
                },
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "targetPort": 8080,
                        "protocol": "TCP"
                    }
                ],
                "type": "ClusterIP"
            }
        }
        
        # Sample invalid manifest (missing required fields)
        self.invalid_manifest = {
            "kind": "Pod",
            "metadata": {
                "namespace": "default"
            },
            "spec": {
                "containers": []
            }
        }
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_valid_pod(self, mock_client_class):
        """Test validate_kubernetes_manifest with a valid pod manifest."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.validate_kubernetes_manifest(self.valid_pod_manifest)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertTrue(result["valid"])
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_valid_deployment(self, mock_client_class):
        """Test validate_kubernetes_manifest with a valid deployment manifest."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.validate_kubernetes_manifest(self.valid_deployment_manifest)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertTrue(result["valid"])
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_valid_service(self, mock_client_class):
        """Test validate_kubernetes_manifest with a valid service manifest."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.validate_kubernetes_manifest(self.valid_service_manifest)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertTrue(result["valid"])
        self.assertIn("errors", result)
        self.assertEqual(len(result["errors"]), 0)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_invalid(self, mock_client_class):
        """Test validate_kubernetes_manifest with an invalid manifest."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.validate_kubernetes_manifest(self.invalid_manifest)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertFalse(result["valid"])
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)
        
        # Check for specific errors
        error_messages = " ".join(result["errors"])
        self.assertIn("apiVersion", error_messages)
        self.assertIn("metadata.name", error_messages)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_pod_warnings(self, mock_client_class):
        """Test validate_kubernetes_manifest with a pod that generates warnings."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create a pod manifest with missing probes and resources
        pod_with_warnings = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "test-pod",
                "namespace": "default"
            },
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "nginx:latest"
                    }
                ]
            }
        }
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.validate_kubernetes_manifest(pod_with_warnings)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertTrue(result["valid"])  # Still valid, but with warnings
        self.assertIn("warnings", result)
        self.assertTrue(len(result["warnings"]) > 0)
        
        # Check for specific warnings
        warning_messages = " ".join(result["warnings"])
        self.assertIn("resource", warning_messages.lower())
        self.assertIn("probe", warning_messages.lower())
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_deployment_warnings(self, mock_client_class):
        """Test validate_kubernetes_manifest with a deployment that generates warnings."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create a deployment manifest with single replica
        deployment_with_warnings = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "test-deployment",
                "namespace": "default"
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "test"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "test"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "test-container",
                                "image": "nginx:latest"
                            }
                        ]
                    }
                }
            }
        }
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.validate_kubernetes_manifest(deployment_with_warnings)
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertTrue(result["valid"])  # Still valid, but with warnings
        self.assertIn("warnings", result)
        self.assertTrue(len(result["warnings"]) > 0)
        
        # Check for specific warnings
        warning_messages = " ".join(result["warnings"])
        self.assertIn("replica", warning_messages.lower())
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_validate_kubernetes_manifest_non_dict_input(self, mock_client_class):
        """Test validate_kubernetes_manifest with non-dictionary input."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with invalid input
        result = tools.validate_kubernetes_manifest("not a dictionary")
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("valid", result)
        self.assertFalse(result["valid"])
        self.assertIn("errors", result)
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("must be a dictionary", result["errors"][0])


if __name__ == "__main__":
    unittest.main()