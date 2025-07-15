"""
Model Manager for KubeIntel
Provides Strands agent creation and management
"""

import os
import logging
from typing import Optional
from strands import Agent
import tools as tools_module

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages Strands agents and model configuration."""
    
    def __init__(self):
        """Initialize the model manager."""
        self.region = os.getenv("AGENT_STRANDS_REGION", "us-east-1")
        self.model_id = os.getenv("AGENT_STRANDS_MODEL", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
        
        logger.info(f"ModelManager initialized with model: {self.model_id}")
    
    async def create_agent(self, name: str, system_prompt: str, session_manager=None, tools=None) -> Agent:
        """Create a Strands agent with the specified configuration."""
        # Use provided tools or default tools
        if tools is not None:
            agent_tools = tools
        else:
            # Default tools if none provided
            agent_tools = [
                tools_module.execute_bash,
                tools_module.fs_read,
                tools_module.fs_write,
                tools_module.report_issue
            ]
        
        # Create agent with tools
        agent = Agent(
            name=name,
            model=self.model_id,
            system_prompt=system_prompt,
            tools=agent_tools,
            session_manager=session_manager
        )
        
        logger.info(f"Created Strands agent '{name}' with model {self.model_id}")
        return agent

    def get_current_model(self) -> str:
        """Get the currently active model ID."""
        return self.model_id
    
    def get_model_status(self) -> dict:
        """Get the current model status."""
        return {
            "current_model": self.model_id,
            "region": self.region,
            "status": "available"
        }

# Global model manager instance
_model_manager = None

def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
