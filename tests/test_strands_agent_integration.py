"""Integration tests for AWS Strands Agent implementation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.agent.strands_agent_enhanced import (
    KubernetesMonitoringAgent,
    GetClusterDataTool,
    GetPodDetailsTool,
    GetNamespaceSummaryTool
)
from src.k8s.collector import DataCollector
from src.models.kubernetes import ClusterData, PodInfo, ServiceInfo, EventInfo


@pytest.fixture
def mock_data_collector():
    """Create a mock data collector."""
    collector = Mock(spec=DataCollector)
    collector.kubernetes_client = Mock()
    collector.kubernetes_client.health_check.return_value = True
    
    # Mock cluster data
    mock_cluster_data = ClusterData(
        pods=[
            PodInfo(
                name="test-pod",
                namespace="default",
                status="Running",
                ready=True,
                restart_count=0,
                node_name="node-1",
                created_at=datetime.utcnow(),
                containers=[],
                labels={},
                annotations={},
                is_healthy=True,
                has_high_restarts=False
            )
        ],
        services=[
            ServiceInfo(
                name="test-service",
                namespace="default",
                type="ClusterIP",
                cluster_ip="10.0.0.1",
                ports=[],
                selector={},
                labels={},
                is_headless=False
            )
        ],
        events=[
            EventInfo(
                name="test-event",
                namespace="default",
                type="Normal",
                reason="Created",
                message="Pod created",
                first_timestamp=datetime.utcnow(),
                last_timestamp=datetime.utcnow(),
                count=1,
                involved_object={}
            )
        ],
        timestamp=datetime.utcnow()
    )
    
    collector.collect_cluster_data = AsyncMock(return_value=mock_cluster_data)
    collector.collect_specific_pod_data = AsyncMock(return_value=mock_cluster_data.pods[0])
    
    return collector


@pytest.fixture
def mock_state_session():
    """Create a mock state session."""
    session = Mock()
    session.session_id = "test-session-123"
    session.set = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


@pytest.fixture
def strands_config():
    """Create test Strands configuration."""
    return {
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "region": "us-east-1",
        "session_ttl": 3600,
        "timeout": 30,
        "temperature": 0.1,
        "max_tokens": 4000
    }


class TestStrandsTools:
    """Test Strands tool implementations."""
    
    @pytest.mark.asyncio
    async def test_get_cluster_data_tool(self, mock_data_collector):
        """Test GetClusterDataTool execution."""
        tool = GetClusterDataTool(mock_data_collector)
        
        # Test successful execution
        result = await tool.execute({"namespace": "default", "include_logs": False})
        
        assert result.status == "success"
        assert "data" in result.result
        assert result.result["data"]["total_pods"] == 1
        assert result.result["data"]["total_services"] == 1
        assert result.result["data"]["namespace"] == "default"
    
    @pytest.mark.asyncio
    async def test_get_pod_details_tool(self, mock_data_collector):
        """Test GetPodDetailsTool execution."""
        tool = GetPodDetailsTool(mock_data_collector)
        
        # Test successful execution
        result = await tool.execute({"pod_name": "test-pod", "namespace": "default"})
        
        assert result.status == "success"
        assert "data" in result.result
        assert result.result["data"]["name"] == "test-pod"
        assert result.result["data"]["namespace"] == "default"
    
    @pytest.mark.asyncio
    async def test_get_namespace_summary_tool(self, mock_data_collector):
        """Test GetNamespaceSummaryTool execution."""
        tool = GetNamespaceSummaryTool(mock_data_collector)
        
        # Test successful execution
        result = await tool.execute({"namespace": "default"})
        
        assert result.status == "success"
        assert "data" in result.result
        assert result.result["data"]["namespace"] == "default"
        assert result.result["data"]["resource_counts"]["total_pods"] == 1
    
    @pytest.mark.asyncio
    async def test_tool_validation_errors(self, mock_data_collector):
        """Test tool input validation."""
        cluster_tool = GetClusterDataTool(mock_data_collector)
        pod_tool = GetPodDetailsTool(mock_data_collector)
        namespace_tool = GetNamespaceSummaryTool(mock_data_collector)
        
        # Test invalid inputs
        result = await cluster_tool.execute({"namespace": 123})
        assert result.status == "error"
        
        result = await pod_tool.execute({"pod_name": ""})
        assert result.status == "error"
        
        result = await namespace_tool.execute({"namespace": None})
        assert result.status == "error"


class TestKubernetesMonitoringAgent:
    """Test KubernetesMonitoringAgent implementation."""
    
    @patch('src.agent.strands_agent_enhanced.Agent')
    def test_agent_initialization(self, mock_agent_class, mock_data_collector, mock_state_session, strands_config):
        """Test agent initialization with proper Strands configuration."""
        mock_agent_instance = Mock()
        mock_agent_instance.tools = []
        mock_agent_class.return_value = mock_agent_instance
        
        agent = KubernetesMonitoringAgent(
            data_collector=mock_data_collector,
            state_session=mock_state_session,
            strands_config=strands_config
        )
        
        # Verify agent was initialized with correct parameters
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        
        assert call_args[1]["name"] == "kubernetes-monitoring-agent"
        assert call_args[1]["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert call_args[1]["region"] == "us-east-1"
        assert call_args[1]["state_session"] == mock_state_session
        assert call_args[1]["temperature"] == 0.1
        assert call_args[1]["max_tokens"] == 4000
        assert len(call_args[1]["tools"]) == 3  # Three Kubernetes tools
    
    @patch('src.agent.strands_agent_enhanced.Agent')
    @pytest.mark.asyncio
    async def test_health_check(self, mock_agent_class, mock_data_collector, mock_state_session, strands_config):
        """Test agent health check."""
        mock_agent_instance = Mock()
        mock_agent_instance.tools = ["tool1", "tool2", "tool3"]
        mock_agent_class.return_value = mock_agent_instance
        
        agent = KubernetesMonitoringAgent(
            data_collector=mock_data_collector,
            state_session=mock_state_session,
            strands_config=strands_config
        )
        
        health = await agent.health_check()
        
        assert health["healthy"] is True
        assert health["components"]["kubernetes_api"] is True
        assert health["components"]["strands_agent"] is True
        assert health["components"]["state_session"] is True
        assert health["components"]["tools_registered"] == 3
        assert health["components"]["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    @patch('src.agent.strands_agent_enhanced.Agent')
    @pytest.mark.asyncio
    async def test_analyze_cluster_with_fallback(self, mock_agent_class, mock_data_collector, mock_state_session, strands_config):
        """Test cluster analysis with fallback when Strands fails."""
        mock_agent_instance = Mock()
        mock_agent_instance.tools = []
        mock_agent_instance.execute = AsyncMock(side_effect=Exception("Strands unavailable"))
        mock_agent_class.return_value = mock_agent_instance
        
        agent = KubernetesMonitoringAgent(
            data_collector=mock_data_collector,
            state_session=mock_state_session,
            strands_config=strands_config
        )
        
        result = await agent.analyze_cluster(namespace="default")
        
        assert result["status"] == "completed"
        assert "analysis_id" in result
        assert "findings" in result
        assert "recommendations" in result
        assert "summary" in result
        assert result["metadata"]["namespace"] == "default"
    
    @patch('src.agent.strands_agent_enhanced.Agent')
    @pytest.mark.asyncio
    async def test_state_session_integration(self, mock_agent_class, mock_data_collector, mock_state_session, strands_config):
        """Test state session integration for learning."""
        mock_agent_instance = Mock()
        mock_agent_instance.tools = []
        mock_agent_instance.execute = AsyncMock(return_value=Mock(content="Analysis complete"))
        mock_agent_class.return_value = mock_agent_instance
        
        agent = KubernetesMonitoringAgent(
            data_collector=mock_data_collector,
            state_session=mock_state_session,
            strands_config=strands_config
        )
        
        await agent.analyze_cluster(namespace="test")
        
        # Verify state session was used for context storage
        assert mock_state_session.set.call_count >= 2  # Context and result storage
        
        # Check that analysis context was stored
        context_calls = [call for call in mock_state_session.set.call_args_list 
                        if "analysis_context_" in str(call)]
        assert len(context_calls) > 0
    
    @pytest.mark.asyncio
    async def test_system_prompt_creation(self, mock_data_collector, strands_config):
        """Test system prompt creation for Claude-3-Sonnet."""
        with patch('src.agent.strands_agent_enhanced.Agent'):
            agent = KubernetesMonitoringAgent(
                data_collector=mock_data_collector,
                strands_config=strands_config
            )
            
            prompt = agent._create_system_prompt()
            
            # Verify prompt contains key elements for Kubernetes analysis
            assert "Kubernetes" in prompt
            assert "Claude-3-Sonnet" in prompt
            assert "get_cluster_data" in prompt
            assert "get_pod_details" in prompt
            assert "get_namespace_summary" in prompt
            assert "Critical Issues" in prompt
            assert "kubectl" in prompt


class TestStrandsIntegration:
    """Test real Strands integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_flow(self, mock_data_collector):
        """Test the complete tool execution flow."""
        # Test that tools can be executed independently
        cluster_tool = GetClusterDataTool(mock_data_collector)
        pod_tool = GetPodDetailsTool(mock_data_collector)
        namespace_tool = GetNamespaceSummaryTool(mock_data_collector)
        
        # Execute tools in sequence as Strands would
        cluster_result = await cluster_tool.execute({"include_logs": False})
        assert cluster_result.status == "success"
        
        pod_result = await pod_tool.execute({"pod_name": "test-pod", "namespace": "default"})
        assert pod_result.status == "success"
        
        namespace_result = await namespace_tool.execute({"namespace": "default"})
        assert namespace_result.status == "success"
        
        # Verify data consistency across tools
        cluster_data = cluster_result.result["data"]
        pod_data = pod_result.result["data"]
        namespace_data = namespace_result.result["data"]
        
        assert cluster_data["namespace"] == "all"  # Cluster tool shows all namespaces
        assert pod_data["namespace"] == "default"
        assert namespace_data["namespace"] == "default"
    
    @patch('src.agent.strands_agent_enhanced.Agent')
    @pytest.mark.asyncio
    async def test_error_handling_and_graceful_degradation(self, mock_agent_class, mock_data_collector, strands_config):
        """Test error handling and graceful degradation."""
        # Simulate various failure scenarios
        mock_agent_instance = Mock()
        mock_agent_instance.tools = []
        mock_agent_class.return_value = mock_agent_instance
        
        # Test with failing data collector
        failing_collector = Mock(spec=DataCollector)
        failing_collector.kubernetes_client = Mock()
        failing_collector.kubernetes_client.health_check.return_value = False
        
        agent = KubernetesMonitoringAgent(
            data_collector=failing_collector,
            strands_config=strands_config
        )
        
        health = await agent.health_check()
        assert health["healthy"] is False
        assert health["components"]["kubernetes_api"] is False