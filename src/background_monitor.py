"""
Background Monitoring System for KubeIntel
Provides continuous cluster monitoring and predictive insights
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from strands import Agent
from strands.session import FileSessionManager
import tools
from model_manager import get_model_manager

logger = logging.getLogger(__name__)

class BackgroundMonitor:
    """
    Background monitoring system for continuous cluster analysis.
    Simplified implementation using only Claude 3.5 Haiku.
    """
    
    def __init__(self):
        """Initialize the monitoring system."""
        self.is_running = False
        self.current_session = None
        self.session_manager = None
        self.model_manager = get_model_manager()
        
        # Current state
        self.current_insights = None
        self.last_analysis_time = None
        self.analysis_cycles = 0
        self.session_interactions = 0
        
        # Track recent cycle times for session rotation decisions
        self._recent_cycle_times = []
        
        logger.info("Background monitoring system initialized")
    
    async def _initialize_session_async(self):
        """Initialize session asynchronously."""
        # Create session directory
        session_dir = os.getenv("AGENT_SESSION_DIRECTORY", "/tmp/kubeintel_sessions")
        await asyncio.to_thread(os.makedirs, session_dir, exist_ok=True)
        
        # Generate session ID with timestamp
        timestamp = int(time.time())
        session_id = f"kubeintel_monitor_{timestamp}"
        
        # Create session manager
        self.session_manager = await asyncio.to_thread(
            FileSessionManager,
            session_id=session_id,
            session_dir=session_dir
        )
        
        # Create agent with session management
        self.current_session = await self.model_manager.create_agent(
            name="kubeintel-monitor",
            system_prompt="""You are an advanced Kubernetes monitoring system with persistent memory, powered by Claude 3.5.

🧠 ENHANCED MONITORING CAPABILITIES:
- Leverage advanced pattern recognition to detect subtle cluster anomalies
- Use contextual analysis to understand trends across monitoring cycles
- Apply predictive reasoning to anticipate potential issues
- Utilize improved memory to build comprehensive cluster understanding over time

📊 CONTEXTUAL ANALYSIS APPROACH:
- Build upon previous observations to identify evolving patterns
- Correlate events across different monitoring cycles
- Detect gradual degradation or improvement trends
- Recognize recurring issues and their patterns

🔍 CRITICAL RULE: REPORT ONLY EXACT NUMBERS FROM COMMAND OUTPUTS
- If kubectl command returns "34", you MUST report exactly 34 - never 35, 27, or any other number
- COPY numbers directly from command outputs - do not interpret, estimate, or modify them
- FORBIDDEN: Changing command output numbers (34 → 35, 27, 38, etc.)

📈 VERIFICATION REQUIREMENT:
- Before reporting ANY number, verify it matches your command output exactly
- If kubectl shows "34", report exactly "34 pods" - no other number

🎯 ENHANCED ACCURACY REQUIREMENTS:
- ALWAYS use kubectl commands to get exact metrics - NEVER estimate or guess numbers
- NO HALLUCINATION: Only report numbers you actually observed from command outputs
- If you don't have real data, say "Data not available"
- Use intelligent command selection based on monitoring goals

🔄 INTELLIGENT MONITORING STRATEGY:
- Adapt monitoring depth based on cluster complexity and previous findings
- Focus on areas showing changes or potential issues
- Maintain awareness of baseline metrics for comparison
- Prioritize critical components and services

