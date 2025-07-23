"""
Tests for Kubernetes deployment history analysis tool for AWS Strands integration.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.strands.kubernetes_tools import KubernetesTools


class TestKubernetesDeploymentHistoryTool(unittest.TestCase):
    """Test cases for Kubernetes deployment history analysis tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample deployment history data for testing
        now = datetime.now()
        one_day_ago = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        three_days_ago = now - timedelta(days=3)
        seven_days_ago = now - timedelta(days=7)
        
        self.sample_deployment = {
            "name": "test-deployment",
            "namespace": "default",
            "replicas": 3,
            "available_replicas": 3,
            "ready_replicas": 3,
            "updated_replicas": 3,
            "unavailable_replicas": 0,
            "strategy": "RollingUpdate",
            "selector": {
                "app": "test-app"
            },
            "labels": {
                "app": "test-app"
            },
            "annotations": {},
            "created_at": seven_days_ago
        }
        
        self.sample_replicasets = [
            {
                "name": "test-deployment-abc123",
                "namespace": "default",
                "replicas": 3,
                "ready_replicas": 3,
                "available_replicas": 3,
                "revision": 3,
                "created_at": one_day_ago,
                "containers": [
                    {
                        "name": "test-container",
                        "image": "test-image:v3"
                    }
                ]
            },
            {
                "name": "test-deployment-def456",
                "namespace": "default",
                "replicas": 0,
                "ready_replicas": 0,
                "available_replicas": 0,
                "revision": 2,
                "created_at": two_days_ago,
                "containers": [
                    {
                        "name": "test-container",
                        "image": "test-image:v2"
                    }
                ]
            },
            {
                "name": "test-deployment-ghi789",
                "namespace": "default",
                "replicas": 0,
                "ready_replicas": 0,
                "available_replicas": 0,
                "revision": 1,
                "created_at": three_days_ago,
                "containers": [
                    {
                        "name": "test-container",
                        "image": "test-image:v1"
                    }
                ]
            }
        ]
        
        self.sample_events = [
            {
                "name": "test-deployment.16b2f50d5df35106",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled up replica set test-deployment-abc123 to 3",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": one_day_ago,
                "last_timestamp": one_day_ago,
                "count": 1
            },
            {
                "name": "test-deployment.16b2f50d5df35107",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled down replica set test-deployment-def456 to 0",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": one_day_ago + timedelta(minutes=1),
                "last_timestamp": one_day_ago + timedelta(minutes=1),
                "count": 1
            },
            {
                "name": "test-deployment.16b2f50d5df35108",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled up replica set test-deployment-def456 to 3",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": two_days_ago,
                "last_timestamp": two_days_ago,
                "count": 1
            },
            {
                "name": "test-deployment.16b2f50d5df35109",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled down replica set test-deployment-ghi789 to 0",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": two_days_ago + timedelta(minutes=1),
                "last_timestamp": two_days_ago + timedelta(minutes=1),
                "count": 1
            }
        ]
        
        # Configure the mock to return sample data
        self.mock_k8s_client.get_deployment.return_value = self.sample_deployment
        self.mock_k8s_client.list_replicasets_for_deployment.return_value = self.sample_replicasets
        self.mock_k8s_client.list_events.return_value = self.sample_events
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_deployment_history(self, mock_client_class):
        """Test analyze_deployment_history with valid deployment."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.analyze_deployment_history("test-deployment", "default")
        
        # Verify the result
        self.assertEqual(result["deployment_name"], "test-deployment")
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["revision_count"], 3)
        self.assertEqual(len(result["revisions"]), 3)
        self.assertIn("current_revision", result)
        self.assertIn("stability_assessment", result)
        self.assertIn("recent_changes", result)
        self.assertIn("change_frequency", result)
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_deployment.assert_called_once_with("test-deployment", "default")
        self.mock_k8s_client.list_replicasets_for_deployment.assert_called_once_with("test-deployment", "default")
        self.mock_k8s_client.list_events.assert_called_once()
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_deployment_history_with_nonexistent_deployment(self, mock_client_class):
        """Test analyze_deployment_history with nonexistent deployment."""
        # Configure the mock to return None for nonexistent deployment
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.get_deployment.return_value = None
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.analyze_deployment_history("nonexistent", "default")
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_deployment.assert_called_once_with("nonexistent", "default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_deployment_history_with_no_replicasets(self, mock_client_class):
        """Test analyze_deployment_history with no replicasets."""
        # Configure the mock to return empty list for replicasets
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.list_replicasets_for_deployment.return_value = []
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.analyze_deployment_history("test-deployment", "default")
        
        # Verify the result
        self.assertEqual(result["deployment_name"], "test-deployment")
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["revision_count"], 0)
        self.assertEqual(len(result["revisions"]), 0)
        self.assertIn("stability_assessment", result)
        self.assertEqual(result["stability_assessment"]["status"], "unknown")
        
        # Verify the client was called correctly
        self.mock_k8s_client.get_deployment.assert_called_once_with("test-deployment", "default")
        self.mock_k8s_client.list_replicasets_for_deployment.assert_called_once_with("test-deployment", "default")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_deployment_history_with_frequent_changes(self, mock_client_class):
        """Test analyze_deployment_history with frequent changes."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create replicasets with frequent changes (all within last day)
        now = datetime.now()
        frequent_replicasets = [
            {
                "name": "test-deployment-abc123",
                "namespace": "default",
                "replicas": 3,
                "ready_replicas": 3,
                "available_replicas": 3,
                "revision": 5,
                "created_at": now - timedelta(hours=1),
                "containers": [{"name": "test-container", "image": "test-image:v5"}]
            },
            {
                "name": "test-deployment-def456",
                "namespace": "default",
                "replicas": 0,
                "ready_replicas": 0,
                "available_replicas": 0,
                "revision": 4,
                "created_at": now - timedelta(hours=6),
                "containers": [{"name": "test-container", "image": "test-image:v4"}]
            },
            {
                "name": "test-deployment-ghi789",
                "namespace": "default",
                "replicas": 0,
                "ready_replicas": 0,
                "available_replicas": 0,
                "revision": 3,
                "created_at": now - timedelta(hours=12),
                "containers": [{"name": "test-container", "image": "test-image:v3"}]
            },
            {
                "name": "test-deployment-jkl012",
                "namespace": "default",
                "replicas": 0,
                "ready_replicas": 0,
                "available_replicas": 0,
                "revision": 2,
                "created_at": now - timedelta(hours=18),
                "containers": [{"name": "test-container", "image": "test-image:v2"}]
            },
            {
                "name": "test-deployment-mno345",
                "namespace": "default",
                "replicas": 0,
                "ready_replicas": 0,
                "available_replicas": 0,
                "revision": 1,
                "created_at": now - timedelta(hours=23),
                "containers": [{"name": "test-container", "image": "test-image:v1"}]
            }
        ]
        
        self.mock_k8s_client.list_replicasets_for_deployment.return_value = frequent_replicasets
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.analyze_deployment_history("test-deployment", "default")
        
        # Verify the result
        self.assertEqual(result["revision_count"], 5)
        self.assertEqual(len(result["revisions"]), 5)
        self.assertIn("stability_assessment", result)
        
        # Check that the stability assessment indicates frequent changes
        self.assertEqual(result["stability_assessment"]["status"], "unstable")
        self.assertIn("high frequency of changes", result["stability_assessment"]["message"].lower())
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_deployment_history_with_rollbacks(self, mock_client_class):
        """Test analyze_deployment_history with rollbacks."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create events that indicate a rollback
        now = datetime.now()
        rollback_events = [
            {
                "name": "test-deployment.16b2f50d5df35106",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled up replica set test-deployment-abc123 to 3",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": now - timedelta(hours=2),
                "last_timestamp": now - timedelta(hours=2),
                "count": 1
            },
            {
                "name": "test-deployment.16b2f50d5df35107",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled down replica set test-deployment-def456 to 0",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": now - timedelta(hours=2),
                "last_timestamp": now - timedelta(hours=2),
                "count": 1
            },
            {
                "name": "test-deployment.16b2f50d5df35108",
                "namespace": "default",
                "type": "Warning",
                "reason": "DeploymentRollback",
                "message": "Rolled back deployment test-deployment to revision 1",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "first_timestamp": now - timedelta(hours=3),
                "last_timestamp": now - timedelta(hours=3),
                "count": 1
            }
        ]
        
        self.mock_k8s_client.list_events.return_value = rollback_events
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.analyze_deployment_history("test-deployment", "default")
        
        # Verify the result
        self.assertIn("stability_assessment", result)
        
        # Check that the stability assessment indicates rollbacks
        self.assertEqual(result["stability_assessment"]["status"], "warning")
        self.assertIn("rollback", result["stability_assessment"]["message"].lower())
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_analyze_deployment_history_error_handling(self, mock_client_class):
        """Test analyze_deployment_history error handling."""
        # Configure the mock to raise an exception
        mock_client_class.return_value = self.mock_k8s_client
        self.mock_k8s_client.get_deployment.side_effect = Exception("Test error")
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.analyze_deployment_history("test-deployment", "default")
        
        # Verify the result contains an error
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
        self.assertIn("error_type", result)
        self.assertIn("suggestion", result)


if __name__ == "__main__":
    unittest.main()