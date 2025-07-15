"""
Telemetry API for KubeIntel Flow Visualizer
Provides Strands telemetry data for agent flows and background monitoring
Includes Strands Trace integration for detailed execution tracking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import os
from collections import deque

# Import Strands telemetry components
try:
    from strands.telemetry.metrics import Trace, MetricsClient
    STRANDS_TELEMETRY_AVAILABLE = True
except ImportError:
    STRANDS_TELEMETRY_AVAILABLE = False
    logging.warning("Strands telemetry not available - using mock implementation")

logger = logging.getLogger(__name__)

class TelemetryCollector:
    """
    Collects and manages telemetry data for agent flows and background monitoring.
    Integrates with Strands telemetry system including Trace functionality.
    """
    
    def __init__(self):
        # Get configurable limits from environment variables
        agent_flows_limit = int(os.getenv("AGENT_TELEMETRY_AGENT_FLOWS_LIMIT", "50"))
        monitor_flows_limit = int(os.getenv("AGENT_TELEMETRY_MONITOR_FLOWS_LIMIT", "100"))
        traces_limit = int(os.getenv("AGENT_TELEMETRY_TRACES_LIMIT", "200"))
        
        self.agent_flows = deque(maxlen=agent_flows_limit)  # Configurable agent flows limit
        self.monitor_flows = deque(maxlen=monitor_flows_limit)  # Configurable monitor cycles limit
        self.active_flows = {}  # Track currently active flows
        self.traces = deque(maxlen=traces_limit)  # Configurable traces limit
        
        # Initialize Strands telemetry if available
        self.metrics_client = None
        self.traces_enabled = STRANDS_TELEMETRY_AVAILABLE
        
        if STRANDS_TELEMETRY_AVAILABLE:
            try:
                self.metrics_client = MetricsClient()
                logger.info("Strands MetricsClient initialized successfully")
                
                # Verify trace creation API
                test_trace = Trace(name="test_trace", metadata={"test": True})
                logger.info(f"Strands Trace test successful: {type(test_trace)}")
                
                # Check available methods
                trace_methods = [method for method in dir(test_trace) if not method.startswith('_')]
                logger.info(f"Available Trace methods: {trace_methods}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize Strands MetricsClient: {e}")
                self.traces_enabled = False
        
        logger.info(f"Telemetry collector initialized (traces_enabled: {self.traces_enabled})")
    
    def _create_strands_trace(self, name: str, metadata: Dict[str, Any]) -> tuple:
        """Create a Strands trace with proper error handling."""
        if not self.traces_enabled:
            return None, f"mock-trace-{name}-{int(datetime.utcnow().timestamp())}"
        
        try:
            # Try different Trace constructor approaches
            trace = None
            trace_id = None
            
            # Approach 1: Basic constructor
            try:
                trace = Trace(name=name, metadata=metadata)
                trace_id = getattr(trace, 'id', None) or getattr(trace, 'trace_id', None)
                if trace_id:
                    logger.info(f"Strands trace created successfully: {trace_id}")
                    return trace, trace_id
            except Exception as e1:
                logger.debug(f"Trace creation approach 1 failed: {e1}")
            
            # Approach 2: Constructor with different parameters
            try:
                trace = Trace(name)
                if hasattr(trace, 'set_metadata'):
                    trace.set_metadata(metadata)
                trace_id = getattr(trace, 'id', None) or getattr(trace, 'trace_id', None)
                if trace_id:
                    logger.info(f"Strands trace created with approach 2: {trace_id}")
                    return trace, trace_id
            except Exception as e2:
                logger.debug(f"Trace creation approach 2 failed: {e2}")
            
            # Approach 3: Use metrics client if available
            if self.metrics_client and hasattr(self.metrics_client, 'create_trace'):
                try:
                    trace = self.metrics_client.create_trace(name, metadata)
                    trace_id = getattr(trace, 'id', None) or getattr(trace, 'trace_id', None)
                    if trace_id:
                        logger.info(f"Strands trace created with metrics client: {trace_id}")
                        return trace, trace_id
                except Exception as e3:
                    logger.debug(f"Trace creation approach 3 failed: {e3}")
            
            # If all approaches fail, create mock trace ID
            logger.warning(f"All Strands trace creation approaches failed, using mock trace")
            return None, f"mock-trace-{name}-{int(datetime.utcnow().timestamp())}"
            
        except Exception as e:
            logger.warning(f"Failed to create Strands trace: {e}")
            return None, f"mock-trace-{name}-{int(datetime.utcnow().timestamp())}"
    
    def start_agent_flow(self, flow_id: str, request: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start tracking an agent analysis flow with trace integration."""
        flow_data = {
            'id': flow_id,
            'type': 'agent_analysis',
            'status': 'running',
            'startTime': datetime.utcnow().isoformat(),
            'endTime': None,
            'duration': None,
            'request': request,
            'tools': [],
            'model': metadata.get('model', 'unknown') if metadata else 'unknown',
            'tokens': {'input': 0, 'output': 0},
            'metadata': metadata or {},
            'error': None,
            'trace_id': None,
            'spans': []
        }
        
        # Start Strands trace if available
        if self.traces_enabled and self.metrics_client:
            try:
                # Create trace with proper Strands API
                trace = Trace(
                    name=f"agent_analysis_{flow_id}",
                    metadata={
                        'flow_id': flow_id,
                        'request_type': 'agent_analysis',
                        'scope': metadata.get('scope', 'unknown') if metadata else 'unknown',
                        'model': metadata.get('model', 'unknown') if metadata else 'unknown'
                    }
                )
                
                # Get trace ID from the trace object
                trace_id = getattr(trace, 'id', None) or getattr(trace, 'trace_id', None) or f"trace-{flow_id}"
                flow_data['trace_id'] = trace_id
                flow_data['trace'] = trace
                
                logger.info(f"Started Strands trace for agent flow: {flow_id} (trace_id: {trace_id})")
            except Exception as e:
                logger.warning(f"Failed to start trace for agent flow {flow_id}: {e}")
                # Create a mock trace ID for consistency
                flow_data['trace_id'] = f"mock-trace-{flow_id}"
        else:
            # Create a mock trace ID when Strands is not available
            flow_data['trace_id'] = f"mock-trace-{flow_id}"
        
        self.active_flows[flow_id] = flow_data
        logger.info(f"Started tracking agent flow: {flow_id}")
        return flow_data
    
    def end_agent_flow(self, flow_id: str, success: bool = True, error: str = None, 
                      tokens: Dict[str, int] = None, tools: List[Dict] = None) -> Dict[str, Any]:
        """End tracking an agent analysis flow with trace completion."""
        if flow_id not in self.active_flows:
            logger.warning(f"Attempted to end unknown flow: {flow_id}")
            return None
        
        flow_data = self.active_flows[flow_id]
        end_time = datetime.utcnow()
        start_time = datetime.fromisoformat(flow_data['startTime'].replace('Z', '+00:00'))
        
        flow_data.update({
            'status': 'completed' if success else 'error',
            'endTime': end_time.isoformat(),
            'duration': int((end_time - start_time).total_seconds() * 1000),  # milliseconds
            'tokens': tokens or {'input': 0, 'output': 0},
            'tools': tools or [],
            'error': error
        })
        
        # Always create a trace entry (Strands or mock)
        trace_created = False
        is_strands_trace = flow_data.get('strands_trace_active', False)
        
        # Try Strands trace if available
        if self.traces_enabled and 'trace' in flow_data and is_strands_trace:
            try:
                trace = flow_data['trace']
                
                # Try different methods to end the trace
                if hasattr(trace, 'end'):
                    try:
                        trace.end()  # Try without parameters first
                    except:
                        trace.end(status='success' if success else 'error')
                elif hasattr(trace, 'finish'):
                    trace.finish()
                elif hasattr(trace, 'close'):
                    trace.close()
                
                # Extract spans from trace for storage (or use pending spans)
                if hasattr(flow_data, '_pending_spans'):
                    flow_data['spans'] = flow_data['_pending_spans']
                else:
                    flow_data['spans'] = self._extract_trace_spans(trace)
                
                # Store trace in traces collection
                self.traces.append({
                    'trace_id': flow_data['trace_id'],
                    'flow_id': flow_id,
                    'type': 'agent_analysis',
                    'name': getattr(trace, 'name', f"agent_analysis_{flow_id}"),
                    'status': 'success' if success else 'error',
                    'startTime': flow_data['startTime'],
                    'endTime': flow_data['endTime'],
                    'duration': flow_data['duration'],
                    'spans': flow_data['spans'],
                    'metadata': dict(getattr(trace, 'metadata', {}), **{'type': 'strands_trace'})
                })
                
                trace_created = True
                logger.info(f"Completed Strands trace for agent flow: {flow_id} (trace_id: {flow_data['trace_id']})")
            except Exception as e:
                logger.warning(f"Failed to end trace for agent flow {flow_id}: {e}")
        
        # Always create a trace entry if one wasn't created above
        if not trace_created and flow_data.get('trace_id'):
            self.traces.append({
                'trace_id': flow_data['trace_id'],
                'flow_id': flow_id,
                'type': 'agent_analysis',
                'name': f"agent_analysis_{flow_id}",
                'status': 'success' if success else 'error',
                'startTime': flow_data['startTime'],
                'endTime': flow_data['endTime'],
                'duration': flow_data['duration'],
                'spans': self._create_mock_spans(flow_data, tools),
                'metadata': dict(flow_data.get('metadata', {}), **{'type': 'mock_trace' if not is_strands_trace else 'strands_trace_fallback'})
            })
            logger.info(f"Created {'fallback' if is_strands_trace else 'mock'} trace for agent flow: {flow_id} (trace_id: {flow_data['trace_id']})")
        
        # Remove trace object to avoid serialization issues
        if 'trace' in flow_data:
            del flow_data['trace']
        
        # Move to completed flows
        self.agent_flows.append(flow_data.copy())
        del self.active_flows[flow_id]
        
        logger.info(f"Completed tracking agent flow: {flow_id} (success: {success})")
        return flow_data
    
    def start_monitor_flow(self, cycle: int, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start tracking a background monitor flow with trace integration."""
        flow_id = f"monitor-cycle-{cycle}-{int(datetime.utcnow().timestamp())}"
        
        flow_data = {
            'id': flow_id,
            'type': 'background_monitor',
            'status': 'running',
            'startTime': datetime.utcnow().isoformat(),
            'endTime': None,
            'duration': None,
            'cycle': cycle,
            'tools': [],
            'model': metadata.get('model', 'unknown') if metadata else 'unknown',
            'tokens': {'input': 0, 'output': 0},
            'insights': {'anomalies': 0, 'warnings': 0, 'recommendations': 0},
            'error': None,
            'trace_id': None,
            'spans': []
        }
        
        # Start Strands trace if available
        if self.traces_enabled and self.metrics_client:
            try:
                # Create trace with proper Strands API
                trace = Trace(
                    name=f"background_monitor_cycle_{cycle}",
                    metadata={
                        'flow_id': flow_id,
                        'request_type': 'background_monitor',
                        'cycle': cycle,
                        'model': metadata.get('model', 'unknown') if metadata else 'unknown'
                    }
                )
                
                # Get trace ID from the trace object
                trace_id = getattr(trace, 'id', None) or getattr(trace, 'trace_id', None) or f"trace-{flow_id}"
                flow_data['trace_id'] = trace_id
                flow_data['trace'] = trace
                
                logger.info(f"Started Strands trace for monitor flow: {flow_id} (trace_id: {trace_id})")
            except Exception as e:
                logger.warning(f"Failed to start trace for monitor flow {flow_id}: {e}")
                # Create a mock trace ID for consistency
                flow_data['trace_id'] = f"mock-trace-{flow_id}"
        else:
            # Create a mock trace ID when Strands is not available
            flow_data['trace_id'] = f"mock-trace-{flow_id}"
        
        self.active_flows[flow_id] = flow_data
        logger.info(f"Started tracking monitor flow: {flow_id} (cycle {cycle})")
        return flow_data
    
    def end_monitor_flow(self, flow_id: str, success: bool = True, error: str = None,
                        tokens: Dict[str, int] = None, tools: List[Dict] = None,
                        insights: Dict[str, int] = None) -> Dict[str, Any]:
        """End tracking a background monitor flow with trace completion."""
        if flow_id not in self.active_flows:
            logger.warning(f"Attempted to end unknown monitor flow: {flow_id}")
            return None
        
        flow_data = self.active_flows[flow_id]
        end_time = datetime.utcnow()
        start_time = datetime.fromisoformat(flow_data['startTime'].replace('Z', '+00:00'))
        
        flow_data.update({
            'status': 'completed' if success else ('timeout' if 'timeout' in (error or '') else 'error'),
            'endTime': end_time.isoformat(),
            'duration': int((end_time - start_time).total_seconds() * 1000),  # milliseconds
            'tokens': tokens or {'input': 0, 'output': 0},
            'tools': tools or [],
            'insights': insights or {'anomalies': 0, 'warnings': 0, 'recommendations': 0},
            'error': error
        })
        
        # Always create a trace entry (Strands or mock)
        trace_created = False
        is_strands_trace = flow_data.get('strands_trace_active', False)
        
        # Try Strands trace if available
        if self.traces_enabled and 'trace' in flow_data and is_strands_trace:
            try:
                trace = flow_data['trace']
                
                # Try different methods to end the trace
                if hasattr(trace, 'end'):
                    try:
                        trace.end()  # Try without parameters first
                    except:
                        trace.end(status='success' if success else 'error')
                elif hasattr(trace, 'finish'):
                    trace.finish()
                elif hasattr(trace, 'close'):
                    trace.close()
                
                # Extract spans from trace for storage (or use pending spans)
                if hasattr(flow_data, '_pending_spans'):
                    flow_data['spans'] = flow_data['_pending_spans']
                else:
                    flow_data['spans'] = self._extract_trace_spans(trace)
                
                # Store trace in traces collection
                self.traces.append({
                    'trace_id': flow_data['trace_id'],
                    'flow_id': flow_id,
                    'type': 'background_monitor',
                    'name': getattr(trace, 'name', f"background_monitor_cycle_{flow_data.get('cycle', 0)}"),
                    'status': 'success' if success else 'error',
                    'startTime': flow_data['startTime'],
                    'endTime': flow_data['endTime'],
                    'duration': flow_data['duration'],
                    'spans': flow_data['spans'],
                    'metadata': dict(getattr(trace, 'metadata', {}), **{'cycle': flow_data.get('cycle', 0), 'type': 'strands_trace'})
                })
                
                trace_created = True
                logger.info(f"Completed Strands trace for monitor flow: {flow_id} (trace_id: {flow_data['trace_id']})")
            except Exception as e:
                logger.warning(f"Failed to end trace for monitor flow {flow_id}: {e}")
        
        # Always create a trace entry if one wasn't created above
        if not trace_created and flow_data.get('trace_id'):
            self.traces.append({
                'trace_id': flow_data['trace_id'],
                'flow_id': flow_id,
                'type': 'background_monitor',
                'name': f"background_monitor_cycle_{flow_data.get('cycle', 0)}",
                'status': 'success' if success else 'error',
                'startTime': flow_data['startTime'],
                'endTime': flow_data['endTime'],
                'duration': flow_data['duration'],
                'spans': self._create_mock_spans(flow_data, tools),
                'metadata': {'cycle': flow_data.get('cycle', 0), 'type': 'mock_trace' if not is_strands_trace else 'strands_trace_fallback'}
            })
            logger.info(f"Created {'fallback' if is_strands_trace else 'mock'} trace for monitor flow: {flow_id} (trace_id: {flow_data['trace_id']})")
        
        # Remove trace object to avoid serialization issues
        if 'trace' in flow_data:
            del flow_data['trace']
        
        # Move to completed flows
        self.monitor_flows.append(flow_data.copy())
        del self.active_flows[flow_id]
        
        logger.info(f"Completed tracking monitor flow: {flow_id} (success: {success})")
        return flow_data
    
    def _create_mock_spans(self, flow_data: Dict[str, Any], tools: List[Dict] = None) -> List[Dict[str, Any]]:
        """Create realistic mock spans when Strands trace is not available."""
        spans = []
        
        start_time = datetime.fromisoformat(flow_data['startTime'].replace('Z', '+00:00'))
        current_time = start_time
        
        # Add initialization span
        init_duration = 500  # 500ms for initialization
        init_end = current_time + timedelta(milliseconds=init_duration)
        spans.append({
            'span_id': f"span-init-{flow_data['id']}",
            'name': 'initialization',
            'start_time': current_time.isoformat(),
            'end_time': init_end.isoformat(),
            'duration': init_duration,
            'status': 'success',
            'metadata': {'type': 'initialization', 'component': 'agent_setup'}
        })
        current_time = init_end
        
        # Add LLM execution span (main processing)
        llm_duration = max(flow_data.get('duration', 10000) - 2000, 5000)  # Most of the time
        llm_end = current_time + timedelta(milliseconds=llm_duration)
        spans.append({
            'span_id': f"span-llm-{flow_data['id']}",
            'name': 'llm_execution',
            'start_time': current_time.isoformat(),
            'end_time': llm_end.isoformat(),
            'duration': llm_duration,
            'status': 'success',
            'metadata': {
                'type': 'llm_processing',
                'model': flow_data.get('model', 'unknown'),
                'tokens_input': flow_data.get('tokens', {}).get('input', 0),
                'tokens_output': flow_data.get('tokens', {}).get('output', 0)
            }
        })
        current_time = llm_end
        
        # Add tool execution spans
        if tools:
            for i, tool in enumerate(tools):
                tool_duration = tool.get('duration', 1000)
                tool_end = current_time + timedelta(milliseconds=tool_duration)
                spans.append({
                    'span_id': f"span-tool-{i}-{flow_data['id']}",
                    'name': f"tool_execution_{tool.get('name', 'unknown')}",
                    'start_time': current_time.isoformat(),
                    'end_time': tool_end.isoformat(),
                    'duration': tool_duration,
                    'status': 'success',
                    'metadata': {
                        'tool_name': tool.get('name', 'unknown'),
                        'command': tool.get('command', ''),
                        'commands_count': tool.get('commands', 0),
                        'type': 'tool_execution'
                    }
                })
                current_time = tool_end
        
        # Add response processing span
        processing_duration = 300  # 300ms for response processing
        processing_end = current_time + timedelta(milliseconds=processing_duration)
        spans.append({
            'span_id': f"span-processing-{flow_data['id']}",
            'name': 'response_processing',
            'start_time': current_time.isoformat(),
            'end_time': processing_end.isoformat(),
            'duration': processing_duration,
            'status': 'success',
            'metadata': {
                'type': 'response_processing',
                'output_length': len(str(flow_data.get('analysis', ''))),
                'processing_type': 'text_extraction'
            }
        })
        current_time = processing_end
        
        # Add completion span
        completion_duration = 100  # 100ms for completion
        completion_end = datetime.fromisoformat(flow_data.get('endTime', flow_data['startTime']).replace('Z', '+00:00'))
        spans.append({
            'span_id': f"span-complete-{flow_data['id']}",
            'name': 'completion',
            'start_time': current_time.isoformat(),
            'end_time': completion_end.isoformat(),
            'duration': completion_duration,
            'status': flow_data.get('status', 'completed'),
            'metadata': {
                'type': 'completion',
                'final_status': flow_data.get('status', 'completed'),
                'total_duration': flow_data.get('duration', 0)
            }
        })
        
        return spans
        """Extract span information from a Strands trace."""
        spans = []
        try:
            if hasattr(trace, 'spans'):
                for span in trace.spans:
                    span_data = {
                        'span_id': getattr(span, 'span_id', 'unknown'),
                        'name': getattr(span, 'name', 'unknown'),
                        'start_time': getattr(span, 'start_time', None),
                        'end_time': getattr(span, 'end_time', None),
                        'duration': getattr(span, 'duration', 0),
                        'status': getattr(span, 'status', 'unknown'),
                        'metadata': getattr(span, 'metadata', {})
                    }
                    spans.append(span_data)
        except Exception as e:
            logger.warning(f"Failed to extract spans from trace: {e}")
        
        return spans
    
    def add_trace_span(self, flow_id: str, span_name: str, metadata: Dict[str, Any] = None):
        """Add a span to an active flow's trace (simplified for compatibility)."""
        if flow_id in self.active_flows:
            flow_data = self.active_flows[flow_id]
            # Log the span for mock creation
            if not hasattr(flow_data, '_pending_spans'):
                flow_data['_pending_spans'] = []
            
            span_data = {
                'name': span_name,
                'start_time': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
            flow_data['_pending_spans'].append(span_data)
            logger.debug(f"Logged span '{span_name}' for flow {flow_id}")
            return span_data
        return None
    
    def end_trace_span(self, flow_id: str, span, status: str = 'success', metadata: Dict[str, Any] = None):
        """End a trace span (simplified for compatibility)."""
        if span and flow_id in self.active_flows:
            span['end_time'] = datetime.utcnow().isoformat()
            span['status'] = status
            if metadata:
                span['metadata'].update(metadata)
            logger.debug(f"Ended span for flow {flow_id}")
        return None
    
    def get_agent_flows(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get recent agent flows."""
        if limit is None:
            limit = int(os.getenv("AGENT_TELEMETRY_DEFAULT_QUERY_LIMIT", "20"))
        
        flows = list(self.agent_flows)
        
        # Add currently active flows
        active_agent_flows = [flow for flow in self.active_flows.values() 
                             if flow['type'] == 'agent_analysis']
        flows.extend(active_agent_flows)
        
        # Sort by start time (newest first) and limit
        flows.sort(key=lambda x: x['startTime'], reverse=True)
        return flows[:limit]
    
    def get_monitor_flows(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get recent monitor flows."""
        if limit is None:
            limit = int(os.getenv("AGENT_TELEMETRY_DEFAULT_QUERY_LIMIT", "20"))
        
        flows = list(self.monitor_flows)
        
        # Add currently active flows
        active_monitor_flows = [flow for flow in self.active_flows.values() 
                               if flow['type'] == 'background_monitor']
        flows.extend(active_monitor_flows)
        
        # Sort by start time (newest first) and limit
        flows.sort(key=lambda x: x['startTime'], reverse=True)
        return flows[:limit]
    
    def get_traces(self, limit: int = 50, flow_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent traces with optional filtering by flow type."""
        traces = list(self.traces)
        
        # Filter by flow type if specified
        if flow_type:
            traces = [trace for trace in traces if trace['type'] == flow_type]
        
        # Sort by start time (newest first) and limit
        traces.sort(key=lambda x: x['startTime'], reverse=True)
        return traces[:limit]
    
    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trace by its ID."""
        for trace in self.traces:
            if trace['trace_id'] == trace_id:
                return trace
        return None
    
    def get_flow_metrics(self) -> Dict[str, Any]:
        """Get aggregated flow metrics."""
        all_flows = list(self.agent_flows) + list(self.monitor_flows)
        active_count = len(self.active_flows)
        
        if not all_flows:
            return {
                'total_flows': active_count,
                'completed_flows': 0,
                'active_flows': active_count,
                'success_rate': 0.0,
                'average_duration': 0,
                'agent_flows': 0,
                'monitor_flows': 0,
                'total_traces': len(self.traces),
                'traces_enabled': self.traces_enabled
            }
        
        completed_flows = [f for f in all_flows if f['status'] in ['completed', 'error', 'timeout']]
        successful_flows = [f for f in completed_flows if f['status'] == 'completed']
        
        avg_duration = 0
        if completed_flows:
            total_duration = sum(f.get('duration', 0) for f in completed_flows if f.get('duration'))
            avg_duration = total_duration / len(completed_flows) if completed_flows else 0
        
        return {
            'total_flows': len(all_flows) + active_count,
            'completed_flows': len(completed_flows),
            'active_flows': active_count,
            'success_rate': len(successful_flows) / len(completed_flows) * 100 if completed_flows else 0,
            'average_duration': avg_duration,
            'agent_flows': len([f for f in all_flows if f['type'] == 'agent_analysis']),
            'monitor_flows': len([f for f in all_flows if f['type'] == 'background_monitor']),
            'total_traces': len(self.traces),
            'traces_enabled': self.traces_enabled
        }
    
    def add_tool_call(self, flow_id: str, tool_name: str, details: Dict[str, Any] = None):
        """Add a tool call to an active flow."""
        if flow_id in self.active_flows:
            tool_call = {
                'name': tool_name,
                'timestamp': datetime.utcnow().isoformat(),
                'duration': details.get('duration', 0) if details else 0
            }
            
            if details:
                if 'command' in details:
                    tool_call['command'] = details['command']
                elif 'commands' in details:
                    tool_call['commands'] = details['commands']
                elif 'file' in details:
                    tool_call['file'] = details['file']
            
            self.active_flows[flow_id]['tools'].append(tool_call)
    
    def update_tokens(self, flow_id: str, input_tokens: int = 0, output_tokens: int = 0):
        """Update token usage for an active flow."""
        if flow_id in self.active_flows:
            tokens = self.active_flows[flow_id]['tokens']
            tokens['input'] += input_tokens
            tokens['output'] += output_tokens
    
    def clear_old_flows(self, hours: int = 24):
        """Clear flows older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()
        
        # Clear old agent flows
        original_agent_count = len(self.agent_flows)
        self.agent_flows = deque([f for f in self.agent_flows if f['startTime'] > cutoff_iso], 
                                maxlen=self.agent_flows.maxlen)
        
        # Clear old monitor flows
        original_monitor_count = len(self.monitor_flows)
        self.monitor_flows = deque([f for f in self.monitor_flows if f['startTime'] > cutoff_iso], 
                                 maxlen=self.monitor_flows.maxlen)
        
        cleared_agent = original_agent_count - len(self.agent_flows)
        cleared_monitor = original_monitor_count - len(self.monitor_flows)
        
        if cleared_agent > 0 or cleared_monitor > 0:
            logger.info(f"Cleared {cleared_agent} old agent flows and {cleared_monitor} old monitor flows")

# Global telemetry collector instance
_telemetry_collector = None

def get_telemetry_collector() -> TelemetryCollector:
    """Get the global telemetry collector instance."""
    global _telemetry_collector
    if _telemetry_collector is None:
        _telemetry_collector = TelemetryCollector()
    return _telemetry_collector

# Convenience functions for easy integration
def start_agent_flow(flow_id: str, request: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Start tracking an agent flow."""
    return get_telemetry_collector().start_agent_flow(flow_id, request, metadata)

def end_agent_flow(flow_id: str, success: bool = True, error: str = None, 
                  tokens: Dict[str, int] = None, tools: List[Dict] = None) -> Dict[str, Any]:
    """End tracking an agent flow."""
    return get_telemetry_collector().end_agent_flow(flow_id, success, error, tokens, tools)

def start_monitor_flow(cycle: int, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Start tracking a monitor flow."""
    return get_telemetry_collector().start_monitor_flow(cycle, metadata)

def end_monitor_flow(flow_id: str, success: bool = True, error: str = None,
                    tokens: Dict[str, int] = None, tools: List[Dict] = None,
                    insights: Dict[str, int] = None) -> Dict[str, Any]:
    """End tracking a monitor flow."""
    return get_telemetry_collector().end_monitor_flow(flow_id, success, error, tokens, tools, insights)

def add_tool_call(flow_id: str, tool_name: str, details: Dict[str, Any] = None):
    """Add a tool call to an active flow."""
    get_telemetry_collector().add_tool_call(flow_id, tool_name, details)

def update_tokens(flow_id: str, input_tokens: int = 0, output_tokens: int = 0):
    """Update token usage for an active flow."""
    get_telemetry_collector().update_tokens(flow_id, input_tokens, output_tokens)