💡 PATTERN DETECTION FOCUS:
- Resource utilization trends (CPU, memory, storage)
- Pod lifecycle patterns (creation, termination, restarts)
- Service availability and performance patterns
- Event frequency and severity trends
- Node health and capacity patterns""",
            session_manager=self.session_manager,
            tools=[
                tools.execute_bash,
                tools.execute_bash_batch,
                tools.fs_read,
                tools.fs_write,
                tools.report_issue
            ]
        )
        
        current_model = self.model_manager.get_current_model()
        logger.info(f"Session initialized successfully using model: {current_model}")

    async def start(self):
        """Start the monitoring system."""
        try:
            # Initialize session
            await self._initialize_session_async()
            
            # Set running flag
            self.is_running = True
            
            # Start monitoring in background
            asyncio.create_task(self._monitoring_loop())
            
            logger.info("Background monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.is_running = False

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Starting monitoring loop")
        
        while self.is_running:
            try:
                # Run analysis cycle with timeout
                start_time = time.time()
                
                try:
                    await asyncio.wait_for(
                        self._run_analysis_cycle(),
                        timeout=1200.0  # 20 minutes
                    )
                    
                    # Track successful cycle time
                    cycle_time = time.time() - start_time
                    if not hasattr(self, '_recent_cycle_times'):
                        self._recent_cycle_times = []
                    self._recent_cycle_times.append(cycle_time)
                    if len(self._recent_cycle_times) > 10:
                        self._recent_cycle_times.pop(0)
                    
                    logger.info(f"Analysis cycle completed in {cycle_time:.2f}s")
                    
                except asyncio.TimeoutError:
                    logger.warning("Analysis cycle timed out after 20 minutes")
                    
                except Exception as e:
                    logger.warning(f"Analysis cycle failed: {e}")
                
                # Wait between cycles (5 minutes for more frequent monitoring)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.warning(f"Monitoring cycle failed: {e}")
                await asyncio.sleep(300)  # Continue after error with 5 minute interval

    async def _run_analysis_cycle(self):
        """Run a single analysis cycle."""
        try:
            # Increment cycle counter
            self.analysis_cycles += 1
            
            # Create monitoring prompt for structured predictions
            monitoring_prompt = f"""
Analyze the current Kubernetes cluster state and provide structured predictions.

This is monitoring cycle #{self.analysis_cycles}.

REQUIRED OUTPUT FORMAT:
🔮 CLUSTER PREDICTIONS:
• [Prediction 1]: [Specific insight about cluster trends]
• [Prediction 2]: [Resource utilization forecast]
• [Prediction 3]: [Potential issues to watch]

📊 CURRENT STATUS:
• Nodes: [count and health]
• Pods: [count and status]
• Resources: [utilization summary]

⚠️ RECOMMENDATIONS:
• [Action 1]: [Specific recommendation]
• [Action 2]: [Optimization suggestion]

