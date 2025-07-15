"""
Kubernetes Analysis Tools

Provides fundamental tools for system interaction and cluster analysis.
These tools are used by AI agents to gather real data and perform analysis tasks.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

import aiofiles
from strands import tool

logger = logging.getLogger(__name__)

@tool
async def execute_bash_batch(commands: list, timeout: int = None) -> Dict[str, Any]:
    """
    Execute multiple bash commands efficiently in a single batch operation.
    
    Perfect for comprehensive cluster analysis - gather all data at once instead of 
    making multiple individual calls. Much faster and more efficient!
    
    Example usage:
    execute_bash_batch([
        "kubectl get nodes -o wide",
        "kubectl get pods --all-namespaces -o wide",
        "kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -20"
    ])
    
    Args:
        commands: List of commands to execute (e.g., ["kubectl get nodes", "kubectl get pods"])
        timeout: Total timeout for all commands (default: from AGENT_BATCH_COMMAND_TIMEOUT env var or 120s)
        
    Returns:
        Dictionary containing all command outputs organized by command number
    """
    if timeout is None:
        timeout = int(os.getenv("AGENT_BATCH_COMMAND_TIMEOUT", "120"))
    
    max_commands = int(os.getenv("AGENT_MAX_BATCH_COMMANDS", "10"))
    
    try:
        logger.info(f"Executing batch of {len(commands)} commands (max: {max_commands})")
        
        results = {}
        start_time = datetime.utcnow()
        
        for i, command in enumerate(commands[:max_commands]):  # Use configurable limit
            try:
                logger.info(f"Batch command {i+1}/{len(commands)}: {command}")
                
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd="/",
                    env=dict(os.environ)
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout // len(commands)  # Distribute timeout
                )
                
                stdout_text = stdout.decode('utf-8', errors='replace').strip()
                stderr_text = stderr.decode('utf-8', errors='replace').strip()
                
                results[f"command_{i+1}"] = {
                    "command": command,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "exit_code": process.returncode,
                    "success": process.returncode == 0
                }
                
                if process.returncode == 0:
                    logger.info(f"Batch command succeeded: {command}")
                else:
                    logger.warning(f"Batch command failed: {command} (exit code: {process.returncode})")
                    
            except asyncio.TimeoutError:
                logger.error(f"Batch command timed out: {command}")
                results[f"command_{i+1}"] = {
                    "command": command,
                    "error": "Command timed out",
                    "success": False
                }
            except Exception as e:
                logger.error(f"Batch command error: {command} - {e}")
                results[f"command_{i+1}"] = {
                    "command": command,
                    "error": str(e),
                    "success": False
                }
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "success": True,
            "results": results,
            "commands_executed": len(commands),
            "execution_time": f"{execution_time:.2f}s",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": f"Executed {len(commands)} commands in batch"
        }
        
    except Exception as e:
        logger.error(f"Batch execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@tool
async def execute_bash(command: str, timeout: int = None) -> Dict[str, Any]:
    """
    Execute system commands including kubectl, aws cli, and other tools asynchronously.
    
    Args:
        command: The command to execute
        timeout: Command timeout in seconds (default: from AGENT_SINGLE_COMMAND_TIMEOUT env var or 30s)
        
    Returns:
        Dictionary containing command output and metadata
    """
    if timeout is None:
        timeout = int(os.getenv("AGENT_SINGLE_COMMAND_TIMEOUT", "30"))
    
    process = None
    try:
        logger.info(f"Executing command: {command}")
        
        # Create subprocess asynchronously
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/",
            env=dict(os.environ)
        )
        
        # Wait for process completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Graceful process termination on timeout
            logger.error(f"Command timed out: {command}")
            process.kill()
            await process.wait()
            return {
                "status": "timeout",
                "error": f"Command timed out after {timeout} seconds",
                "command": command,
                "timestamp": datetime.now().isoformat()
            }
        
        # Decode output
        stdout_text = stdout.decode('utf-8') if stdout else ""
        stderr_text = stderr.decode('utf-8') if stderr else ""
        
        response = {
            "status": "success" if process.returncode == 0 else "error",
            "stdout": stdout_text,
            "stderr": stderr_text,
            "returncode": process.returncode,
            "command": command,
            "timestamp": datetime.now().isoformat()
        }
        
        log_truncate_length = int(os.getenv("AGENT_LOG_TRUNCATION_LENGTH", "50"))
        
        if process.returncode == 0:
            logger.info(f"Command succeeded: {command[:log_truncate_length]}...")
        else:
            logger.warning(f"Command failed: {command[:log_truncate_length]}... (exit code: {process.returncode})")
        
        return response
        
    except Exception as e:
        logger.error(f"Command failed: {command}, Error: {e}")
        # Ensure process cleanup on error
        if process and process.returncode is None:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
        
        return {
            "status": "error",
            "error": str(e),
            "command": command,
            "timestamp": datetime.now().isoformat()
        }

@tool
async def read_file(file_path: str) -> Dict[str, Any]:
    """
    Read content from files, configurations, logs, or manifests asynchronously.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Dictionary containing file content and metadata
    """
    try:
        logger.info(f"Reading file: {file_path}")
        
        path = Path(file_path)
        if not path.exists():
            return {
                "status": "error",
                "error": f"File not found: {file_path}",
                "file_path": file_path,
                "timestamp": datetime.now().isoformat()
            }
        
        # Use aiofiles for async file operations with proper context management
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        response = {
            "status": "success",
            "content": content,
            "file_path": file_path,
            "size": len(content),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Successfully read file: {file_path}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path,
            "timestamp": datetime.now().isoformat()
        }

@tool
async def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Write analysis results, reports, or configuration files asynchronously.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Dictionary containing operation result and metadata
    """
    try:
        logger.info(f"Writing file: {file_path}")
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use aiofiles for async file operations with proper context management
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        response = {
            "status": "success",
            "file_path": file_path,
            "size": len(content),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Successfully wrote file: {file_path}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path,
            "timestamp": datetime.now().isoformat()
        }

