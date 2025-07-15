"""
KubeIntel Cost Visualizer
Comprehensive cost tracking and visualization for AI model usage
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class ModelPricing:
    """Model pricing configuration"""
    input_cost_per_1m: float  # Cost per 1M input tokens
    output_cost_per_1m: float  # Cost per 1M output tokens
    context_window: int  # Maximum context window size

# AWS Bedrock Claude 3.5 Haiku pricing (as of 2024)
CLAUDE_35_HAIKU_PRICING = ModelPricing(
    input_cost_per_1m=0.25,  # $0.25 per 1M input tokens
    output_cost_per_1m=1.25,  # $1.25 per 1M output tokens
    context_window=200000  # 200k token context window
)

class CostVisualizer:
    """
    Comprehensive cost visualization and tracking system
    """
    
    def __init__(self):
        """Initialize cost visualizer"""
        self.pricing = CLAUDE_35_HAIKU_PRICING
        logger.info("Cost visualizer initialized with Claude 3.5 Haiku pricing")
    
    async def get_session_costs(self) -> Dict[str, Any]:
        """Get comprehensive session cost analysis"""
        try:
            # Get session files and analyze costs
            session_analysis = await self._analyze_session_files()
            
            # Get telemetry data
            from telemetry_api import get_telemetry_collector
            telemetry = get_telemetry_collector()
            
            # Analyze flows
            agent_flows = telemetry.get_agent_flows()
            monitor_flows = telemetry.get_monitor_flows()
            
            # Handle the case where telemetry returns lists directly
            if isinstance(agent_flows, dict) and 'flows' in agent_flows:
                agent_flow_list = agent_flows['flows']
            else:
                agent_flow_list = agent_flows if isinstance(agent_flows, list) else []
                
            if isinstance(monitor_flows, dict) and 'flows' in monitor_flows:
                monitor_flow_list = monitor_flows['flows']
            else:
                monitor_flow_list = monitor_flows if isinstance(monitor_flows, list) else []
            
            # Calculate costs
            cost_breakdown = self._calculate_cost_breakdown(
                session_analysis, agent_flow_list, monitor_flow_list
            )
            
            # Generate projections
            projections = self._calculate_projections(cost_breakdown)
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "model_info": {
                    "model": "anthropic.claude-3-5-haiku-20241022-v1:0",
                    "pricing": {
                        "input_cost_per_1m_tokens": self.pricing.input_cost_per_1m,
                        "output_cost_per_1m_tokens": self.pricing.output_cost_per_1m,
                        "context_window": self.pricing.context_window
                    }
                },
                "session_analysis": session_analysis,
                "cost_breakdown": cost_breakdown,
                "projections": projections,
                "optimization_recommendations": self._get_optimization_recommendations(cost_breakdown)
            }
            
        except Exception as e:
            logger.error(f"Error getting session costs: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def _analyze_session_files(self) -> Dict[str, Any]:
        """Analyze session files to understand token usage"""
        try:
            # This would need to be run inside the pod to access session files
            # For now, return estimated analysis based on telemetry
            return {
                "active_sessions": 1,
                "estimated_context_size": 30000,  # Based on 20 messages observed
                "message_count": 20,
                "session_age_hours": 0.5,
                "estimated_tokens_per_message": 1500
            }
        except Exception as e:
            logger.warning(f"Could not analyze session files: {e}")
            return {"error": "Session file analysis not available"}
    
    def _calculate_cost_breakdown(self, session_analysis: Dict, agent_flows: List, monitor_flows: List) -> Dict[str, Any]:
        """Calculate detailed cost breakdown"""
        
        # Calculate agent analysis costs
        agent_costs = self._calculate_flow_costs(agent_flows, "agent")
        
        # Calculate monitor costs  
        monitor_costs = self._calculate_flow_costs(monitor_flows, "monitor")
        
        # Session context costs (estimated)
        context_size = session_analysis.get('estimated_context_size', 30000)
        context_cost = self._calculate_token_cost(context_size, 0, "context")
        
        # Total costs
        total_input_tokens = agent_costs['total_input_tokens'] + monitor_costs['total_input_tokens']
        total_output_tokens = agent_costs['total_output_tokens'] + monitor_costs['total_output_tokens']
        total_cost = agent_costs['total_cost'] + monitor_costs['total_cost']
        
        return {
            "agent_analysis": agent_costs,
            "background_monitoring": monitor_costs,
            "session_context": {
                "estimated_context_size": context_size,
                "context_cost_per_call": context_cost['input_cost'],
                "message_count": session_analysis.get('message_count', 0)
            },
            "totals": {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "total_cost": total_cost,
                "average_cost_per_request": total_cost / max(len(agent_flows) + len(monitor_flows), 1)
            }
        }
    
    def _calculate_flow_costs(self, flows: List[Dict], flow_type: str) -> Dict[str, Any]:
        """Calculate costs for a list of flows"""
        if not flows:
            return {
                "flow_count": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "average_cost_per_flow": 0.0,
                "flows": []
            }
        
        flow_costs = []
        total_input = 0
        total_output = 0
        total_cost = 0.0
        
        for flow in flows:
            # Estimate tokens based on flow duration and type
            if flow_type == "agent":
                # Agent flows: larger context, more complex
                estimated_input = 50000  # Estimated based on session context + request
                estimated_output = 2000   # Estimated response size
            else:
                # Monitor flows: structured, predictable
                estimated_input = 30000   # Estimated based on session context + monitoring prompt
                estimated_output = 1500   # Estimated structured response
            
            # Use actual tokens if available, otherwise use estimates
            input_tokens = flow.get('tokens', {}).get('input', estimated_input)
            output_tokens = flow.get('tokens', {}).get('output', estimated_output)
            
            # Calculate cost for this flow
            cost_info = self._calculate_token_cost(input_tokens, output_tokens, flow.get('id', 'unknown'))
            
            flow_cost = {
                "id": flow.get('id'),
                "duration_seconds": flow.get('duration', 0) / 1000 if flow.get('duration') else 0,
                "status": flow.get('status'),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost_info['total_cost'],
                "input_cost": cost_info['input_cost'],
                "output_cost": cost_info['output_cost']
            }
            
            flow_costs.append(flow_cost)
            total_input += input_tokens
            total_output += output_tokens
            total_cost += cost_info['total_cost']
        
        return {
            "flow_count": len(flows),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost": total_cost,
            "average_cost_per_flow": total_cost / len(flows),
            "flows": flow_costs[-10:]  # Last 10 flows for detail
        }
    
    def _calculate_token_cost(self, input_tokens: int, output_tokens: int, flow_id: str) -> Dict[str, Any]:
        """Calculate cost for given token usage"""
        input_cost = (input_tokens / 1_000_000) * self.pricing.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.pricing.output_cost_per_1m
        total_cost = input_cost + output_cost
        
        return {
            "flow_id": flow_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def _calculate_projections(self, cost_breakdown: Dict) -> Dict[str, Any]:
        """Calculate cost projections"""
        
        # Current totals
        current_cost = cost_breakdown['totals']['total_cost']
        avg_cost_per_request = cost_breakdown['totals']['average_cost_per_request']
        
        # Background monitoring projections (every 5 minutes)
        monitor_cost_per_cycle = cost_breakdown['background_monitoring']['average_cost_per_flow']
        cycles_per_hour = 12  # Every 5 minutes
        cycles_per_day = 288  # 24 * 12
        
        # Agent analysis projections (estimated usage)
        agent_cost_per_analysis = cost_breakdown['agent_analysis']['average_cost_per_flow']
        estimated_analyses_per_day = 10  # Conservative estimate
        
        # Session rotation impact
        session_rotations_per_day = 1.4  # Every 200 cycles at 5-min intervals
        
        return {
            "hourly": {
                "background_monitoring": monitor_cost_per_cycle * cycles_per_hour,
                "agent_analysis": agent_cost_per_analysis * (estimated_analyses_per_day / 24),
                "total_estimated": (monitor_cost_per_cycle * cycles_per_hour) + (agent_cost_per_analysis * (estimated_analyses_per_day / 24))
            },
            "daily": {
                "background_monitoring": monitor_cost_per_cycle * cycles_per_day,
                "agent_analysis": agent_cost_per_analysis * estimated_analyses_per_day,
                "session_rotations": session_rotations_per_day,
                "total_estimated": (monitor_cost_per_cycle * cycles_per_day) + (agent_cost_per_analysis * estimated_analyses_per_day)
            },
            "monthly": {
                "background_monitoring": monitor_cost_per_cycle * cycles_per_day * 30,
                "agent_analysis": agent_cost_per_analysis * estimated_analyses_per_day * 30,
                "total_estimated": ((monitor_cost_per_cycle * cycles_per_day) + (agent_cost_per_analysis * estimated_analyses_per_day)) * 30
            },
            "session_rotation_savings": {
                "cost_without_rotation": self._calculate_no_rotation_cost(),
                "cost_with_rotation": cost_breakdown['totals']['total_cost'],
                "savings_percentage": self._calculate_rotation_savings_percentage()
            }
        }
    
    def _calculate_no_rotation_cost(self) -> float:
        """Calculate what costs would be without session rotation"""
        # Without rotation, context would grow to ~300k tokens by cycle 200
        max_context = 300000
        cost_per_call_max = (max_context / 1_000_000) * self.pricing.input_cost_per_1m
        return cost_per_call_max * 200  # 200 cycles before rotation
    
    def _calculate_rotation_savings_percentage(self) -> float:
        """Calculate percentage savings from session rotation"""
        cost_without_rotation = self._calculate_no_rotation_cost()
        cost_with_rotation = 50.0  # Estimated current cost with rotation
        if cost_without_rotation > 0:
            return ((cost_without_rotation - cost_with_rotation) / cost_without_rotation) * 100
        return 0.0
    
    def _get_optimization_recommendations(self, cost_breakdown: Dict) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        total_cost = cost_breakdown['totals']['total_cost']
        avg_cost = cost_breakdown['totals']['average_cost_per_request']
        
        # High cost warning
        if avg_cost > 0.05:
            recommendations.append({
                "type": "warning",
                "title": "High Average Cost Per Request",
                "description": f"Average cost of ${avg_cost:.4f} per request is above optimal range",
                "suggestion": "Consider more frequent session rotation or prompt optimization",
                "impact": "high"
            })
        
        # Session rotation optimization
        recommendations.append({
            "type": "optimization",
            "title": "Session Rotation Efficiency",
            "description": "Current 200-cycle rotation provides good cost control",
            "suggestion": "Monitor for performance degradation to optimize rotation frequency",
            "impact": "medium"
        })
        
        # Token usage optimization
        recommendations.append({
            "type": "optimization", 
            "title": "Token Usage Optimization",
            "description": "Batch operations and structured prompts help minimize token usage",
            "suggestion": "Continue using execute_bash_batch for multiple commands",
            "impact": "medium"
        })
        
        # Cost monitoring
        recommendations.append({
            "type": "monitoring",
            "title": "Cost Monitoring",
            "description": "Regular cost tracking helps identify usage patterns",
            "suggestion": "Review cost visualizer daily to track trends",
            "impact": "low"
        })
        
        return recommendations

# Global cost visualizer instance
_cost_visualizer = None

def get_cost_visualizer() -> CostVisualizer:
    """Get the global cost visualizer instance"""
    global _cost_visualizer
    if _cost_visualizer is None:
        _cost_visualizer = CostVisualizer()
    return _cost_visualizer
