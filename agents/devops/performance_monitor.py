"""
Performance Monitor Agent - Performance Optimization and Monitoring

Monitors and optimizes application performance:
- Real-time performance metrics
- Bottleneck detection
- Resource optimization
- Performance recommendations
- Auto-scaling triggers
"""

import logging
import asyncio
import json
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Performance metric types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"


class AlertLevel(str, Enum):
    """Performance alert levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    unit: str
    labels: Dict[str, str]


@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    level: AlertLevel
    metric_type: MetricType
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    recommendations: List[str]


@dataclass
class PerformanceReport:
    """Performance analysis report"""
    report_id: str
    period_start: datetime
    period_end: datetime
    metrics_summary: Dict[str, Any]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[str]
    score: float


class PerformanceMonitor:
    """
    Autonomous performance monitoring agent.
    
    Capabilities:
    - Real-time metric collection
    - Anomaly detection
    - Bottleneck identification
    - Performance optimization recommendations
    - Auto-scaling triggers
    - AI-powered analysis
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        collection_interval: int = 60,
    ):
        self.ollama = ollama_client or OllamaClient()
        self.collection_interval = collection_interval
        self.metrics: Dict[MetricType, List[PerformanceMetric]] = {
            metric_type: [] for metric_type in MetricType
        }
        self.alerts: List[PerformanceAlert] = []
        self.thresholds = self._default_thresholds()
        self.monitoring = False
        
        logger.info("Performance Monitor initialized")
    
    def _default_thresholds(self) -> Dict[MetricType, Dict[str, float]]:
        """Default performance thresholds"""
        return {
            MetricType.CPU: {"warning": 70.0, "critical": 90.0},
            MetricType.MEMORY: {"warning": 75.0, "critical": 90.0},
            MetricType.DISK: {"warning": 80.0, "critical": 95.0},
            MetricType.LATENCY: {"warning": 500.0, "critical": 1000.0},  # ms
            MetricType.ERROR_RATE: {"warning": 1.0, "critical": 5.0},  # %
        }
    
    async def start_monitoring(self, deployment_id: str) -> None:
        """Start continuous monitoring"""
        self.monitoring = True
        logger.info(f"Starting performance monitoring: {deployment_id}")
        
        while self.monitoring:
            try:
                # Collect metrics
                metrics = await self._collect_metrics(deployment_id)
                
                # Store metrics
                for metric in metrics:
                    self.metrics[metric.metric_type].append(metric)
                    
                    # Keep only last 24 hours
                    cutoff = datetime.utcnow() - timedelta(hours=24)
                    self.metrics[metric.metric_type] = [
                        m for m in self.metrics[metric.metric_type]
                        if m.timestamp > cutoff
                    ]
                
                # Check thresholds
                alerts = await self._check_thresholds(metrics)
                self.alerts.extend(alerts)
                
                # Detect anomalies
                anomalies = await self._detect_anomalies(metrics)
                if anomalies:
                    logger.warning(f"Anomalies detected: {len(anomalies)}")
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def stop_monitoring(self) -> None:
        """Stop monitoring"""
        self.monitoring = False
        logger.info("Performance monitoring stopped")
    
    async def _collect_metrics(self, deployment_id: str) -> List[PerformanceMetric]:
        """Collect performance metrics"""
        metrics = []
        timestamp = datetime.utcnow()
        
        # CPU metrics
        cpu_usage = await self._get_cpu_usage(deployment_id)
        metrics.append(PerformanceMetric(
            metric_type=MetricType.CPU,
            value=cpu_usage,
            timestamp=timestamp,
            unit="%",
            labels={"deployment": deployment_id},
        ))
        
        # Memory metrics
        memory_usage = await self._get_memory_usage(deployment_id)
        metrics.append(PerformanceMetric(
            metric_type=MetricType.MEMORY,
            value=memory_usage,
            timestamp=timestamp,
            unit="%",
            labels={"deployment": deployment_id},
        ))
        
        # Disk metrics
        disk_usage = await self._get_disk_usage(deployment_id)
        metrics.append(PerformanceMetric(
            metric_type=MetricType.DISK,
            value=disk_usage,
            timestamp=timestamp,
            unit="%",
            labels={"deployment": deployment_id},
        ))
        
        # Network metrics
        network_throughput = await self._get_network_throughput(deployment_id)
        metrics.append(PerformanceMetric(
            metric_type=MetricType.THROUGHPUT,
            value=network_throughput,
            timestamp=timestamp,
            unit="Mbps",
            labels={"deployment": deployment_id},
        ))
        
        # Application metrics
        latency = await self._get_latency(deployment_id)
        metrics.append(PerformanceMetric(
            metric_type=MetricType.LATENCY,
            value=latency,
            timestamp=timestamp,
            unit="ms",
            labels={"deployment": deployment_id},
        ))
        
        error_rate = await self._get_error_rate(deployment_id)
        metrics.append(PerformanceMetric(
            metric_type=MetricType.ERROR_RATE,
            value=error_rate,
            timestamp=timestamp,
            unit="%",
            labels={"deployment": deployment_id},
        ))
        
        return metrics
    
    async def _check_thresholds(
        self,
        metrics: List[PerformanceMetric]
    ) -> List[PerformanceAlert]:
        """Check metrics against thresholds"""
        alerts = []
        
        for metric in metrics:
            if metric.metric_type not in self.thresholds:
                continue
            
            thresholds = self.thresholds[metric.metric_type]
            
            if metric.value >= thresholds["critical"]:
                alert = await self._create_alert(
                    metric,
                    AlertLevel.CRITICAL,
                    thresholds["critical"]
                )
                alerts.append(alert)
            elif metric.value >= thresholds["warning"]:
                alert = await self._create_alert(
                    metric,
                    AlertLevel.WARNING,
                    thresholds["warning"]
                )
                alerts.append(alert)
        
        return alerts
    
    async def _create_alert(
        self,
        metric: PerformanceMetric,
        level: AlertLevel,
        threshold: float
    ) -> PerformanceAlert:
        """Create performance alert with AI recommendations"""
        alert_id = f"alert-{metric.metric_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Generate AI recommendations
        recommendations = await self._generate_recommendations(metric, level)
        
        return PerformanceAlert(
            alert_id=alert_id,
            level=level,
            metric_type=metric.metric_type,
            message=f"{metric.metric_type} {level}: {metric.value}{metric.unit} (threshold: {threshold}{metric.unit})",
            current_value=metric.value,
            threshold=threshold,
            timestamp=datetime.utcnow(),
            recommendations=recommendations,
        )
    
    async def _generate_recommendations(
        self,
        metric: PerformanceMetric,
        level: AlertLevel
    ) -> List[str]:
        """Generate AI-powered optimization recommendations"""
        prompt = f"""
        Performance Issue Detected:
        
        Metric: {metric.metric_type}
        Current Value: {metric.value}{metric.unit}
        Alert Level: {level}
        Deployment: {metric.labels.get('deployment', 'unknown')}
        
        Provide 3-5 specific, actionable recommendations to:
        1. Immediately address this issue
        2. Optimize performance
        3. Prevent future occurrences
        
        Format as a numbered list.
        """
        
        response = await self.ollama.generate(
            prompt,
            system="You are a performance optimization expert."
        )
        
        # Parse recommendations
        recommendations = [
            line.strip() for line in response.split('\n')
            if line.strip() and line.strip()[0].isdigit()
        ]
        
        return recommendations[:5]
    
    async def _detect_anomalies(
        self,
        metrics: List[PerformanceMetric]
    ) -> List[Dict[str, Any]]:
        """Detect performance anomalies using statistical analysis"""
        anomalies = []
        
        for metric in metrics:
            historical = self.metrics.get(metric.metric_type, [])
            if len(historical) < 10:
                continue
            
            # Calculate statistics
            values = [m.value for m in historical[-100:]]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            
            # Check if current value is anomalous (> 3 standard deviations)
            if stdev > 0 and abs(metric.value - mean) > 3 * stdev:
                anomalies.append({
                    "metric_type": metric.metric_type,
                    "value": metric.value,
                    "mean": mean,
                    "stdev": stdev,
                    "deviation": abs(metric.value - mean) / stdev,
                })
        
        return anomalies
    
    async def generate_report(
        self,
        period_hours: int = 24
    ) -> PerformanceReport:
        """Generate performance analysis report"""
        period_start = datetime.utcnow() - timedelta(hours=period_hours)
        period_end = datetime.utcnow()
        
        # Collect metrics for period
        metrics_summary = {}
        for metric_type in MetricType:
            period_metrics = [
                m for m in self.metrics[metric_type]
                if period_start <= m.timestamp <= period_end
            ]
            
            if period_metrics:
                values = [m.value for m in period_metrics]
                metrics_summary[metric_type] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": statistics.mean(values),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                }
        
        # Identify bottlenecks
        bottlenecks = await self._identify_bottlenecks(metrics_summary)
        
        # Generate recommendations
        recommendations = await self._generate_report_recommendations(
            metrics_summary,
            bottlenecks
        )
        
        # Calculate performance score
        score = self._calculate_performance_score(metrics_summary)
        
        return PerformanceReport(
            report_id=f"report-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            period_start=period_start,
            period_end=period_end,
            metrics_summary=metrics_summary,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            score=score,
        )
    
    async def _identify_bottlenecks(
        self,
        metrics_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        for metric_type, stats in metrics_summary.items():
            if metric_type in self.thresholds:
                thresholds = self.thresholds[MetricType(metric_type)]
                
                if stats["p95"] > thresholds["warning"]:
                    bottlenecks.append({
                        "metric": metric_type,
                        "severity": "high" if stats["p95"] > thresholds["critical"] else "medium",
                        "p95_value": stats["p95"],
                        "threshold": thresholds["warning"],
                    })
        
        return bottlenecks
    
    async def _generate_report_recommendations(
        self,
        metrics_summary: Dict[str, Any],
        bottlenecks: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate comprehensive optimization recommendations"""
        if not bottlenecks:
            return ["Performance is within acceptable thresholds. No immediate action required."]
        
        prompt = f"""
        Performance Analysis Summary:
        
        Metrics: {json.dumps(metrics_summary, indent=2)}
        Bottlenecks: {json.dumps(bottlenecks, indent=2)}
        
        Provide comprehensive optimization recommendations:
        1. Priority actions to address bottlenecks
        2. Long-term optimization strategies
        3. Infrastructure scaling recommendations
        4. Code-level optimizations
        5. Monitoring improvements
        """
        
        response = await self.ollama.generate(
            prompt,
            system="You are a performance optimization expert providing strategic recommendations."
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    def _calculate_performance_score(self, metrics_summary: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        if not metrics_summary:
            return 100.0
        
        scores = []
        
        for metric_type, stats in metrics_summary.items():
            if metric_type in self.thresholds:
                thresholds = self.thresholds[MetricType(metric_type)]
                warning = thresholds["warning"]
                
                # Score based on p95 value
                p95 = stats["p95"]
                if p95 <= warning * 0.5:
                    score = 100
                elif p95 <= warning:
                    score = 100 - ((p95 - warning * 0.5) / (warning * 0.5)) * 30
                else:
                    score = 70 - min(((p95 - warning) / warning) * 70, 70)
                
                scores.append(max(0, score))
        
        return statistics.mean(scores) if scores else 100.0
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    # Metric collection methods (TODO: Implement actual collection)
    
    async def _get_cpu_usage(self, deployment_id: str) -> float:
        """Get CPU usage percentage"""
        # TODO: Implement actual CPU metric collection
        return 45.0
    
    async def _get_memory_usage(self, deployment_id: str) -> float:
        """Get memory usage percentage"""
        # TODO: Implement actual memory metric collection
        return 60.0
    
    async def _get_disk_usage(self, deployment_id: str) -> float:
        """Get disk usage percentage"""
        # TODO: Implement actual disk metric collection
        return 55.0
    
    async def _get_network_throughput(self, deployment_id: str) -> float:
        """Get network throughput in Mbps"""
        # TODO: Implement actual network metric collection
        return 150.0
    
    async def _get_latency(self, deployment_id: str) -> float:
        """Get average latency in ms"""
        # TODO: Implement actual latency metric collection
        return 120.0
    
    async def _get_error_rate(self, deployment_id: str) -> float:
        """Get error rate percentage"""
        # TODO: Implement actual error rate collection
        return 0.5
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop_monitoring()
        await self.ollama.close()

# Made with Bob
