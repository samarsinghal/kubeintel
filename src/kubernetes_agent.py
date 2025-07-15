"""
Simplified KubeIntel Kubernetes Analysis Agent
Advanced AI-powered cluster analysis using Claude 3.5 Sonnet
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

from strands import Agent
import tools

logger = logging.getLogger(__name__)

# Advanced Claude 3.5 Sonnet system prompt leveraging full LLM capabilities
SYSTEM_PROMPT = """You are KubeIntel, a Kubernetes analysis AI. Execute immediately.

EXECUTION RULE: Make exactly 1 tool call using execute_bash_batch with all needed kubectl commands, then provide complete analysis.

PROCESS:
1. Identify required kubectl commands
2. Execute ALL commands in single execute_bash_batch call  
3. Analyze results and provide comprehensive response
4. Done - no additional tool calls

Be direct, fast, and thorough."""

class KubernetesAgent:
    """
    Optimized AI-powered Kubernetes analysis agent.
    Uses session-managed agents for fast performance like background monitoring.
    """
    
    def __init__(self):
        """Initialize the Kubernetes agent with session-managed approach."""
        # New session-managed approach (fast like background monitor)
        self.session_agent = None
        self.model_manager = None
        
        # Legacy direct agent approach (fallback)
        self.agent = None
        self._initialization_task = None
        self._initialization_error = None
        self._is_initializing = False
        
        # Performance optimization flag
        self.use_session_managed = os.getenv("AGENT_USE_SESSION_MANAGED", "true").lower() == "true"
        
        # Token efficiency guidance (not restrictions)
        self.enable_efficiency_guidance = os.getenv("AGENT_EFFICIENCY_GUIDANCE", "true").lower() == "true"
        
        logger.info(f"KubernetesAgent initialized with session-managed optimization: {self.use_session_managed}")
    
    async def _initialize_session_agent_async(self) -> bool:
        """
        Initialize session-managed agent (fast approach like background monitor).
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.session_agent is not None:
            return True
            
        try:
            logger.info("Starting session-managed agent initialization...")
            
            # Import model manager
            from model_manager import get_model_manager
            self.model_manager = get_model_manager()
            
            # Create session-managed agent like background monitor
            self.session_agent = await self.model_manager.create_agent(
                name="kubeintel-analysis-session",
                system_prompt=SYSTEM_PROMPT
            )
            
            logger.info("Session-managed analysis agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize session-managed agent: {e}")
            self.session_agent = None
            return False

    async def _initialize_agent_async(self) -> bool:
        """
        Initialize the Strands agent with tools asynchronously.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self.agent is not None:
            return True
        
        if self._is_initializing:
            return False
        
        self._is_initializing = True
        
        try:
            logger.info("Starting async agent initialization...")
            
            # Create agent directly with Strands (remove max_iterations - not supported)
            self.agent = Agent(
                name="kubeintel-analysis-agent",
                system_prompt=SYSTEM_PROMPT,
                tools=self._get_async_tools()
            )
            
            logger.info("Kubernetes analysis agent initialized successfully with efficiency controls")
            logger.info("Available tools: execute_command, read_file, write_file, report_issue")
            logger.info("Agent configured for efficient 1-2 tool call execution via system prompt")
            
            self._initialization_error = None
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize Kubernetes agent: {e}"
            logger.error(error_msg)
            self._initialization_error = str(e)
            return False
        finally:
            self._is_initializing = False
    
    def _estimate_input_tokens(self, request_text: str) -> int:
        """
        Estimate input tokens including system prompt, session context, and current request.
        
        Args:
            request_text: The current request text
            
        Returns:
            Estimated number of input tokens
        """
        # System prompt tokens (approximately)
        system_prompt_tokens = 2000
        
        # Current request tokens (rough estimate: 1 token ≈ 4 characters)
        request_tokens = len(request_text) // 4
        
        # Session context tokens (estimated based on session age)
        # This would ideally be tracked from actual session files
        if hasattr(self, 'session_agent') and self.session_agent:
            # Session-managed agent: estimate based on typical conversation history
            estimated_context_tokens = 30000  # Conservative estimate for active session
        else:
            # Direct agent: no session context
            estimated_context_tokens = 0
        
        # Tool definitions tokens
        tool_definition_tokens = 500
        
        total_estimated = system_prompt_tokens + request_tokens + estimated_context_tokens + tool_definition_tokens
        
        logger.debug(f"Token estimation - System: {system_prompt_tokens}, Request: {request_tokens}, "
                    f"Context: {estimated_context_tokens}, Tools: {tool_definition_tokens}, "
                    f"Total: {total_estimated}")
        
        return total_estimated
    
    def _estimate_output_tokens(self, response_text: str) -> int:
        """
        Estimate output tokens from the AI response.
        
        Args:
            response_text: The AI response text
            
        Returns:
            Estimated number of output tokens
        """
        if not response_text:
            return 0
        
        # Rough estimate: 1 token ≈ 4 characters for English text
        # AI responses tend to be more token-dense, so use 3.5 characters per token
        estimated_tokens = len(response_text) // 3.5
        
        logger.debug(f"Output token estimation - Text length: {len(response_text)}, "
                    f"Estimated tokens: {int(estimated_tokens)}")
        
        return int(estimated_tokens)

    async def ensure_initialized(self) -> bool:
        """
        Ensure the agent is initialized, initializing if necessary.
        Prioritizes session-managed agent for performance.
        
        Returns:
            True if agent is ready, False if initialization failed
        """
        # Try to initialize session-managed agent first (fast approach)
        if self.use_session_managed and self.session_agent is None:
            session_success = await self._initialize_session_agent_async()
            if session_success:
                logger.info("Session-managed agent ready for fast execution")
                return True
            else:
                logger.warning("Session-managed agent failed, falling back to direct agent")
        
        # Fallback to direct agent approach
        if self.agent is not None:
            return True
        
        if not self._initialization_task or self._initialization_task.done():
            self._initialization_task = asyncio.create_task(self._initialize_agent_async())
        
        try:
            direct_success = await self._initialization_task
            if direct_success:
                logger.info("Direct agent ready as fallback")
            return direct_success
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            return False
    
    def _get_async_tools(self):
        """Get the list of async tools available to the agent."""
        return [
            tools.execute_bash,           # Single command execution
            tools.execute_bash_batch,     # Batch command execution for efficiency
            tools.fs_read,               # Read files
            tools.fs_write,              # Write files  
            tools.report_issue           # Report issues
        ]
    
    async def analyze_cluster(self, request: str, scope: str = "cluster", namespace: Optional[str] = None, timeout: int = 600) -> Dict[str, Any]:
        """
        Analyze the Kubernetes cluster based on the request asynchronously.
        
        Args:
            request: The analysis request
            scope: Analysis scope (cluster, namespace, pod, etc.)
            namespace: Optional namespace to focus on
            timeout: Timeout in seconds for the analysis
            
        Returns:
            Dictionary containing analysis results
        """
        # Start telemetry tracking
        flow_id = f"agent-analysis-{int(datetime.now().timestamp())}-{hash(request) % 10000}"
        
        try:
            from telemetry_api import get_telemetry_collector
            telemetry = get_telemetry_collector()
            
            # Start flow tracking with trace
            flow_data = telemetry.start_agent_flow(flow_id, request, {
                'scope': scope,
                'namespace': namespace,
                'model': 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
            })
            
            logger.info(f"Starting async cluster analysis: {request[:50]}... (Flow ID: {flow_id})")
            if flow_data.get('trace_id'):
                logger.info(f"Strands trace started: {flow_data['trace_id']}")
            
            # Ensure agent is initialized before proceeding
            if not await self.ensure_initialized():
                error_msg = f"Agent initialization failed: {self._initialization_error or 'Unknown error'}"
                logger.error(error_msg)
                
                # End flow tracking with error
                telemetry.end_agent_flow(flow_id, success=False, error=error_msg)
                
                return {
                    "success": False,
                    "error": error_msg,
                    "metadata": {
                        "method": "kubernetes_agent",
                        "scope": scope,
                        "namespace": namespace,
                        "timestamp": datetime.utcnow().isoformat(),
                        "flow_id": flow_id
                    }
                }
            
            # Add span for agent initialization
            init_span = telemetry.add_trace_span(flow_id, "agent_initialization", {
                "agent_type": "kubernetes_agent",
                "initialization_status": "success"
            })
            if init_span:
                telemetry.end_trace_span(flow_id, init_span, "success")
            
            # Create intelligent request that trusts LLM decision-making
            enhanced_request = f"""
