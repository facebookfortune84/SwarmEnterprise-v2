"""
Self-Healing Agents Package

Autonomous agents for system health monitoring and automatic recovery.
"""

from agents.self_healing.health_monitor import (
    HealthMonitor,
    HealthStatus,
    HealthCheck,
    HealthReport,
    ComponentType,
    HealthThresholds
)

from agents.self_healing.auto_recovery import (
    AutoRecoveryAgent,
    RecoveryAction,
    RecoveryStatus,
    RecoveryStrategy,
    RecoveryAttempt,
    RecoveryReport
)

from agents.self_healing.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerManager,
    CircuitState,
    CircuitConfig,
    CircuitMetrics,
    CircuitEvent,
    CircuitBreakerError,
    circuit_breaker
)

__all__ = [
    # Health Monitor
    "HealthMonitor",
    "HealthStatus",
    "HealthCheck",
    "HealthReport",
    "ComponentType",
    "HealthThresholds",
    
    # Auto Recovery
    "AutoRecoveryAgent",
    "RecoveryAction",
    "RecoveryStatus",
    "RecoveryStrategy",
    "RecoveryAttempt",
    "RecoveryReport",
    
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitState",
    "CircuitConfig",
    "CircuitMetrics",
    "CircuitEvent",
    "CircuitBreakerError",
    "circuit_breaker",
]

# Made with Bob