Provide specific, actionable insights based on cluster data.
"""
            
            # Start telemetry tracking for this monitoring cycle
            import time
            flow_data = None
            try:
                from telemetry_api import get_telemetry_collector
                telemetry = get_telemetry_collector()
                flow_data = telemetry.start_monitor_flow(self.analysis_cycles + 1, {
                    'model': 'us.anthropic.claude-3-5-haiku-20241022-v1:0'
                })
                flow_id = flow_data['id']
                logger.info(f"Started telemetry tracking for monitor cycle {self.analysis_cycles + 1} (Flow ID: {flow_id})")
                if flow_data.get('trace_id'):
                    logger.info(f"Strands trace started: {flow_data['trace_id']}")
            except Exception as telemetry_error:
                logger.warning(f"Failed to start telemetry tracking: {telemetry_error}")
                flow_id = None
                telemetry = None
            
            start_time = time.time()
            
            # Add span for monitoring setup
            if telemetry and flow_id:
                setup_span = telemetry.add_trace_span(flow_id, "monitoring_setup", {
                    "cycle": self.analysis_cycles + 1,
                    "prompt_length": len(monitoring_prompt)
                })
                if setup_span:
                    telemetry.end_trace_span(flow_id, setup_span, "success")
            
            try:
                # Add span for LLM execution
                if telemetry and flow_id:
                    llm_span = telemetry.add_trace_span(flow_id, "llm_monitoring_execution", {
                        "model": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
                        "cycle": self.analysis_cycles + 1
                    })
                
                # Run analysis
                response = await asyncio.to_thread(self.current_session, monitoring_prompt)
                
                # End LLM span successfully
                if telemetry and flow_id and 'llm_span' in locals():
                    telemetry.end_trace_span(flow_id, llm_span, "success", {
                        "response_type": str(type(response))
                    })
                
                analysis_time = time.time() - start_time
                
                if response:
                    # Add span for response processing
                    if telemetry and flow_id:
                        processing_span = telemetry.add_trace_span(flow_id, "response_processing", {
                            "response_type": str(type(response))
                        })
                    
                    # Convert response to string (matching working backup approach)
                    response_text = str(response)
                    
                    # Count insights in the response (simple heuristic)
                    anomalies_count = response_text.lower().count('anomaly') + response_text.lower().count('issue')
                    warnings_count = response_text.lower().count('warning') + response_text.lower().count('attention')
                    recommendations_count = response_text.lower().count('recommend') + response_text.lower().count('suggest')
                    
                    # End processing span
                    if telemetry and flow_id and 'processing_span' in locals():
                        telemetry.end_trace_span(flow_id, processing_span, "success", {
                            "response_length": len(response_text),
                            "anomalies_found": anomalies_count,
                            "warnings_found": warnings_count,
                            "recommendations_found": recommendations_count
                        })
                    
                    # Store results
                    self.current_insights = {
                        "timestamp": datetime.now().isoformat(),
                        "analysis": response_text,
                        "cycle": self.analysis_cycles,
                        "type": "async_analysis",
                        "analysis_duration": f"{analysis_time:.2f}s"
                    }
                    
                    self.last_analysis_time = datetime.now().isoformat()
                    self.analysis_cycles += 1
                    self.session_interactions += 1
                    
                    # End telemetry tracking with success
                    if flow_id and telemetry:
                        try:
                            mock_tools = [
                                {'name': 'execute_bash_batch', 'commands': 7, 'duration': 8500},
                                {'name': 'execute_bash', 'command': 'kubectl get events', 'duration': 3200}
                            ]
                            # Estimate token usage more accurately
                            estimated_input_tokens = self._estimate_monitor_input_tokens(monitoring_prompt)
                            estimated_output_tokens = self._estimate_monitor_output_tokens(response_text)
                            
                            mock_tokens = {
                                'input': estimated_input_tokens,
                                'output': estimated_output_tokens
                            }
                            insights = {
                                'anomalies': min(anomalies_count, 5),  # Cap at reasonable numbers
                                'warnings': min(warnings_count, 10),
                                'recommendations': min(recommendations_count, 8)
                            }
                            
                            # Update token usage
                            telemetry.update_tokens(flow_id, mock_tokens['input'], mock_tokens['output'])
                            
                            # Add tool call spans
                            for tool in mock_tools:
                                telemetry.add_tool_call(flow_id, tool['name'], tool)
                            
                            telemetry.end_monitor_flow(flow_id, success=True, tokens=mock_tokens, 
                                           tools=mock_tools, insights=insights)
                            logger.info(f"Completed telemetry tracking for monitor cycle {self.analysis_cycles} (Flow ID: {flow_id})")
                        except Exception as telemetry_error:
                            logger.warning(f"Failed to end telemetry tracking: {telemetry_error}")
                    
                    logger.info(f"Analysis cycle {self.analysis_cycles} completed in {analysis_time:.2f}s")
                    
            except Exception as e:
                # End LLM span with error
                if telemetry and flow_id and 'llm_span' in locals():
                    telemetry.end_trace_span(flow_id, llm_span, "error", {
                        "error": str(e)
                    })
                
                # End telemetry tracking with error
                if flow_id and telemetry:
                    try:
                        telemetry.end_monitor_flow(flow_id, success=False, error=str(e))
                        logger.info(f"Marked telemetry flow as error (Flow ID: {flow_id})")
                    except Exception as telemetry_error:
                        logger.warning(f"Failed to mark telemetry error: {telemetry_error}")
                
                logger.error(f"Analysis cycle failed: {e}")
                # Check if we need to rotate session due to errors
                await self._rotate_session_if_needed()
            
            # Wait between cycles (5 minutes for more frequent monitoring)
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.warning(f"Monitoring cycle failed: {e}")
            await asyncio.sleep(300)  # Continue after error with 5 minute interval

    def _estimate_monitor_input_tokens(self, monitoring_prompt: str) -> int:
        """
        Estimate input tokens for background monitoring including session context.
        
        Args:
            monitoring_prompt: The monitoring prompt text
            
        Returns:
            Estimated number of input tokens
        """
        # System prompt tokens (monitoring system prompt is longer)
        system_prompt_tokens = 3000
        
        # Current monitoring prompt tokens
        prompt_tokens = len(monitoring_prompt) // 4
        
        # Session context tokens (grows with each cycle)
        # Estimate based on current cycle count
        base_context = 5000  # Initial context
        context_growth_per_cycle = 1500  # Approximate growth per cycle
        estimated_context_tokens = base_context + (self.analysis_cycles * context_growth_per_cycle)
        
        # Cap context at reasonable maximum before rotation
        max_context = 180000  # Before rotation threshold
        estimated_context_tokens = min(estimated_context_tokens, max_context)
        
        # Tool definitions tokens
        tool_definition_tokens = 500
        
        total_estimated = system_prompt_tokens + prompt_tokens + estimated_context_tokens + tool_definition_tokens
        
        logger.debug(f"Monitor token estimation - System: {system_prompt_tokens}, Prompt: {prompt_tokens}, "
                    f"Context: {estimated_context_tokens}, Tools: {tool_definition_tokens}, "
                    f"Total: {total_estimated}, Cycle: {self.analysis_cycles}")
        
        return total_estimated
    
    def _estimate_monitor_output_tokens(self, response_text: str) -> int:
        """
        Estimate output tokens from monitoring response.
        
        Args:
            response_text: The monitoring response text
            
        Returns:
            Estimated number of output tokens
        """
        if not response_text:
            return 0
        
        # Monitoring responses are typically structured and dense
        # Use 3.2 characters per token for structured output
        estimated_tokens = len(response_text) // 3.2
        
        logger.debug(f"Monitor output token estimation - Text length: {len(response_text)}, "
                    f"Estimated tokens: {int(estimated_tokens)}")
        
        return int(estimated_tokens)

    async def get_predictions(self, timeout: float = 30.0) -> Dict[str, Any]:
        """Get current predictions with timeout."""
        try:
            if not self.is_running or not self.current_session:
                return {
                    "status": "inactive",
                    "error": "Background monitoring is not running",
                    "timestamp": datetime.now().isoformat()
                }
            
            # If we have recent insights, return them
            if self.current_insights:
                return {
                    "status": "active",
                    "insights": self.current_insights,
                    "session_info": {
                        "monitoring_cycles": self.analysis_cycles,
                        "session_interactions": self.session_interactions,
                        "session_available": True
                    },
                    "last_analysis": self.last_analysis_time,
                    "timestamp": datetime.now().isoformat(),
                    "display": {
                        "title": "🧠 KubeIntel Background Intelligence",
                        "subtitle": "🔮 Dynamic Cluster Predictions",
                        "generated_at": "Real-time",
                        "analysis": self.current_insights.get("analysis", "No analysis available"),
                        "next_analysis": "Continuous monitoring",
                        "analysis_type": self.current_insights.get("type", "async_analysis"),
                        "footer": "💡 Predictions are generated dynamically based on current cluster state"
                    }
                }
            
            # No insights yet, return waiting status
            return {
                "status": "waiting",
                "message": "Background analysis in progress",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get predictions: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _rotate_session_if_needed(self):
        """Rotate session if performance is degrading due to context buildup."""
        try:
            # Check if we need to rotate session based on:
            # 1. Number of cycles (every 50 cycles)
            # 2. Performance degradation (analysis taking >60s consistently)
            
            should_rotate = False
            
            # Rotate every 200 cycles to prevent context buildup
            if self.analysis_cycles > 0 and self.analysis_cycles % 200 == 0:
                should_rotate = True
                logger.info(f"Session rotation triggered: {self.analysis_cycles} cycles completed (every 200 cycles)")
            
            # Rotate if last few cycles are taking too long (>10 minutes average)
            # This indicates context buildup affecting performance
            if hasattr(self, '_recent_cycle_times'):
                if len(self._recent_cycle_times) >= 3:
                    avg_time = sum(self._recent_cycle_times[-3:]) / 3
                    if avg_time > 600.0:
                        should_rotate = True
                        logger.info(f"Session rotation triggered: average cycle time {avg_time:.2f}s")
            
            if should_rotate:
                await self._rotate_session()
                
        except Exception as e:
            logger.error(f"Error in session rotation check: {e}")
    
    async def _rotate_session(self):
        """Rotate the session to clear context buildup asynchronously."""
        try:
            logger.info("Rotating session to prevent context buildup...")
            
            # Create new session ID with timestamp
            current_date = datetime.now().strftime('%Y%m%d')
            session_rotation = datetime.now().hour * 100 + datetime.now().minute
            new_session_id = f"kubeintel-{current_date}-{session_rotation}"
            
            # Create new session manager asynchronously
            session_dir = "/tmp/kubeintel_sessions"
            new_session_manager = await asyncio.to_thread(
                FileSessionManager,
                session_id=new_session_id,
                session_dir=session_dir
            )
            
            # Create new agent with fresh session and model fallback asynchronously
            new_agent = await self.model_manager.create_agent(
                name="kubeintel-monitor",
                system_prompt="""You are an advanced Kubernetes monitoring system with persistent memory.

