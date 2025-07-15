#!/usr/bin/env python3
"""
KubeIntel Application Entry Point

Main entry point for the KubeIntel Kubernetes analysis platform.
Starts the FastAPI server with AI-powered cluster analysis capabilities.
"""

import asyncio
import logging
import sys
import os

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """Main application entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting KubeIntel application")
    
    try:
        import uvicorn
        
        # Import the app directly
        import importlib.util
        api_path = os.path.join(current_dir, 'api.py')
        spec = importlib.util.spec_from_file_location("api", api_path)
        api_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api_module)
        
        # Get configurable host and port settings
        host = os.getenv("AGENT_HOST", "0.0.0.0")
        port = int(os.getenv("AGENT_PORT", "8000"))
        log_level = os.getenv("AGENT_LOG_LEVEL", "info").lower()
        
        # Start the FastAPI server
        uvicorn.run(
            api_module.app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