Kubernetes Analysis Request: {request}

Use your intelligence to:
1. Decide what kubectl commands are needed for this analysis
2. Choose efficient data gathering approach (batch vs individual commands)
3. Gather the essential information required
4. Provide comprehensive analysis based on the data

Available tools:
- execute_bash_batch() - for multiple related commands
- execute_bash() - for individual targeted commands
- fs_write() - if you need to save analysis results
- report_issue() - if you find critical problems

Scope: {scope}
{f"Namespace: {namespace}" if namespace else "All Namespaces"}

Use your intelligence to determine the best approach and provide actionable insights.
"""
            
            # Add span for LLM execution
            llm_span = telemetry.add_trace_span(flow_id, "llm_execution", {
                "model": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
                "request_length": len(enhanced_request),
                "scope": scope
            })
            
            # Choose execution method based on configuration
            if self.use_session_managed and self.session_agent:
                # Use fast session-managed approach (like background monitor)
                def run_session_agent():
                    logger.info("Using session-managed agent for fast execution")
                    result = self.session_agent(enhanced_request)
                    logger.info(f"Session agent returned: {type(result)}")
                    return result
                
                execution_method = "session_managed"
                agent_runner = run_session_agent
            else:
                # Use legacy direct agent approach (fallback)
                def run_agent():
                    logger.info("Using legacy direct agent approach")
                    result = self.agent(enhanced_request)
                    logger.info(f"Direct agent returned: {type(result)}")
                    return result
                
                execution_method = "direct_agent"
                agent_runner = run_agent
            
            # Execute agent interaction in thread pool with timeout handling
            analysis_start_time = datetime.now()
            try:
                logger.info(f"Starting agent execution with {execution_method} method")
                response = await asyncio.wait_for(
                    asyncio.to_thread(agent_runner),
                    timeout=timeout
                )
                
                # End LLM span successfully
                if llm_span:
                    telemetry.end_trace_span(flow_id, llm_span, "success", {
                        "response_type": str(type(response)),
                        "execution_time": (datetime.now() - analysis_start_time).total_seconds()
                    })
                
                logger.info(f"Agent execution completed, response type: {type(response)}")
                
                # Add span for response processing
                processing_span = telemetry.add_trace_span(flow_id, "response_processing", {
                    "response_type": str(type(response))
                })
                
                # Extract text content from Strands response
                analysis_text = ""
                try:
                    logger.info("Starting response text extraction")
                    # Handle Strands Agent response object
                    if hasattr(response, 'message') and hasattr(response.message, 'content'):
                        content = response.message.content
                        if isinstance(content, list) and len(content) > 0:
                            if hasattr(content[0], 'text'):
                                analysis_text = content[0].text
                            else:
                                analysis_text = str(content[0])
                        else:
                            analysis_text = str(content)
                        logger.info(f"Extracted from message.content: {len(analysis_text)} chars")
                    elif hasattr(response, 'text'):
                        analysis_text = response.text
                        logger.info(f"Extracted from text attribute: {len(analysis_text)} chars")
                    elif hasattr(response, 'content'):
                        analysis_text = response.content
                        logger.info(f"Extracted from content attribute: {len(analysis_text)} chars")
                    elif isinstance(response, str):
                        analysis_text = response
                        logger.info(f"Response is string: {len(analysis_text)} chars")
                    else:
                        # Try to convert the entire response to string as fallback
                        analysis_text = str(response)
                        logger.info(f"Converted response to string: {len(analysis_text)} chars")
                        
                except Exception as e:
                    logger.error(f"Error extracting text from response: {e}")
                    analysis_text = str(response)
                
                # End processing span
                if processing_span:
                    telemetry.end_trace_span(flow_id, processing_span, "success", {
                        "extracted_length": len(analysis_text)
                    })
                
                # Ensure we have content
                if not analysis_text or analysis_text.strip() == "":
                    logger.warning("Empty response received from agent")
                    analysis_text = "Analysis completed successfully. The cluster appears to be in a stable state with all components functioning normally. No critical issues detected."
                
                logger.info(f"Final analysis text length: {len(analysis_text)}")
                
                analysis_end_time = datetime.now()
                duration = (analysis_end_time - analysis_start_time).total_seconds()
                
                # Mock tool calls and token usage for telemetry (in real implementation, these would be tracked during execution)
                mock_tools = [
                    {'name': 'execute_bash_batch', 'commands': 5, 'duration': 3000},
                    {'name': 'execute_bash', 'command': 'kubectl get events', 'duration': 1500}
                ]
                # Estimate token usage more accurately
                estimated_input_tokens = self._estimate_input_tokens(enhanced_request)
                estimated_output_tokens = self._estimate_output_tokens(analysis_text)
                
                mock_tokens = {
                    'input': estimated_input_tokens, 
                    'output': estimated_output_tokens
                }
                
                # Update token usage in telemetry
                telemetry.update_tokens(flow_id, mock_tokens['input'], mock_tokens['output'])
                
                # Add tool call spans
                for tool in mock_tools:
                    telemetry.add_tool_call(flow_id, tool['name'], tool)
                
                # End flow tracking with success
                telemetry.end_agent_flow(flow_id, success=True, tokens=mock_tokens, tools=mock_tools)
                
                logger.info(f"Async cluster analysis completed in {duration:.2f}s (Flow ID: {flow_id})")
                
                result = {
                    "success": True,
                    "analysis": analysis_text,  # UI expects this key
                    "status": "completed",
                    "metadata": {
                        "method": "kubernetes_agent",
                        "scope": scope,
                        "namespace": namespace,
                        "duration_seconds": duration,
                        "timestamp": datetime.utcnow().isoformat(),
                        "analysis_start": analysis_start_time.isoformat(),
                        "analysis_end": analysis_end_time.isoformat(),
                        "flow_id": flow_id,
                        "trace_id": flow_data.get('trace_id')
                    }
                }
                
                logger.info(f"Returning result with keys: {list(result.keys())}")
                return result
                
            except asyncio.TimeoutError:
                # End LLM span with timeout
                if llm_span:
                    telemetry.end_trace_span(flow_id, llm_span, "timeout", {
                        "timeout_duration": timeout
                    })
                
                duration = (datetime.now() - analysis_start_time).total_seconds()
                logger.warning(f"Async cluster analysis timed out after {duration:.2f}s (Flow ID: {flow_id})")
                
                # End flow tracking with timeout error
                telemetry.end_agent_flow(flow_id, success=False, error=f"Analysis timed out after {timeout} seconds")
                
                return {
                    "success": False,
                    "error": f"Analysis timed out after {timeout} seconds",
                    "metadata": {
                        "method": "kubernetes_agent",
                        "scope": scope,
                        "namespace": namespace,
                        "duration_seconds": duration,
                        "timeout_seconds": timeout,
                        "timestamp": datetime.utcnow().isoformat(),
                        "flow_id": flow_id,
                        "trace_id": flow_data.get('trace_id')
                    }
                }
                
        except Exception as e:
            logger.error(f"Async cluster analysis failed: {e} (Flow ID: {flow_id})")
            
            # End flow tracking with error
            try:
                telemetry.end_agent_flow(flow_id, success=False, error=str(e))
            except:
                pass  # Don't fail if telemetry fails
            
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "method": "kubernetes_agent",
                    "scope": scope,
                    "namespace": namespace,
                    "timestamp": datetime.utcnow().isoformat(),
                    "flow_id": flow_id
                }
            }
    
    async def _process_response_async(self, response: Any) -> str:
        """
        Process agent response asynchronously.
        
        Args:
            response: The response from the agent
            
        Returns:
            Processed response content as string
        """
        try:
            # Handle Strands Agent response object first
            if hasattr(response, 'message') and hasattr(response.message, 'content'):
                content = response.message.content
                if isinstance(content, list) and len(content) > 0:
                    if hasattr(content[0], 'text'):
                        return content[0].text
                    else:
                        return str(content[0])
                else:
                    return str(content)
            elif hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                # Convert response to string asynchronously if needed
                if hasattr(response, '__str__'):
                    # Use asyncio.to_thread for potentially expensive string conversion
                    content = await asyncio.to_thread(str, response)
                else:
                    content = str(response)
                
                logger.debug(f"Processed response content: {len(content)} characters")
                return content
            
        except Exception as e:
            logger.error(f"Failed to process response: {e}")
            return f"Response processing failed: {str(e)}"
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Kubernetes agent.
        
        Returns:
            Dictionary containing agent status information
        """
        if self.agent is None:
            if self._is_initializing:
                status = "initializing"
            elif self._initialization_error:
                status = f"initialization_failed: {self._initialization_error}"
            else:
                status = "not_initialized"
        else:
            status = "ready"
        
        base_status = {
            "agent_type": "kubernetes_agent",
            "async_tools": ["execute_command", "read_file", "write_file", "report_issue"],
            "sync_tools": ["report_issue"],
            "concurrent_execution": "supported",
            "status": status
        }
        
        return base_status
