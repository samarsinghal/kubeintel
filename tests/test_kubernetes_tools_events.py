"""
Tests for Kubernetes event summarization tool.
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


class TestKubernetesToolsEvents(unittest.TestCase):
    """Test cases for Kubernetes event summarization tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "config_type": "kubeconfig",
            "kubeconfig_path": "/path/to/kubeconfig"
        }
        
        # Create a mock Kubernetes client
        self.mock_k8s_client = MagicMock()
        
        # Sample events data for testing
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
            },
            {
                "name": "pod-2.16b2f50d5df35108",
                "namespace": "default",
                "type": "Warning",
                "reason": "FailedScheduling",
                "message": "0/3 nodes are available: 3 Insufficient memory",
                "involved_object": {
                    "kind": "Pod",
                    "name": "pod-2",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-02T00:02:00Z",
                "last_timestamp": "2023-01-02T00:03:00Z",
                "count": 5
            },
            {
                "name": "deployment-1.16b2f50d5df35109",
                "namespace": "default",
                "type": "Normal",
                "reason": "ScalingReplicaSet",
                "message": "Scaled up replica set deployment-1-abc123 to 3",
                "involved_object": {
                    "kind": "Deployment",
                    "name": "deployment-1",
                    "namespace": "default"
                },
                "first_timestamp": "2023-01-03T00:00:00Z",
                "last_timestamp": "2023-01-03T00:00:00Z",
                "count": 1
            },
            {
                "name": "node-1.16b2f50d5df35110",
                "namespace": "default",
                "type": "Warning",
                "reason": "NodeNotReady",
                "message": "Node node-1 status is now: NodeNotReady",
                "involved_object": {
                    "kind": "Node",
                    "name": "node-1",
                    "namespace": ""
                },
                "first_timestamp": "2023-01-04T00:00:00Z",
                "last_timestamp": "2023-01-04T00:00:00Z",
                "count": 1
            },
            {
                "name": "service-1.16b2f50d5df35111",
                "namespace": "kube-system",
                "type": "Normal",
                "reason": "Created",
                "message": "Created service",
                "involved_object": {
                    "kind": "Service",
                    "name": "service-1",
                    "namespace": "kube-system"
                },
                "first_timestamp": "2023-01-05T00:00:00Z",
                "last_timestamp": "2023-01-05T00:00:00Z",
                "count": 1
            },
            {
                "name": "pod-3.16b2f50d5df35112",
                "namespace": "kube-system",
                "type": "Warning",
                "reason": "Evicted",
                "message": "The node was low on resource: memory",
                "involved_object": {
                    "kind": "Pod",
                    "name": "pod-3",
                    "namespace": "kube-system"
                },
                "first_timestamp": "2023-01-06T00:00:00Z",
                "last_timestamp": "2023-01-06T00:00:00Z",
                "count": 1
            }
        ]
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_summarize_events(self, mock_client_class):
        """Test summarize_events with normal data."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.summarize_events(self.sample_events)
        
        # Verify the result
        self.assertIsInstance(result, str)
        self.assertIn("Kubernetes Events Summary", result)
        self.assertIn("7 events", result)
        self.assertIn("3 Normal events", result)
        self.assertIn("4 Warning events", result)
        
        # Check for warning events section
        self.assertIn("Warning Events", result)
        self.assertIn("Failed", result)
        self.assertIn("FailedScheduling", result)
        self.assertIn("NodeNotReady", result)
        self.assertIn("Evicted", result)
        
        # Check for events by namespace
        self.assertIn("Events by Namespace", result)
        self.assertIn("default:", result)
        self.assertIn("kube-system:", result)
        
        # Check for events by resource kind
        self.assertIn("Events by Resource Kind", result)
        self.assertIn("Pod:", result)
        self.assertIn("Deployment:", result)
        self.assertIn("Node:", result)
        self.assertIn("Service:", result)
        
        # Check for most frequent event reasons
        self.assertIn("Most Frequent Event Reasons", result)
        
        # Check for recent events timeline
        self.assertIn("Recent Events Timeline", result)
        
        # Check for insights and recommendations
        self.assertIn("Insights and Recommendations", result)
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_summarize_events_empty_list(self, mock_client_class):
        """Test summarize_events with an empty list."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with empty list
        result = tools.summarize_events([])
        
        # Verify the result
        self.assertEqual(result, "No events to summarize.")
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_summarize_events_invalid_input(self, mock_client_class):
        """Test summarize_events with invalid input."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method with invalid input
        result = tools.summarize_events("not a list")
        
        # Verify the result
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("events must be a list", result["error"])
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_summarize_events_insights(self, mock_client_class):
        """Test that summarize_events generates insights."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Call the method
        result = tools.summarize_events(self.sample_events)
        
        # Verify insights are generated
        self.assertIn("Found", result)
        self.assertIn("pod failure", result.lower())
        self.assertIn("resource constraint", result.lower())
    
    @patch('src.strands.kubernetes_tools.KubernetesClient')
    def test_summarize_events_error_handling(self, mock_client_class):
        """Test summarize_events error handling."""
        # Configure the mock
        mock_client_class.return_value = self.mock_k8s_client
        
        # Create the tools instance
        tools = KubernetesTools(self.config)
        
        # Create a mock that raises an exception
        def mock_generate_insights(*args, **kwargs):
            raise Exception("Test error")
        
        # Replace the _generate_event_insights method with our mock
        tools._generate_event_insights = mock_generate_insights
        
        # Call the method
        result = tools.summarize_events(self.sample_events)
        
        # Verify the result contains an error
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])


if __name__ == "__main__":
    unittest.main()