@tool
def report_issue(title: str, description: str) -> Dict[str, Any]:
    """
    Report critical issues or findings that need attention.
    
    Args:
        title: Issue title
        description: Detailed description of the issue
        
    Returns:
        Dictionary containing the reported issue information
    """
    try:
        logger.warning(f"Issue reported: {title}")
        
        issue_data = {
            "title": title,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "severity": "medium",
            "category": "cluster_analysis"
        }
        
        response = {
            "status": "success",
            "issue": issue_data,
            "timestamp": datetime.now().isoformat()
        }
        
        log_truncate_length = int(os.getenv("AGENT_LOG_TRUNCATION_LENGTH", "50"))
        logger.info(f"Issue details: {description[:log_truncate_length * 2]}...")  # Use 2x length for issue descriptions
        return response
        
    except Exception as e:
        logger.error(f"Failed to report issue: {e}")
        return {
            "status": "error",
            "error": str(e),
            "title": title,
            "timestamp": datetime.now().isoformat()
        }

# Async context managers for resource management
class AsyncResourceManager:
    """
    Async context manager for proper resource cleanup.
    """
    def __init__(self, resource_name: str):
        self.resource_name = resource_name
        self.resources = []
        
    async def __aenter__(self):
        logger.debug(f"Acquiring async resource: {self.resource_name}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug(f"Cleaning up async resource: {self.resource_name}")
        await self.cleanup()
        
    async def cleanup(self):
        """Clean up any managed resources."""
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
            except Exception as e:
                logger.warning(f"Error cleaning up resource: {e}")

# Utility functions for safe async operation execution
async def safe_async_operation(operation, timeout: int = 30, operation_name: str = "operation") -> Dict[str, Any]:
    """
    Execute an async operation safely with timeout and error handling.
    
    Args:
        operation: The async operation to execute
        timeout: Timeout in seconds
        operation_name: Name of the operation for logging
        
    Returns:
        Dictionary containing operation result and metadata
    """
    try:
        logger.debug(f"Starting safe async operation: {operation_name}")
        
        result = await asyncio.wait_for(operation, timeout=timeout)
        
        logger.debug(f"Safe async operation completed: {operation_name}")
        return {
            "status": "success",
            "result": result,
            "operation": operation_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except asyncio.TimeoutError:
        logger.error(f"Async operation timed out: {operation_name}")
        return {
            "status": "timeout",
            "error": f"Operation timed out after {timeout} seconds",
            "operation": operation_name,
            "timestamp": datetime.now().isoformat()
        }
    except asyncio.CancelledError:
        logger.warning(f"Async operation cancelled: {operation_name}")
        return {
            "status": "cancelled",
            "error": "Operation was cancelled",
            "operation": operation_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Async operation failed: {operation_name}, Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "operation": operation_name,
            "timestamp": datetime.now().isoformat()
        }

async def execute_with_retry(operation_func, max_retries: int = None, delay: float = None, operation_name: str = "operation", *args, **kwargs) -> Dict[str, Any]:
    """
    Execute an async operation with retry logic and exponential backoff.
    
    Args:
        operation_func: The async function to execute (not a coroutine)
        max_retries: Maximum number of retry attempts (default: from AGENT_MAX_RETRIES env var or 3)
        delay: Initial delay between retries in seconds (default: from AGENT_RETRY_DELAY env var or 1.0)
        operation_name: Name of the operation for logging
        *args, **kwargs: Arguments to pass to the operation function
        
    Returns:
        Dictionary containing operation result and metadata
    """
    if max_retries is None:
        max_retries = int(os.getenv("AGENT_MAX_RETRIES", "3"))
    if delay is None:
        delay = float(os.getenv("AGENT_RETRY_DELAY", "1.0"))
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.info(f"Retrying {operation_name} (attempt {attempt + 1}/{max_retries + 1}) after {wait_time}s")
                await asyncio.sleep(wait_time)
            
            # Create a new coroutine for each attempt
            result = await operation_func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(f"Operation succeeded on retry: {operation_name}")
            
            return {
                "status": "success",
                "result": result,
                "operation": operation_name,
                "attempts": attempt + 1,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            last_error = e
            logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {operation_name}, Error: {e}")
            
            if attempt == max_retries:
                break
    
    logger.error(f"Operation failed after {max_retries + 1} attempts: {operation_name}")
    return {
        "status": "error",
        "error": str(last_error),
        "operation": operation_name,
        "attempts": max_retries + 1,
        "timestamp": datetime.now().isoformat()
    }

# Async helper functions for direct use
async def read_file_async(file_path: str) -> Dict[str, Any]:
    """
    Direct async file reading function for internal use.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Dictionary containing file content and metadata
    """
    return await read_file(file_path)

async def write_file_async(file_path: str, content: str) -> Dict[str, Any]:
    """
    Direct async file writing function for internal use.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Dictionary containing operation result and metadata
    """
    return await write_file(file_path, content)

# Legacy aliases for backward compatibility
fs_read = read_file
fs_write = write_file
