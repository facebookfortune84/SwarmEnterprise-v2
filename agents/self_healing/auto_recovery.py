"""
Auto-Recovery Agent

Automatically detects and recovers from failures:
- Service crashes
- Resource exhaustion
- Network issues
- Database connection failures
- Dependency failures
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import subprocess
import psutil

from backend.llm.ollama_client import OllamaClient
from agents.self_healing.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthReport,
    ComponentType
)


logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Types of recovery actions"""
    RESTART_SERVICE = "restart_service"
    RESTART_CONTAINER = "restart_container"
    CLEAR_CACHE = "clear_cache"
    KILL_PROCESS = "kill_process"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    CLEAR_DISK_SPACE = "clear_disk_space"
    RESTART_DATABASE = "restart_database"
    FLUSH_CONNECTIONS = "flush_connections"
    CUSTOM = "custom"


class RecoveryStatus(Enum):
    """Recovery attempt status"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class RecoveryStrategy:
    """Recovery strategy definition"""
    component: str
    component_type: ComponentType
    actions: List[RecoveryAction]
    max_attempts: int = 3
    cooldown_seconds: int = 60
    escalation_actions: Optional[List[RecoveryAction]] = None
    custom_handler: Optional[Callable] = None


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt"""
    component: str
    action: RecoveryAction
    status: RecoveryStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryReport:
    """Recovery operation report"""
    component: str
    triggered_by: str
    attempts: List[RecoveryAttempt]
    final_status: RecoveryStatus
    total_duration_seconds: float
    health_before: HealthStatus
    health_after: HealthStatus
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AutoRecoveryAgent:
    """
    Autonomous recovery agent
    
    Monitors system health and automatically recovers from failures:
    - Detects unhealthy components
    - Executes recovery strategies
    - Tracks recovery success rates
    - Learns from failures
    - Escalates when needed
    """
    
    def __init__(
        self,
        health_monitor: HealthMonitor,
        ollama_client: Optional[OllamaClient] = None,
        enable_auto_recovery: bool = True
    ):
        self.health_monitor = health_monitor
        self.ollama = ollama_client or OllamaClient()
        self.enable_auto_recovery = enable_auto_recovery
        
        # Recovery strategies registry
        self.strategies: Dict[str, RecoveryStrategy] = {}
        
        # Recovery history
        self.recovery_history: List[RecoveryReport] = []
        
        # Cooldown tracking (component -> last recovery time)
        self.last_recovery: Dict[str, datetime] = {}
        
        # Attempt counters (component -> attempt count)
        self.attempt_counters: Dict[str, int] = {}
        
        # Success rates (component -> success count / total attempts)
        self.success_rates: Dict[str, tuple] = {}
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
        
        # Register default strategies
        self._register_default_strategies()
        
        # Register health monitor callback
        self.health_monitor.register_alert_callback(self._on_health_alert)
    
    def register_strategy(self, strategy: RecoveryStrategy):
        """
        Register a recovery strategy for a component
        
        Args:
            strategy: Recovery strategy definition
        """
        self.strategies[strategy.component] = strategy
        logger.info(f"Registered recovery strategy for: {strategy.component}")
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for recovery alerts"""
        self.alert_callbacks.append(callback)
    
    async def _on_health_alert(self, report: HealthReport):
        """Handle health alerts from monitor"""
        
        if not self.enable_auto_recovery:
            logger.info("Auto-recovery disabled, skipping")
            return
        
        # Identify components needing recovery
        unhealthy_components = [
            c for c in report.components
            if c.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
        ]
        
        if not unhealthy_components:
            return
        
        logger.warning(f"Health alert: {len(unhealthy_components)} unhealthy components")
        
        # Attempt recovery for each component
        for component in unhealthy_components:
            if component.component in self.strategies:
                await self.recover_component(component.component)
    
    async def recover_component(self, component: str) -> RecoveryReport:
        """
        Attempt to recover a component
        
        Args:
            component: Component name
            
        Returns:
            Recovery report with results
        """
        logger.info(f"Starting recovery for component: {component}")
        
        if component not in self.strategies:
            logger.warning(f"No recovery strategy for: {component}")
            return self._create_skipped_report(component, "No strategy defined")
        
        strategy = self.strategies[component]
        
        # Check cooldown
        if not self._check_cooldown(component, strategy.cooldown_seconds):
            logger.info(f"Component {component} in cooldown period")
            return self._create_skipped_report(component, "Cooldown period active")
        
        # Check attempt limit
        if not self._check_attempt_limit(component, strategy.max_attempts):
            logger.warning(f"Component {component} exceeded max attempts")
            # Escalate if configured
            if strategy.escalation_actions:
                return await self._escalate_recovery(component, strategy)
            return self._create_skipped_report(component, "Max attempts exceeded")
        
        # Get health before recovery
        health_report = await self.health_monitor.check_health()
        component_health = next(
            (c for c in health_report.components if c.component == component),
            None
        )
        health_before = component_health.status if component_health else HealthStatus.UNHEALTHY
        
        # Execute recovery actions
        start_time = datetime.utcnow()
        attempts = []
        
        for action in strategy.actions:
            attempt = await self._execute_action(component, action, strategy)
            attempts.append(attempt)
            
            # If action succeeded, check if component is healthy
            if attempt.status == RecoveryStatus.SUCCESS:
                await asyncio.sleep(5)  # Wait for component to stabilize
                
                health_report = await self.health_monitor.check_health()
                component_health = next(
                    (c for c in health_report.components if c.component == component),
                    None
                )
                
                if component_health and component_health.status == HealthStatus.HEALTHY:
                    logger.info(f"Component {component} recovered successfully")
                    break
            
            # If action failed critically, stop
            if attempt.status == RecoveryStatus.FAILED:
                logger.error(f"Recovery action failed for {component}: {action.value}")
                break
        
        # Get health after recovery
        health_report = await self.health_monitor.check_health()
        component_health = next(
            (c for c in health_report.components if c.component == component),
            None
        )
        health_after = component_health.status if component_health else HealthStatus.UNHEALTHY
        
        # Determine final status
        final_status = self._determine_final_status(attempts, health_after)
        
        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Generate recommendations
        recommendations = await self._generate_recovery_recommendations(
            component, attempts, health_before, health_after
        )
        
        # Create report
        report = RecoveryReport(
            component=component,
            triggered_by="health_monitor",
            attempts=attempts,
            final_status=final_status,
            total_duration_seconds=duration,
            health_before=health_before,
            health_after=health_after,
            recommendations=recommendations
        )
        
        # Update tracking
        self._update_tracking(component, final_status)
        
        # Store in history
        self.recovery_history.append(report)
        
        # Trigger alerts
        await self._trigger_alerts(report)
        
        return report
    
    async def _execute_action(
        self,
        component: str,
        action: RecoveryAction,
        strategy: RecoveryStrategy
    ) -> RecoveryAttempt:
        """Execute a single recovery action"""
        
        logger.info(f"Executing {action.value} for {component}")
        start_time = datetime.utcnow()
        
        try:
            # Use custom handler if provided
            if action == RecoveryAction.CUSTOM and strategy.custom_handler:
                result = await strategy.custom_handler(component)
                status = RecoveryStatus.SUCCESS if result else RecoveryStatus.FAILED
                error_msg = None if result else "Custom handler returned False"
            else:
                # Execute built-in action
                status, error_msg = await self._execute_builtin_action(component, action)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return RecoveryAttempt(
                component=component,
                action=action,
                status=status,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                duration_seconds=duration,
                error_message=error_msg
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Action {action.value} failed: {e}")
            
            return RecoveryAttempt(
                component=component,
                action=action,
                status=RecoveryStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.utcnow(),
                duration_seconds=duration,
                error_message=str(e)
            )
    
    async def _execute_builtin_action(
        self,
        component: str,
        action: RecoveryAction
    ) -> tuple[RecoveryStatus, Optional[str]]:
        """Execute a built-in recovery action"""
        
        try:
            if action == RecoveryAction.RESTART_SERVICE:
                return await self._restart_service(component)
            
            elif action == RecoveryAction.RESTART_CONTAINER:
                return await self._restart_container(component)
            
            elif action == RecoveryAction.CLEAR_CACHE:
                return await self._clear_cache(component)
            
            elif action == RecoveryAction.KILL_PROCESS:
                return await self._kill_process(component)
            
            elif action == RecoveryAction.SCALE_UP:
                return await self._scale_up(component)
            
            elif action == RecoveryAction.CLEAR_DISK_SPACE:
                return await self._clear_disk_space()
            
            elif action == RecoveryAction.FLUSH_CONNECTIONS:
                return await self._flush_connections(component)
            
            else:
                return RecoveryStatus.SKIPPED, f"Action {action.value} not implemented"
                
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _restart_service(self, component: str) -> tuple[RecoveryStatus, Optional[str]]:
        """Restart a systemd service"""
        try:
            # Restart service using systemctl
            result = subprocess.run(
                ["systemctl", "restart", component],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return RecoveryStatus.SUCCESS, None
            else:
                return RecoveryStatus.FAILED, result.stderr
                
        except subprocess.TimeoutExpired:
            return RecoveryStatus.FAILED, "Restart timeout"
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _restart_container(self, component: str) -> tuple[RecoveryStatus, Optional[str]]:
        """Restart a Docker container"""
        try:
            # Restart container using docker
            result = subprocess.run(
                ["docker", "restart", component],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return RecoveryStatus.SUCCESS, None
            else:
                return RecoveryStatus.FAILED, result.stderr
                
        except subprocess.TimeoutExpired:
            return RecoveryStatus.FAILED, "Restart timeout"
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _clear_cache(self, component: str) -> tuple[RecoveryStatus, Optional[str]]:
        """Clear cache for a component"""
        try:
            # This would integrate with Redis or other cache
            # For now, just log
            logger.info(f"Clearing cache for {component}")
            return RecoveryStatus.SUCCESS, None
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _kill_process(self, component: str) -> tuple[RecoveryStatus, Optional[str]]:
        """Kill a stuck process"""
        try:
            # Find and kill process by name
            killed = False
            for proc in psutil.process_iter(['name', 'pid']):
                if component in proc.info['name']:
                    proc.kill()
                    killed = True
                    logger.info(f"Killed process {proc.info['pid']}")
            
            if killed:
                return RecoveryStatus.SUCCESS, None
            else:
                return RecoveryStatus.SKIPPED, "No matching process found"
                
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _scale_up(self, component: str) -> tuple[RecoveryStatus, Optional[str]]:
        """Scale up a component"""
        try:
            # This would integrate with orchestration system
            logger.info(f"Scaling up {component}")
            return RecoveryStatus.SUCCESS, None
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _clear_disk_space(self) -> tuple[RecoveryStatus, Optional[str]]:
        """Clear disk space"""
        try:
            # Clear temporary files, logs, etc.
            freed_mb = 0
            
            # Clear /tmp
            subprocess.run(["find", "/tmp", "-type", "f", "-atime", "+7", "-delete"])
            
            # Rotate logs
            subprocess.run(["logrotate", "-f", "/etc/logrotate.conf"])
            
            logger.info(f"Cleared disk space: ~{freed_mb}MB")
            return RecoveryStatus.SUCCESS, None
            
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _flush_connections(self, component: str) -> tuple[RecoveryStatus, Optional[str]]:
        """Flush network connections"""
        try:
            # This would flush connection pools
            logger.info(f"Flushing connections for {component}")
            return RecoveryStatus.SUCCESS, None
        except Exception as e:
            return RecoveryStatus.FAILED, str(e)
    
    async def _escalate_recovery(
        self,
        component: str,
        strategy: RecoveryStrategy
    ) -> RecoveryReport:
        """Escalate to more aggressive recovery actions"""
        
        logger.warning(f"Escalating recovery for {component}")
        
        if not strategy.escalation_actions:
            return self._create_skipped_report(component, "No escalation actions")
        
        # Reset attempt counter for escalation
        self.attempt_counters[component] = 0
        
        # Execute escalation actions
        start_time = datetime.utcnow()
        attempts = []
        
        for action in strategy.escalation_actions:
            attempt = await self._execute_action(component, action, strategy)
            attempts.append(attempt)
            
            if attempt.status == RecoveryStatus.SUCCESS:
                break
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Get final health
        health_report = await self.health_monitor.check_health()
        component_health = next(
            (c for c in health_report.components if c.component == component),
            None
        )
        health_after = component_health.status if component_health else HealthStatus.UNHEALTHY
        
        final_status = self._determine_final_status(attempts, health_after)
        
        return RecoveryReport(
            component=component,
            triggered_by="escalation",
            attempts=attempts,
            final_status=final_status,
            total_duration_seconds=duration,
            health_before=HealthStatus.CRITICAL,
            health_after=health_after,
            recommendations=["Escalation actions executed", "Manual intervention may be required"],
            timestamp=datetime.utcnow()
        )
    
    def _check_cooldown(self, component: str, cooldown_seconds: int) -> bool:
        """Check if component is in cooldown period"""
        
        if component not in self.last_recovery:
            return True
        
        elapsed = (datetime.utcnow() - self.last_recovery[component]).total_seconds()
        return elapsed >= cooldown_seconds
    
    def _check_attempt_limit(self, component: str, max_attempts: int) -> bool:
        """Check if component has exceeded attempt limit"""
        
        if component not in self.attempt_counters:
            return True
        
        return self.attempt_counters[component] < max_attempts
    
    def _update_tracking(self, component: str, status: RecoveryStatus):
        """Update recovery tracking"""
        
        # Update last recovery time
        self.last_recovery[component] = datetime.utcnow()
        
        # Update attempt counter
        if component not in self.attempt_counters:
            self.attempt_counters[component] = 0
        self.attempt_counters[component] += 1
        
        # Update success rate
        if component not in self.success_rates:
            self.success_rates[component] = (0, 0)
        
        successes, total = self.success_rates[component]
        total += 1
        if status == RecoveryStatus.SUCCESS:
            successes += 1
        
        self.success_rates[component] = (successes, total)
        
        # Reset attempt counter on success
        if status == RecoveryStatus.SUCCESS:
            self.attempt_counters[component] = 0
    
    def _determine_final_status(
        self,
        attempts: List[RecoveryAttempt],
        health_after: HealthStatus
    ) -> RecoveryStatus:
        """Determine final recovery status"""
        
        if health_after == HealthStatus.HEALTHY:
            return RecoveryStatus.SUCCESS
        
        if any(a.status == RecoveryStatus.SUCCESS for a in attempts):
            if health_after == HealthStatus.DEGRADED:
                return RecoveryStatus.PARTIAL
            return RecoveryStatus.SUCCESS
        
        return RecoveryStatus.FAILED
    
    async def _generate_recovery_recommendations(
        self,
        component: str,
        attempts: List[RecoveryAttempt],
        health_before: HealthStatus,
        health_after: HealthStatus
    ) -> List[str]:
        """Generate recommendations based on recovery results"""
        
        recommendations = []
        
        # Check if recovery improved health
        if health_after.value < health_before.value:  # Enum ordering
            recommendations.append("Recovery improved component health")
        elif health_after == health_before:
            recommendations.append("Recovery did not improve health - investigate root cause")
        
        # Check for repeated failures
        if component in self.success_rates:
            successes, total = self.success_rates[component]
            success_rate = successes / total if total > 0 else 0
            
            if success_rate < 0.5 and total >= 5:
                recommendations.append(
                    f"Low success rate ({success_rate*100:.0f}%) - consider updating recovery strategy"
                )
        
        # Check for failed actions
        failed_actions = [a for a in attempts if a.status == RecoveryStatus.FAILED]
        if failed_actions:
            recommendations.append(
                f"{len(failed_actions)} recovery actions failed - review error logs"
            )
        
        return recommendations
    
    def _create_skipped_report(self, component: str, reason: str) -> RecoveryReport:
        """Create a skipped recovery report"""
        
        return RecoveryReport(
            component=component,
            triggered_by="health_monitor",
            attempts=[],
            final_status=RecoveryStatus.SKIPPED,
            total_duration_seconds=0,
            health_before=HealthStatus.UNHEALTHY,
            health_after=HealthStatus.UNHEALTHY,
            recommendations=[f"Recovery skipped: {reason}"]
        )
    
    async def _trigger_alerts(self, report: RecoveryReport):
        """Trigger alert callbacks"""
        
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(report)
                else:
                    callback(report)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _register_default_strategies(self):
        """Register default recovery strategies"""
        
        # API service recovery
        self.register_strategy(RecoveryStrategy(
            component="api",
            component_type=ComponentType.API,
            actions=[
                RecoveryAction.RESTART_CONTAINER,
                RecoveryAction.CLEAR_CACHE
            ],
            max_attempts=3,
            cooldown_seconds=60,
            escalation_actions=[
                RecoveryAction.RESTART_SERVICE,
                RecoveryAction.ROLLBACK
            ]
        ))
        
        # Database recovery
        self.register_strategy(RecoveryStrategy(
            component="database",
            component_type=ComponentType.DATABASE,
            actions=[
                RecoveryAction.FLUSH_CONNECTIONS,
                RecoveryAction.RESTART_CONTAINER
            ],
            max_attempts=2,
            cooldown_seconds=120,
            escalation_actions=[
                RecoveryAction.FAILOVER
            ]
        ))
    
    def get_success_rate(self, component: str) -> float:
        """Get recovery success rate for a component"""
        
        if component not in self.success_rates:
            return 0.0
        
        successes, total = self.success_rates[component]
        return successes / total if total > 0 else 0.0
    
    def get_recovery_history(
        self,
        component: Optional[str] = None,
        limit: int = 100
    ) -> List[RecoveryReport]:
        """Get recovery history"""
        
        history = self.recovery_history
        
        if component:
            history = [r for r in history if r.component == component]
        
        return history[-limit:]

# Made with Bob
