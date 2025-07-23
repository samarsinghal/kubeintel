"""
Monitoring Scheduler for AWS Strands Kubernetes Event Loop

Handles intelligent scheduling and timing of monitoring activities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ScheduleType(Enum):
    """Types of monitoring schedules."""
    FIXED_INTERVAL = "fixed_interval"
    ADAPTIVE = "adaptive"
    EVENT_DRIVEN = "event_driven"
    CRON_LIKE = "cron_like"

@dataclass
class ScheduledTask:
    """Represents a scheduled monitoring task."""
    task_id: str
    name: str
    schedule_type: ScheduleType
    interval_seconds: int
    callback: Callable
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    priority: int = 1  # 1-5, 5 being highest
    metadata: Dict[str, Any] = None

class MonitoringScheduler:
    """
    Intelligent scheduler for monitoring tasks.
    
    Features:
    - Adaptive scheduling based on cluster activity
    - Priority-based task execution
    - Load balancing and resource management
    - Event-driven scheduling triggers
    """
    
    def __init__(self, base_interval: int = 30):
        """
        Initialize the monitoring scheduler.
        
        Args:
            base_interval: Base monitoring interval in seconds
        """
        self.base_interval = base_interval
        self.tasks = {}
        self.is_running = False
        self.scheduler_task = None
        
        # Adaptive scheduling parameters
        self.cluster_activity_level = "normal"  # low, normal, high, critical
        self.load_factor = 1.0
        self.max_concurrent_tasks = 5
        self.running_tasks = set()
        
        # Performance tracking
        self.metrics = {
            "tasks_executed": 0,
            "tasks_failed": 0,
            "average_execution_time": 0,
            "last_cycle_duration": 0,
            "adaptive_adjustments": 0
        }
        
        logger.info(f"Monitoring Scheduler initialized with base interval: {base_interval}s")
    
    def add_task(
        self,
        task_id: str,
        name: str,
        callback: Callable,
        interval_seconds: int,
        schedule_type: ScheduleType = ScheduleType.FIXED_INTERVAL,
        priority: int = 1,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Add a scheduled monitoring task.
        
        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            callback: Async function to execute
            interval_seconds: Execution interval in seconds
            schedule_type: Type of scheduling to use
            priority: Task priority (1-5)
            metadata: Additional task metadata
        """
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            callback=callback,
            priority=priority,
            metadata=metadata or {}
        )
        
        # Calculate initial next run time
        task.next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)
        
        self.tasks[task_id] = task
        logger.info(f"Added scheduled task: {name} (interval: {interval_seconds}s, priority: {priority})")
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.
        
        Args:
            task_id: Task identifier to remove
            
        Returns:
            True if task was removed, False if not found
        """
        if task_id in self.tasks:
            task = self.tasks.pop(task_id)
            logger.info(f"Removed scheduled task: {task.name}")
            return True
        return False
    
    def enable_task(self, task_id: str) -> bool:
        """Enable a scheduled task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            logger.info(f"Enabled task: {task_id}")
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Disable a scheduled task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            logger.info(f"Disabled task: {task_id}")
            return True
        return False
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        logger.info("Starting monitoring scheduler")
        
        # Start the main scheduler loop
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        try:
            await self.scheduler_task
        except asyncio.CancelledError:
            logger.info("Scheduler task cancelled")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        logger.info("Stopping monitoring scheduler")
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel any running tasks
        for task_id in list(self.running_tasks):
            logger.info(f"Cancelling running task: {task_id}")
        
        logger.info("Scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                cycle_start = datetime.utcnow()
                
                # Get tasks ready to run
                ready_tasks = self._get_ready_tasks()
                
                if ready_tasks:
                    # Sort by priority and execute
                    ready_tasks.sort(key=lambda t: t.priority, reverse=True)
                    await self._execute_tasks(ready_tasks)
                
                # Adaptive scheduling adjustments
                await self._adjust_scheduling()
                
                # Update metrics
                cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
                self.metrics["last_cycle_duration"] = cycle_duration
                
                # Sleep until next check (minimum 1 second)
                sleep_time = max(1, min(task.interval_seconds for task in self.tasks.values()) // 10)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    def _get_ready_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are ready to run."""
        now = datetime.utcnow()
        ready_tasks = []
        
        for task in self.tasks.values():
            if (task.enabled and 
                task.next_run and 
                now >= task.next_run and
                task.task_id not in self.running_tasks):
                ready_tasks.append(task)
        
        return ready_tasks
    
    async def _execute_tasks(self, tasks: List[ScheduledTask]) -> None:
        """Execute a list of tasks with concurrency control."""
        # Limit concurrent tasks
        available_slots = self.max_concurrent_tasks - len(self.running_tasks)
        tasks_to_run = tasks[:available_slots]
        
        if not tasks_to_run:
            return
        
        # Create task coroutines
        task_coroutines = []
        for task in tasks_to_run:
            self.running_tasks.add(task.task_id)
            task_coroutines.append(self._execute_single_task(task))
        
        # Execute tasks concurrently
        if task_coroutines:
            await asyncio.gather(*task_coroutines, return_exceptions=True)
    
    async def _execute_single_task(self, task: ScheduledTask) -> None:
        """Execute a single scheduled task."""
        execution_start = datetime.utcnow()
        
        try:
            logger.debug(f"Executing task: {task.name}")
            
            # Execute the task callback
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback()
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, task.callback)
            
            # Update task timing
            task.last_run = execution_start
            task.next_run = self._calculate_next_run(task)
            
            # Update metrics
            execution_time = (datetime.utcnow() - execution_start).total_seconds()
            self._update_execution_metrics(execution_time, success=True)
            
            logger.debug(f"Task completed: {task.name} (took {execution_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.name} - {e}")
            
            # Update task timing even on failure
            task.last_run = execution_start
            task.next_run = self._calculate_next_run(task, failed=True)
            
            # Update metrics
            execution_time = (datetime.utcnow() - execution_start).total_seconds()
            self._update_execution_metrics(execution_time, success=False)
            
        finally:
            # Remove from running tasks
            self.running_tasks.discard(task.task_id)
    
    def _calculate_next_run(self, task: ScheduledTask, failed: bool = False) -> datetime:
        """Calculate the next run time for a task."""
        now = datetime.utcnow()
        
        if task.schedule_type == ScheduleType.FIXED_INTERVAL:
            # Fixed interval scheduling
            interval = task.interval_seconds
            if failed:
                # Shorter retry interval on failure
                interval = min(interval, 60)
            
            return now + timedelta(seconds=interval)
        
        elif task.schedule_type == ScheduleType.ADAPTIVE:
            # Adaptive scheduling based on cluster activity
            base_interval = task.interval_seconds
            adjusted_interval = base_interval * self.load_factor
            
            # Adjust based on cluster activity
            if self.cluster_activity_level == "critical":
                adjusted_interval *= 0.5  # More frequent monitoring
            elif self.cluster_activity_level == "high":
                adjusted_interval *= 0.7
            elif self.cluster_activity_level == "low":
                adjusted_interval *= 1.5  # Less frequent monitoring
            
            if failed:
                adjusted_interval = min(adjusted_interval, 60)
            
            return now + timedelta(seconds=int(adjusted_interval))
        
        elif task.schedule_type == ScheduleType.EVENT_DRIVEN:
            # Event-driven tasks run immediately when triggered
            # For now, use a short interval as fallback
            return now + timedelta(seconds=10)
        
        else:
            # Default to fixed interval
            return now + timedelta(seconds=task.interval_seconds)
    
    async def _adjust_scheduling(self) -> None:
        """Adjust scheduling parameters based on system performance."""
        try:
            # Simple adaptive logic based on execution metrics
            avg_execution_time = self.metrics.get("average_execution_time", 0)
            
            # Adjust load factor based on performance
            if avg_execution_time > 10:  # Tasks taking too long
                self.load_factor = min(2.0, self.load_factor * 1.1)
                self.metrics["adaptive_adjustments"] += 1
                logger.debug(f"Increased load factor to {self.load_factor:.2f}")
            elif avg_execution_time < 2:  # Tasks completing quickly
                self.load_factor = max(0.5, self.load_factor * 0.95)
                self.metrics["adaptive_adjustments"] += 1
                logger.debug(f"Decreased load factor to {self.load_factor:.2f}")
            
            # Adjust max concurrent tasks based on system load
            if len(self.running_tasks) >= self.max_concurrent_tasks * 0.8:
                # High concurrency, might need to reduce
                if avg_execution_time > 5:
                    self.max_concurrent_tasks = max(2, self.max_concurrent_tasks - 1)
                    logger.debug(f"Reduced max concurrent tasks to {self.max_concurrent_tasks}")
            
        except Exception as e:
            logger.error(f"Error adjusting scheduling: {e}")
    
    def _update_execution_metrics(self, execution_time: float, success: bool) -> None:
        """Update execution metrics."""
        if success:
            self.metrics["tasks_executed"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        # Update average execution time (simple moving average)
        current_avg = self.metrics["average_execution_time"]
        total_tasks = self.metrics["tasks_executed"] + self.metrics["tasks_failed"]
        
        if total_tasks > 0:
            self.metrics["average_execution_time"] = (
                (current_avg * (total_tasks - 1) + execution_time) / total_tasks
            )
    
    def set_cluster_activity_level(self, level: str) -> None:
        """
        Set the cluster activity level for adaptive scheduling.
        
        Args:
            level: Activity level ("low", "normal", "high", "critical")
        """
        if level in ["low", "normal", "high", "critical"]:
            old_level = self.cluster_activity_level
            self.cluster_activity_level = level
            
            if old_level != level:
                logger.info(f"Cluster activity level changed: {old_level} -> {level}")
                self.metrics["adaptive_adjustments"] += 1
        else:
            logger.warning(f"Invalid cluster activity level: {level}")
    
    def trigger_task(self, task_id: str) -> bool:
        """
        Manually trigger a task to run immediately.
        
        Args:
            task_id: Task to trigger
            
        Returns:
            True if task was triggered, False if not found or already running
        """
        if task_id not in self.tasks:
            return False
        
        if task_id in self.running_tasks:
            logger.warning(f"Task {task_id} is already running")
            return False
        
        task = self.tasks[task_id]
        task.next_run = datetime.utcnow()
        logger.info(f"Manually triggered task: {task.name}")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        return {
            "task_id": task.task_id,
            "name": task.name,
            "enabled": task.enabled,
            "schedule_type": task.schedule_type.value,
            "interval_seconds": task.interval_seconds,
            "priority": task.priority,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "is_running": task.task_id in self.running_tasks,
            "metadata": task.metadata
        }
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """Get status for all tasks."""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    def get_scheduler_metrics(self) -> Dict[str, Any]:
        """Get scheduler performance metrics."""
        return {
            "is_running": self.is_running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": len([t for t in self.tasks.values() if t.enabled]),
            "running_tasks": len(self.running_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "cluster_activity_level": self.cluster_activity_level,
            "load_factor": self.load_factor,
            "metrics": self.metrics.copy()
        }
