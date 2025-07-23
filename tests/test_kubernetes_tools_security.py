"""
Tests for Kubernetes cluster security analysis tool.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesSecurityTool(unittest.TestCase):
    """Test cases for Kubernetes cluster security analysis tool."""
    
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
                "name": "secure-pod-1",
                "namespace": "default",
                "status": "Running",
                "ready": True,
                "containers": [
                    {
                        "name": "container-1",
                        "image": "nginx:latest",
                        "security_context": {
                            "run_as_non_root": True,
                            "read_only_root_filesystem": True,
                            "privileged": False,
                            "capabilities": {
                                "drop": ["ALL"]
                            }
                        }
                    }
                ],
                "labels": {
                    "app": "web",
                    "tier": "frontend"
                },
                "annotations": {}
            },
            {
                "name": "privileged-pod-1",
                "namespace": "kube-system",
                "status": "Running",
                "ready": True,
                "containers": [
                    {
                        "name": "container-2",
                        "image": "system:latest",
                        "security_context": {
                            "privileged": True
                        }
                    }
                ],
                "labels": {
                    "app": "system",
                    "tier": "infrastructure"
                },
                "annotations": {}
            },
            {
                "name": "insecure-pod-1",
                "namespace": "default",
                "status": "Running",
                "ready": True,
                "containers": [
                    {
                        "name": "container-3",
                        "image": "app:latest",
                        "security_context": {}
                    }
                ],
                "labels": {
                    "app": "api",
                    "tier": "backend"
                },
                "annotations": {}
            }
        ]
        
        # Sample service account data for testing
        self.sample_service_accounts = [
            {
                "name": "default",
                "namespace": "default",
                "secrets": ["default-token-abc123"],
                "automount_service_account_token": True
            },
            {
                "name": "restricted",
                "namespace": "default",
                "secrets": ["restricted-token-xyz789"],
                "automount_service_account_token": False
            }
        ]
        
        # Sample role and role binding data
        self.sample_roles = [
            {
                "name": "pod-reader",
                "namespace": "default",
                "rules": [
                    {
                        "api_groups": [""],
                        "resources": ["pods"],
                        "verbs": ["get", "list", "watch"]
                    }
                ]
            },
            {
                "name": "cluster-admin",
                "namespace": None,  # Cluster role
                "rules": [
                    {
                        "api_groups": ["*"],
                        "resources": ["*"],
                        "verbs": ["*"]
                    }
                ]
            }
        ]
        
        self.sample_role_bindings = [
            {
                "name": "read-pods",
                "namespace": "default",
                "role_ref": {
                    "kind": "Role",
                    "name": "pod-reader"
                },
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "default",
                        "namespace": "default"
                    }
                ]
            },
            {
                "name": "admin-binding",
                "namespace": None,  # Cluster role binding
                "role_ref": {
                    "kind": "ClusterRole",
                    "name": "cluster-admin"
                },
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "admin",
                        "namespace": "kube-system"
                    }
                ]
            }
        ]
        
        # Sample network policy data
        self.sample_network_policies = [
            {
                "name": "default-deny",
                "namespace": "default",
                "pod_selector": {},
                "policy_types": ["Ingress", "Egress"]
            }
        ]
        
        # Mock responses for get_pods
        self.mock_pods_response = {
            "pods": self.sample_pods,
            "count": len(self.sample_pods),
            "namespace": "all"
        }
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_check_cluster_security(self, mock_client_class):
        """Test check_cluster_security with default parameters."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value=self.mock_pods_response)
        
        # Mock additional methods on the k8s_client
        tools.k8s_client.list_service_accounts = MagicMock(return_value=self.sample_service_accounts)
        tools.k8s_client.list_roles = MagicMock(return_value=self.sample_roles)
        tools.k8s_client.list_role_bindings = MagicMock(return_value=self.sample_role_bindings)
        tools.k8s_client.list_network_policies = MagicMock(return_value=self.sample_network_policies)
        
        # Call the method
        result = tools.check_cluster_security()
        
        # Verify the result structure
        self.assertIn("status", result)
        self.assertIn("message", result)
        self.assertIn("security_score", result)
        self.assertIn("issues", result)
        self.assertIn("recommendations", result)
        self.assertIn("confidence_level", result)
        
        # Verify the content
        self.assertIsInstance(result["security_score"], (int, float))
        self.assertGreaterEqual(result["security_score"], 0)
        self.assertLessEqual(result["security_score"], 100)
        
        # Verify issues were identified
        self.assertIsInstance(result["issues"], list)
        
        # Verify recommendations were generated
        self.assertIsInstance(result["recommendations"], list)
        
        # Verify confidence level
        self.assertIn("level", result["confidence_level"])
        self.assertIn("factors", result["confidence_level"])
        self.assertIn("explanation", result["confidence_level"])
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_check_cluster_security_with_namespace(self, mock_client_class):
        """Test check_cluster_security with namespace filter."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        
        # Update mock responses for namespace filter
        namespace_pods_response = self.mock_pods_response.copy()
        namespace_pods_response["namespace"] = "default"
        namespace_pods_response["pods"] = [pod for pod in self.sample_pods if pod["namespace"] == "default"]
        namespace_pods_response["count"] = len(namespace_pods_response["pods"])
        
        tools.get_pods = MagicMock(return_value=namespace_pods_response)
        
        # Filter service accounts for namespace
        namespace_service_accounts = [sa for sa in self.sample_service_accounts if sa["namespace"] == "default"]
        tools.k8s_client.list_service_accounts = MagicMock(return_value=namespace_service_accounts)
        
        # Filter roles for namespace
        namespace_roles = [role for role in self.sample_roles if role["namespace"] == "default"]
        tools.k8s_client.list_roles = MagicMock(return_value=namespace_roles)
        
        # Filter role bindings for namespace
        namespace_role_bindings = [rb for rb in self.sample_role_bindings if rb["namespace"] == "default"]
        tools.k8s_client.list_role_bindings = MagicMock(return_value=namespace_role_bindings)
        
        # Filter network policies for namespace
        namespace_network_policies = [np for np in self.sample_network_policies if np["namespace"] == "default"]
        tools.k8s_client.list_network_policies = MagicMock(return_value=namespace_network_policies)
        
        # Call the method
        result = tools.check_cluster_security(namespace="default")
        
        # Verify the namespace in the result
        self.assertEqual(result["namespace"], "default")
        
        # Verify the get_pods method was called with namespace
        tools.get_pods.assert_called_once_with(namespace="default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_check_cluster_security_error_handling(self, mock_client_class):
        """Test check_cluster_security error handling."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance with mocked methods
        tools = KubernetesTools(self.config)
        tools.get_pods = MagicMock(return_value={"error": "Failed to get pods"})
        
        # Call the method
        result = tools.check_cluster_security()
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to get pods")


if __name__ == "__main__":
    unittest.main()