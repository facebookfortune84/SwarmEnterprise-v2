"""
Health Monitor Agent

Continuously monitors system health across all components:
- Service availability
- Resource utilization
- Error rates
- Performance metrics
- Database health
- External dependencies
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
import psutil
import httpx
from collections import deque

from backend.llm.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class ComponentType(Enum):
    """Types of monitored components"""
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    EXTERNAL_SERVICE = "external_service"
    WORKER = "worker"
    LLM = "llm"


@dataclass
class HealthCheck:
    """Individual health check result"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    response_time_ms: float
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResourceMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    open_connections: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthReport:
    """Comprehensive health report"""
    overall_status: HealthStatus
    components: List[HealthCheck]
    resource_metrics: ResourceMetrics
    error_rate: float
    avg_response_time_ms: float
    unhealthy_components: List[str]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthThresholds:
    """Configurable health thresholds"""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 75.0
    memory_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 95.0
    response_time_warning_ms: float = 1000.0
    response_time_critical_ms: float = 5000.0
    error_rate_warning: float = 0.05  # 5%
    error_rate_critical: float = 0.15  # 15%


class HealthMonitor:
    """
    Comprehensive health monitoring agent
    
    Monitors all system components and provides:
    - Real-time health status
    - Resource utilization tracking
    - Error rate monitoring
    - Performance metrics
    - Automatic alerting
    - AI-powered diagnostics
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        check_interval_seconds: int = 30,
        thresholds: Optional[HealthThresholds] = None
    ):
        self.ollama = ollama_client or OllamaClient()
        self.check_interval = check_interval_seconds
        self.thresholds = thresholds or HealthThresholds()
        
        # Health check registry
        self.health_checks: Dict[str, Dict] = {}
        
        # Metrics history (last 100 checks per component)
        self.metrics_history: Dict[str, deque] = {}
        
        # Error tracking
        self.error_counts: Dict[str, int] = {}
        self.total_checks: Dict[str, int] = {}
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
        
        # Monitoring state
        self.is_monitoring = False
        self.last_report: Optional[HealthReport] = None
        
        # Register default health checks
        self._register_default_checks()
    
    def register_health_check(
        self,
        component: str,
        component_type: ComponentType,
        check_func: Callable
    ):
        """
        Register a custom health check
        
        Args:
            component: Component name
            component_type: Type of component
            check_func: Async function that returns HealthCheck
        """
        self.health_checks[component] = {
            "type": component_type,
            "func": check_func
        }
        self.metrics_history[component] = deque(maxlen=100)
        self.error_counts[component] = 0
        self.total_checks[component] = 0
        
        logger.info(f"Registered health check: {component}")
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for health alerts"""
        self.alert_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.is_monitoring = True
        logger.info("Starting health monitoring")
        
        while self.is_monitoring:
            try:
                report = await self.check_health()
                self.last_report = report
                
                # Trigger alerts if needed
                if report.overall_status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    await self._trigger_alerts(report)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        logger.info("Stopped health monitoring")
    
    async def check_health(self) -> HealthReport:
        """
        Perform comprehensive health check
        
        Returns:
            Health report with all component statuses
        """
        logger.debug("Performing health check")
        
        # Run all health checks concurrently
        check_tasks = []
        for component, config in self.health_checks.items():
            check_tasks.append(self._run_health_check(component, config))
        
        component_results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Filter out exceptions and collect valid results
        components = []
        for result in component_results:
            if isinstance(result, HealthCheck):
                components.append(result)
                
                # Update metrics history
                self.metrics_history[result.component].append(result)
                self.total_checks[result.component] += 1
                
                if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    self.error_counts[result.component] += 1
        
        # Get resource metrics
        resource_metrics = await self._get_resource_metrics()
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(components, resource_metrics)
        
        # Calculate error rate
        error_rate = self._calculate_error_rate()
        
        # Calculate average response time
        avg_response_time = sum(c.response_time_ms for c in components) / len(components) if components else 0
        
        # Identify unhealthy components
        unhealthy = [c.component for c in components if c.status != HealthStatus.HEALTHY]
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            components,
            resource_metrics,
            error_rate,
            avg_response_time
        )
        
        return HealthReport(
            overall_status=overall_status,
            components=components,
            resource_metrics=resource_metrics,
            error_rate=error_rate,
            avg_response_time_ms=avg_response_time,
            unhealthy_components=unhealthy,
            recommendations=recommendations
        )
    
    async def _run_health_check(
        self,
        component: str,
        config: Dict
    ) -> HealthCheck:
        """Run a single health check"""
        start_time = datetime.utcnow()
        
        try:
            result = await config["func"]()
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Ensure result is a HealthCheck
            if isinstance(result, HealthCheck):
                result.response_time_ms = response_time
                return result
            else:
                # Create HealthCheck from boolean result
                return HealthCheck(
                    component=component,
                    component_type=config["type"],
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    response_time_ms=response_time
                )
                
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Health check failed for {component}: {e}")
            
            return HealthCheck(
                component=component,
                component_type=config["type"],
                status=HealthStatus.CRITICAL,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _get_resource_metrics(self) -> ResourceMetrics:
        """Get current system resource metrics"""
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Network I/O
        net_io = psutil.net_io_counters()
        network_sent_mb = net_io.bytes_sent / (1024 * 1024)
        network_recv_mb = net_io.bytes_recv / (1024 * 1024)
        
        # Open connections
        try:
            connections = len(psutil.net_connections())
        except Exception:
            connections = 0
        
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            open_connections=connections
        )
    
    def _calculate_overall_status(
        self,
        components: List[HealthCheck],
        resources: ResourceMetrics
    ) -> HealthStatus:
        """Calculate overall system health status"""
        
        # Check for critical components
        critical_components = [c for c in components if c.status == HealthStatus.CRITICAL]
        if critical_components:
            return HealthStatus.CRITICAL
        
        # Check resource thresholds
        if (resources.cpu_percent >= self.thresholds.cpu_critical or
            resources.memory_percent >= self.thresholds.memory_critical or
            resources.disk_percent >= self.thresholds.disk_critical):
            return HealthStatus.CRITICAL
        
        # Check for unhealthy components
        unhealthy_components = [c for c in components if c.status == HealthStatus.UNHEALTHY]
        if len(unhealthy_components) > len(components) * 0.3:  # More than 30% unhealthy
            return HealthStatus.UNHEALTHY
        
        # Check for degraded components or resources
        degraded_components = [c for c in components if c.status == HealthStatus.DEGRADED]
        if (degraded_components or
            resources.cpu_percent >= self.thresholds.cpu_warning or
            resources.memory_percent >= self.thresholds.memory_warning or
            resources.disk_percent >= self.thresholds.disk_warning):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _calculate_error_rate(self) -> float:
        """Calculate overall error rate"""
        total_errors = sum(self.error_counts.values())
        total_checks = sum(self.total_checks.values())
        
        if total_checks == 0:
            return 0.0
        
        return total_errors / total_checks
    
    async def _generate_recommendations(
        self,
        components: List[HealthCheck],
        resources: ResourceMetrics,
        error_rate: float,
        avg_response_time: float
    ) -> List[str]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        # Resource recommendations
        if resources.cpu_percent >= self.thresholds.cpu_critical:
            recommendations.append(
                f"CRITICAL: CPU usage at {resources.cpu_percent:.1f}%. Scale horizontally or optimize CPU-intensive operations."
            )
        elif resources.cpu_percent >= self.thresholds.cpu_warning:
            recommendations.append(
                f"WARNING: CPU usage at {resources.cpu_percent:.1f}%. Monitor for continued increase."
            )
        
        if resources.memory_percent >= self.thresholds.memory_critical:
            recommendations.append(
                f"CRITICAL: Memory usage at {resources.memory_percent:.1f}%. Check for memory leaks or scale up."
            )
        elif resources.memory_percent >= self.thresholds.memory_warning:
            recommendations.append(
                f"WARNING: Memory usage at {resources.memory_percent:.1f}%. Monitor memory consumption."
            )
        
        if resources.disk_percent >= self.thresholds.disk_critical:
            recommendations.append(
                f"CRITICAL: Disk usage at {resources.disk_percent:.1f}%. Clean up logs or expand storage."
            )
        elif resources.disk_percent >= self.thresholds.disk_warning:
            recommendations.append(
                f"WARNING: Disk usage at {resources.disk_percent:.1f}%. Plan for storage expansion."
            )
        
        # Component recommendations
        unhealthy = [c for c in components if c.status != HealthStatus.HEALTHY]
        if unhealthy:
            for component in unhealthy:
                recommendations.append(
                    f"{component.status.value.upper()}: {component.component} - {component.error_message or 'Health check failed'}"
                )
        
        # Performance recommendations
        if avg_response_time >= self.thresholds.response_time_critical_ms:
            recommendations.append(
                f"CRITICAL: Average response time {avg_response_time:.0f}ms. Investigate performance bottlenecks."
            )
        elif avg_response_time >= self.thresholds.response_time_warning_ms:
            recommendations.append(
                f"WARNING: Average response time {avg_response_time:.0f}ms. Monitor performance trends."
            )
        
        # Error rate recommendations
        if error_rate >= self.thresholds.error_rate_critical:
            recommendations.append(
                f"CRITICAL: Error rate at {error_rate*100:.1f}%. Investigate failing components immediately."
            )
        elif error_rate >= self.thresholds.error_rate_warning:
            recommendations.append(
                f"WARNING: Error rate at {error_rate*100:.1f}%. Monitor error trends."
            )
        
        # AI-powered recommendations
        if unhealthy and self.ollama:
            try:
                ai_rec = await self._get_ai_recommendations(components, resources)
                if ai_rec:
                    recommendations.append(f"AI Insight: {ai_rec}")
            except Exception as e:
                logger.warning(f"Failed to get AI recommendations: {e}")
        
        return recommendations
    
    async def _get_ai_recommendations(
        self,
        components: List[HealthCheck],
        resources: ResourceMetrics
    ) -> str:
        """Get AI-powered recommendations"""
        
        unhealthy = [c for c in components if c.status != HealthStatus.HEALTHY]
        
        prompt = f"""Analyze this system health issue and provide a concise recommendation (1-2 sentences):

Unhealthy Components:
{chr(10).join(f'- {c.component} ({c.component_type.value}): {c.status.value} - {c.error_message}' for c in unhealthy[:5])}

Resources:
- CPU: {resources.cpu_percent:.1f}%
- Memory: {resources.memory_percent:.1f}%
- Disk: {resources.disk_percent:.1f}%

What is the most likely root cause and immediate action?"""
        
        try:
            response = await self.ollama.generate(
                prompt=prompt,
                temperature=0.3
            )
            return response.strip()
        except Exception as e:
            logger.warning(f"AI recommendation failed: {e}")
            return ""
    
    async def _trigger_alerts(self, report: HealthReport):
        """Trigger registered alert callbacks"""
        
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(report)
                else:
                    callback(report)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _register_default_checks(self):
        """Register default health checks"""
        
        # API health check
        async def check_api():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8000/health", timeout=5.0)
                    return HealthCheck(
                        component="api",
                        component_type=ComponentType.API,
                        status=HealthStatus.HEALTHY if response.status_code == 200 else HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        metadata={"status_code": response.status_code}
                    )
            except Exception as e:
                return HealthCheck(
                    component="api",
                    component_type=ComponentType.API,
                    status=HealthStatus.CRITICAL,
                    response_time_ms=0,
                    error_message=str(e)
                )
        
        self.register_health_check("api", ComponentType.API, check_api)
        
        # Ollama LLM health check
        async def check_ollama():
            try:
                healthy = await self.ollama.health_check()
                return HealthCheck(
                    component="ollama",
                    component_type=ComponentType.LLM,
                    status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
                    response_time_ms=0
                )
            except Exception as e:
                return HealthCheck(
                    component="ollama",
                    component_type=ComponentType.LLM,
                    status=HealthStatus.CRITICAL,
                    response_time_ms=0,
                    error_message=str(e)
                )
        
        self.register_health_check("ollama", ComponentType.LLM, check_ollama)
    
    def get_component_history(
        self,
        component: str,
        limit: int = 100
    ) -> List[HealthCheck]:
        """Get health check history for a component"""
        
        if component not in self.metrics_history:
            return []
        
        return list(self.metrics_history[component])[-limit:]
    
    def get_component_uptime(self, component: str) -> float:
        """Get component uptime percentage"""
        
        if component not in self.total_checks or self.total_checks[component] == 0:
            return 100.0
        
        successful = self.total_checks[component] - self.error_counts[component]
        return (successful / self.total_checks[component]) * 100

# Made with Bob