🧠 ENHANCED MONITORING CAPABILITIES:
- Leverage advanced pattern recognition to detect subtle cluster anomalies
- Use contextual analysis to understand trends across monitoring cycles
- Apply predictive reasoning to anticipate potential issues
- Utilize improved memory to build comprehensive cluster understanding over time

📊 CONTEXTUAL ANALYSIS APPROACH:
- Build upon previous observations to identify evolving patterns
- Correlate events across different monitoring cycles
- Detect gradual degradation or improvement trends
- Recognize recurring issues and their patterns

🔍 CRITICAL RULE: REPORT ONLY EXACT NUMBERS FROM COMMAND OUTPUTS
- If kubectl command returns "34", you MUST report exactly 34 - never 35, 27, or any other number
- COPY numbers directly from command outputs - do not interpret, estimate, or modify them
- FORBIDDEN: Changing command output numbers (34 → 35, 27, 38, etc.)

📈 VERIFICATION REQUIREMENT:
- Before reporting ANY number, verify it matches your command output exactly
- If kubectl shows "34", report exactly "34 pods" - no other number

🎯 ENHANCED ACCURACY REQUIREMENTS:
- ALWAYS use kubectl commands to get exact metrics - NEVER estimate or guess numbers
- NO HALLUCINATION: Only report numbers you actually observed from command outputs
- If you don't have real data, say "Data not available"
- Use intelligent command selection based on monitoring goals

