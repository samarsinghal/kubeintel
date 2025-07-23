"""
Event Processor for AWS Strands Kubernetes Monitoring

Handles intelligent processing and analysis of monitoring events.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from strands import Agent

logger = logging.getLogger(__name__)

@dataclass
class ProcessedEvent:
    """Represents a processed monitoring event with analysis."""
    original_event_id: str
    analysis_id: str
    timestamp: datetime
    severity: str
    summary: str
    recommendations: List[str]
    impact_assessment: str
    priority: int  # 1-5, 5 being highest
    requires_action: bool
    metadata: Dict[str, Any]

class EventProcessor:
    """
    Intelligent event processor using AWS Strands for analysis.
    
    This class provides:
    - Event correlation and deduplication
    - Intelligent severity assessment
    - Automated recommendation generation
    - Impact analysis
    - Priority scoring
    """
    
    def __init__(self, strands_agent: Agent):
        """
        Initialize the event processor.
        
        Args:
            strands_agent: The AWS Strands agent for analysis
        """
        self.strands_agent = strands_agent
        self.processed_events = {}  # Cache of processed events
        self.event_patterns = {}    # Pattern recognition cache
        self.correlation_window = timedelta(minutes=5)  # Time window for event correlation
        
        logger.info("Event Processor initialized")
    
    async def process_events(self, events: List[Any]) -> List[ProcessedEvent]:
        """
        Process a batch of monitoring events with intelligent analysis.
        
        Args:
            events: List of monitoring events to process
            
        Returns:
            List of processed events with analysis
        """
        if not events:
            return []
        
        try:
            # Step 1: Correlate and deduplicate events
            correlated_events = await self._correlate_events(events)
            
            # Step 2: Analyze each correlated event group
            processed_events = []
            for event_group in correlated_events:
                processed_event = await self._analyze_event_group(event_group)
                if processed_event:
                    processed_events.append(processed_event)
            
            # Step 3: Sort by priority
            processed_events.sort(key=lambda x: x.priority, reverse=True)
            
            # Step 4: Update cache
            for event in processed_events:
                self.processed_events[event.analysis_id] = event
            
            logger.info(f"Processed {len(events)} events into {len(processed_events)} analyzed events")
            return processed_events
            
        except Exception as e:
            logger.error(f"Error processing events: {e}")
            return []
    
    async def _correlate_events(self, events: List[Any]) -> List[List[Any]]:
        """
        Correlate related events and group them for analysis.
        
        Args:
            events: Raw monitoring events
            
        Returns:
            List of event groups (correlated events)
        """
        # Group events by resource and time proximity
        event_groups = {}
        
        for event in events:
            # Create correlation key based on resource and namespace
            correlation_key = f"{event.namespace or 'cluster'}:{event.resource_type}:{event.resource_name}"
            
            if correlation_key not in event_groups:
                event_groups[correlation_key] = []
            
            event_groups[correlation_key].append(event)
        
        # Further correlate events within time windows
        correlated_groups = []
        for group_key, group_events in event_groups.items():
            # Sort events by timestamp
            group_events.sort(key=lambda x: x.timestamp)
            
            # Split into time-based sub-groups
            current_group = []
            last_timestamp = None
            
            for event in group_events:
                if (last_timestamp is None or 
                    event.timestamp - last_timestamp <= self.correlation_window):
                    current_group.append(event)
                else:
                    if current_group:
                        correlated_groups.append(current_group)
                    current_group = [event]
                
                last_timestamp = event.timestamp
            
            if current_group:
                correlated_groups.append(current_group)
        
        return correlated_groups
    
    async def _analyze_event_group(self, event_group: List[Any]) -> Optional[ProcessedEvent]:
        """
        Analyze a group of correlated events using AWS Strands.
        
        Args:
            event_group: List of correlated events
            
        Returns:
            ProcessedEvent with analysis results
        """
        if not event_group:
            return None
        
        try:
            # Create analysis prompt
            prompt = self._create_event_analysis_prompt(event_group)
            
            # Use Strands agent for intelligent analysis
            analysis_result = await self.strands_agent.run_async(prompt)
            
            # Parse and structure the analysis
            processed_event = await self._parse_analysis_result(
                event_group, analysis_result
            )
            
            return processed_event
            
        except Exception as e:
            logger.error(f"Error analyzing event group: {e}")
            return self._create_fallback_processed_event(event_group)
    
    def _create_event_analysis_prompt(self, event_group: List[Any]) -> str:
        """Create an analysis prompt for a group of events."""
        primary_event = event_group[0]
        
        prompt_parts = [
            "Analyze the following Kubernetes monitoring events and provide structured insights:",
            "",
            f"Resource: {primary_event.resource_type}/{primary_event.resource_name}",
            f"Namespace: {primary_event.namespace or 'cluster-wide'}",
            f"Event Count: {len(event_group)}",
            f"Time Span: {event_group[0].timestamp} to {event_group[-1].timestamp}",
            "",
            "Events:"
        ]
        
        for i, event in enumerate(event_group, 1):
            prompt_parts.extend([
                f"{i}. [{event.severity.upper()}] {event.event_type}",
                f"   Time: {event.timestamp}",
                f"   Message: {event.message}",
                ""
            ])
        
        prompt_parts.extend([
            "Please provide a JSON response with the following structure:",
            "{",
            '  "summary": "Brief summary of the issue",',
            '  "severity": "critical|high|medium|low",',
            '  "priority": 1-5,',
            '  "impact_assessment": "Description of potential impact",',
            '  "recommendations": ["action1", "action2", ...],',
            '  "requires_immediate_action": true/false,',
            '  "root_cause": "Likely root cause",',
            '  "related_components": ["component1", "component2", ...]',
            "}",
            "",
            "Focus on actionable insights and practical recommendations."
        ])
        
        return "\n".join(prompt_parts)
    
    async def _parse_analysis_result(self, event_group: List[Any], analysis_result: str) -> ProcessedEvent:
        """Parse the Strands analysis result into a ProcessedEvent."""
        try:
            # Try to parse JSON response
            if "{" in analysis_result and "}" in analysis_result:
                json_start = analysis_result.find("{")
                json_end = analysis_result.rfind("}") + 1
                json_str = analysis_result[json_start:json_end]
                analysis_data = json.loads(json_str)
            else:
                # Fallback to text parsing
                analysis_data = self._parse_text_analysis(analysis_result)
            
            # Map severity to priority
            severity_priority_map = {
                "critical": 5,
                "high": 4,
                "medium": 3,
                "low": 2,
                "info": 1
            }
            
            primary_event = event_group[0]
            analysis_id = f"analysis-{primary_event.event_id}-{datetime.utcnow().isoformat()}"
            
            return ProcessedEvent(
                original_event_id=primary_event.event_id,
                analysis_id=analysis_id,
                timestamp=datetime.utcnow(),
                severity=analysis_data.get("severity", "medium"),
                summary=analysis_data.get("summary", "Event analysis completed"),
                recommendations=analysis_data.get("recommendations", []),
                impact_assessment=analysis_data.get("impact_assessment", "Impact assessment pending"),
                priority=analysis_data.get("priority", severity_priority_map.get(analysis_data.get("severity", "medium"), 3)),
                requires_action=analysis_data.get("requires_immediate_action", False),
                metadata={
                    "event_count": len(event_group),
                    "resource_type": primary_event.resource_type,
                    "resource_name": primary_event.resource_name,
                    "namespace": primary_event.namespace,
                    "root_cause": analysis_data.get("root_cause"),
                    "related_components": analysis_data.get("related_components", []),
                    "original_events": [event.event_id for event in event_group]
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing analysis result: {e}")
            return self._create_fallback_processed_event(event_group)
    
    def _parse_text_analysis(self, text: str) -> Dict[str, Any]:
        """Parse text-based analysis when JSON parsing fails."""
        # Simple text parsing fallback
        lines = text.lower().split('\n')
        
        severity = "medium"
        priority = 3
        requires_action = False
        
        # Look for severity indicators
        if any(word in text.lower() for word in ["critical", "urgent", "emergency"]):
            severity = "critical"
            priority = 5
            requires_action = True
        elif any(word in text.lower() for word in ["high", "important", "serious"]):
            severity = "high"
            priority = 4
            requires_action = True
        elif any(word in text.lower() for word in ["warning", "caution"]):
            severity = "medium"
            priority = 3
        
        # Extract recommendations (lines starting with action words)
        recommendations = []
        action_words = ["recommend", "suggest", "should", "need to", "must", "fix", "resolve"]
        
        for line in lines:
            if any(word in line for word in action_words):
                recommendations.append(line.strip())
        
        return {
            "summary": text[:200] + "..." if len(text) > 200 else text,
            "severity": severity,
            "priority": priority,
            "impact_assessment": "Automated assessment based on event analysis",
            "recommendations": recommendations[:5],  # Limit to 5 recommendations
            "requires_immediate_action": requires_action
        }
    
    def _create_fallback_processed_event(self, event_group: List[Any]) -> ProcessedEvent:
        """Create a fallback processed event when analysis fails."""
        primary_event = event_group[0]
        
        # Determine severity based on event types
        max_severity = "info"
        for event in event_group:
            if event.severity == "error":
                max_severity = "high"
                break
            elif event.severity == "warning" and max_severity != "error":
                max_severity = "medium"
        
        severity_priority_map = {"high": 4, "medium": 3, "info": 1}
        
        return ProcessedEvent(
            original_event_id=primary_event.event_id,
            analysis_id=f"fallback-{primary_event.event_id}-{datetime.utcnow().isoformat()}",
            timestamp=datetime.utcnow(),
            severity=max_severity,
            summary=f"Multiple events detected for {primary_event.resource_type}/{primary_event.resource_name}",
            recommendations=[
                f"Investigate {primary_event.resource_type} {primary_event.resource_name}",
                "Check resource logs for detailed information",
                "Verify resource configuration and status"
            ],
            impact_assessment=f"Potential impact on {primary_event.resource_type} availability",
            priority=severity_priority_map.get(max_severity, 2),
            requires_action=max_severity in ["high", "critical"],
            metadata={
                "event_count": len(event_group),
                "resource_type": primary_event.resource_type,
                "resource_name": primary_event.resource_name,
                "namespace": primary_event.namespace,
                "analysis_method": "fallback",
                "original_events": [event.event_id for event in event_group]
            }
        )
    
    def get_recent_analyses(self, hours: int = 24) -> List[ProcessedEvent]:
        """Get recent processed events within the specified time window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            event for event in self.processed_events.values()
            if event.timestamp >= cutoff_time
        ]
    
    def get_high_priority_events(self, min_priority: int = 4) -> List[ProcessedEvent]:
        """Get high priority events that require attention."""
        return [
            event for event in self.processed_events.values()
            if event.priority >= min_priority
        ]
    
    def clear_old_events(self, hours: int = 168):  # Default: 1 week
        """Clear old processed events from cache."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        old_event_ids = [
            event_id for event_id, event in self.processed_events.items()
            if event.timestamp < cutoff_time
        ]
        
        for event_id in old_event_ids:
            del self.processed_events[event_id]
        
        logger.info(f"Cleared {len(old_event_ids)} old processed events")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        if not self.processed_events:
            return {"total_events": 0}
        
        events = list(self.processed_events.values())
        
        severity_counts = {}
        priority_counts = {}
        
        for event in events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
            priority_counts[event.priority] = priority_counts.get(event.priority, 0) + 1
        
        return {
            "total_events": len(events),
            "severity_distribution": severity_counts,
            "priority_distribution": priority_counts,
            "high_priority_count": len([e for e in events if e.priority >= 4]),
            "requires_action_count": len([e for e in events if e.requires_action]),
            "latest_event": max(events, key=lambda x: x.timestamp).timestamp.isoformat() if events else None
        }
