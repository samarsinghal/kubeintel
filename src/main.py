"""
Main entry point for KubeIntel - AI-Powered Kubernetes Intelligence Platform.

This module starts the FastAPI application using the AWS Strands framework
with full event loop and streaming capabilities.
"""

import logging
import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strands_api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    
    # Use AGENT_PORT if available, otherwise fall back to PORT, then default to 8000
    port = int(os.environ.get("AGENT_PORT", os.environ.get("PORT", 8000)))
    
    logger.info("🚀 Starting KubeIntel - AI-Powered Kubernetes Intelligence Platform")
    logger.info(f"📡 Framework: AWS Strands v1.0.x")
    logger.info(f"🔄 Event Loop: Enabled")
    logger.info(f"📊 Streaming: Enabled")
    logger.info(f"🌐 Port: {port}")
    
    uvicorn.run(
        "src.strands_api:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        reload=False,
        loop="asyncio"
    )