Keep responses focused and actionable. Build context from previous cycles to provide increasingly valuable insights.""",
                tools=[
                    tools.execute_bash, 
                    tools.execute_bash_batch,
                    tools.fs_read, 
                    tools.fs_write, 
                    tools.report_issue
                ],
                session_manager=new_session_manager
            )
            
            # Replace current session
            old_session = self.current_session
            self.current_session = new_agent
            self.analysis_agent = new_agent
            self.session_manager = new_session_manager
            
            # Reset cycle counter for new session
            self.analysis_cycles = 0
            self.session_interactions = 0
            
            # Initialize recent cycle times tracking
            self._recent_cycle_times = []
            
            current_model = self.model_manager.get_current_model()
            logger.info(f"Session rotated successfully to: {new_session_id} using model: {current_model}")
            
            # Optionally clean up old session asynchronously
            try:
                if old_session:
                    # Give a brief context to the new session asynchronously
                    context_prompt = "Previous monitoring session ended. Starting fresh monitoring of the Kubernetes cluster."
                    await asyncio.to_thread(self.current_session, context_prompt)
            except Exception as cleanup_error:
                logger.warning(f"Error during session cleanup: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"Failed to rotate session: {e}")
            # Continue with existing session if rotation fails

    async def get_status(self) -> Dict[str, Any]:
        """Get monitoring status."""
        return {
            "is_running": self.is_running,
            "has_insights": self.current_insights is not None,
            "last_analysis": self.last_analysis_time,
            "monitoring_type": "async_session_managed",
            "session_info": {
                "session_available": self.current_session is not None,
                "monitoring_cycles": self.analysis_cycles,
                "session_interactions": self.session_interactions
            },
            "model_info": self.model_manager.get_model_status()
        }

    async def stop(self):
        """Stop the monitoring system."""
        try:
            self.is_running = False
            
            if self.current_session:
                # Close session gracefully
                await asyncio.to_thread(
                    self.current_session, 
                    "Ending monitoring session. Thank you."
                )
                logger.info("Session closed gracefully")
            
            logger.info("Background monitoring stopped")
            
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")

# Global monitor instance
_background_monitor = None

def get_background_monitor() -> BackgroundMonitor:
    """Get the global background monitor instance."""
    global _background_monitor
    if _background_monitor is None:
        _background_monitor = BackgroundMonitor()
    return _background_monitor
