"""
Circuit Breaker Agent

Prevents cascading failures by breaking circuits when services fail:
- Monitors service health
- Opens circuit on repeated failures
- Half-open state for testing recovery
- Automatic circuit closing on success
- Metrics and alerting
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from collections import deque
import time

from backend.llm.ollama_client import OllamaClient


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 2           # Successes to close from half-open
    timeout_seconds: int = 60            # Time before trying half-open
    half_open_max_calls: int = 3         # Max calls in half-open state
    window_size: int = 100               # Rolling window size for metrics
    error_rate_threshold: float = 0.5    # Error rate to open (50%)


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


@dataclass
class CircuitEvent:
    """Circuit state change event"""
    circuit_name: str
    old_state: CircuitState
    new_state: CircuitState
    reason: str
    metrics: CircuitMetrics
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CircuitBreakerError(Exception):
    """Raised when circuit is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker for a single service
    
    Implements the circuit breaker pattern to prevent cascading failures:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Blocking requests, failing fast
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitConfig] = None
    ):
        self.name = name
        self.config = config or CircuitConfig()
        
        # State
        self.state = CircuitState.CLOSED
        self.opened_at: Optional[datetime] = None
        self.half_open_calls = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        
        # Metrics
        self.metrics = CircuitMetrics()
        
        # Rolling window for recent calls
        self.recent_calls: deque = deque(maxlen=self.config.window_size)
        
        # Event callbacks
        self.event_callbacks: List[Callable] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def register_event_callback(self, callback: Callable):
        """Register callback for state change events"""
        self.event_callbacks.append(callback)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            # Check if circuit allows call
            if not self._can_attempt_call():
                self.metrics.rejected_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}"
                )
            
            # Track half-open calls
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
        
        # Execute function
        start_time = time.time()
        success = False
        error = None
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            success = True
            return result
            
        except Exception as e:
            error = e
            raise
            
        finally:
            duration = time.time() - start_time
            
            # Record call result
            async with self._lock:
                await self._record_call(success, duration, error)
    
    def _can_attempt_call(self) -> bool:
        """Check if call can be attempted in current state"""
        
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self.opened_at:
                elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    # Transition to half-open
                    self._change_state(
                        CircuitState.HALF_OPEN,
                        "Timeout elapsed, testing recovery"
                    )
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Limit calls in half-open state
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    async def _record_call(self, success: bool, duration: float, error: Optional[Exception]):
        """Record call result and update state"""
        
        # Update metrics
        self.metrics.total_calls += 1
        
        if success:
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = datetime.utcnow()
            self.consecutive_failures = 0
            self.consecutive_successes += 1
            
            # Record in rolling window
            self.recent_calls.append({
                "success": True,
                "duration": duration,
                "timestamp": datetime.utcnow()
            })
            
            # Handle state transitions on success
            if self.state == CircuitState.HALF_OPEN:
                if self.consecutive_successes >= self.config.success_threshold:
                    self._change_state(
                        CircuitState.CLOSED,
                        f"Service recovered ({self.consecutive_successes} consecutive successes)"
                    )
        else:
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self.consecutive_successes = 0
            self.consecutive_failures += 1
            
            # Record in rolling window
            self.recent_calls.append({
                "success": False,
                "duration": duration,
                "error": str(error) if error else "Unknown error",
                "timestamp": datetime.utcnow()
            })
            
            # Handle state transitions on failure
            if self.state == CircuitState.CLOSED:
                # Check if should open circuit
                if (self.consecutive_failures >= self.config.failure_threshold or
                    self._calculate_recent_error_rate() >= self.config.error_rate_threshold):
                    self._change_state(
                        CircuitState.OPEN,
                        f"Failure threshold exceeded ({self.consecutive_failures} failures)"
                    )
                    self.opened_at = datetime.utcnow()
            
            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._change_state(
                    CircuitState.OPEN,
                    "Service still failing in half-open state"
                )
                self.opened_at = datetime.utcnow()
    
    def _calculate_recent_error_rate(self) -> float:
        """Calculate error rate from recent calls"""
        if not self.recent_calls:
            return 0.0
        
        failures = sum(1 for call in self.recent_calls if not call["success"])
        return failures / len(self.recent_calls)
    
    def _change_state(self, new_state: CircuitState, reason: str):
        """Change circuit state and trigger events"""
        old_state = self.state
        self.state = new_state
        self.metrics.current_state = new_state
        self.metrics.state_changes += 1
        
        logger.info(f"Circuit '{self.name}': {old_state.value} -> {new_state.value} ({reason})")
        
        # Create event
        event = CircuitEvent(
            circuit_name=self.name,
            old_state=old_state,
            new_state=new_state,
            reason=reason,
            metrics=self.metrics
        )
        
        # Trigger callbacks
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event callback failed: {e}")
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.opened_at = None
        self.half_open_calls = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        logger.info(f"Circuit '{self.name}' manually reset")
    
    def get_metrics(self) -> CircuitMetrics:
        """Get current metrics"""
        return self.metrics
    
    def get_state(self) -> CircuitState:
        """Get current state"""
        return self.state


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers
    
    Provides centralized management of circuit breakers for different services.
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        
        # Circuit breakers registry
        self.circuits: Dict[str, CircuitBreaker] = {}
        
        # Global event callbacks
        self.event_callbacks: List[Callable] = []
        
        # Event history
        self.event_history: deque = deque(maxlen=1000)
    
    def create_circuit(
        self,
        name: str,
        config: Optional[CircuitConfig] = None
    ) -> CircuitBreaker:
        """
        Create a new circuit breaker
        
        Args:
            name: Circuit name
            config: Circuit configuration
            
        Returns:
            Circuit breaker instance
        """
        if name in self.circuits:
            logger.warning(f"Circuit '{name}' already exists")
            return self.circuits[name]
        
        circuit = CircuitBreaker(name, config)
        
        # Register global event callback
        circuit.register_event_callback(self._on_circuit_event)
        
        self.circuits[name] = circuit
        logger.info(f"Created circuit breaker: {name}")
        
        return circuit
    
    def get_circuit(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuits.get(name)
    
    def register_event_callback(self, callback: Callable):
        """Register global event callback"""
        self.event_callbacks.append(callback)
    
    async def _on_circuit_event(self, event: CircuitEvent):
        """Handle circuit events"""
        
        # Store in history
        self.event_history.append(event)
        
        # Trigger global callbacks
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Global event callback failed: {e}")
        
        # Generate AI insights for critical events
        if event.new_state == CircuitState.OPEN:
            await self._generate_insights(event)
    
    async def _generate_insights(self, event: CircuitEvent):
        """Generate AI insights for circuit opening"""
        
        try:
            prompt = f"""Analyze this circuit breaker event and provide a brief recommendation (1-2 sentences):

Circuit: {event.circuit_name}
State Change: {event.old_state.value} -> {event.new_state.value}
Reason: {event.reason}
Error Rate: {event.metrics.error_rate*100:.1f}%
Failed Calls: {event.metrics.failed_calls}
Total Calls: {event.metrics.total_calls}

What is the likely cause and recommended action?"""
            
            insight = await self.ollama.generate(
                prompt=prompt,
                temperature=0.3
            )
            
            logger.info(f"AI Insight for {event.circuit_name}: {insight.strip()}")
            
        except Exception as e:
            logger.warning(f"Failed to generate insights: {e}")
    
    def get_all_metrics(self) -> Dict[str, CircuitMetrics]:
        """Get metrics for all circuits"""
        return {
            name: circuit.get_metrics()
            for name, circuit in self.circuits.items()
        }
    
    def get_open_circuits(self) -> List[str]:
        """Get list of open circuits"""
        return [
            name for name, circuit in self.circuits.items()
            if circuit.get_state() == CircuitState.OPEN
        ]
    
    def get_event_history(self, limit: int = 100) -> List[CircuitEvent]:
        """Get recent circuit events"""
        return list(self.event_history)[-limit:]
    
    def reset_circuit(self, name: str) -> bool:
        """Reset a circuit breaker"""
        circuit = self.circuits.get(name)
        if circuit:
            circuit.reset()
            return True
        return False
    
    def reset_all_circuits(self):
        """Reset all circuit breakers"""
        for circuit in self.circuits.values():
            circuit.reset()
        logger.info("All circuits reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of all circuits"""
        
        total_circuits = len(self.circuits)
        open_circuits = len(self.get_open_circuits())
        half_open_circuits = sum(
            1 for c in self.circuits.values()
            if c.get_state() == CircuitState.HALF_OPEN
        )
        
        return {
            "total_circuits": total_circuits,
            "open_circuits": open_circuits,
            "half_open_circuits": half_open_circuits,
            "closed_circuits": total_circuits - open_circuits - half_open_circuits,
            "health_status": "healthy" if open_circuits == 0 else "degraded",
            "circuits": {
                name: {
                    "state": circuit.get_state().value,
                    "error_rate": circuit.get_metrics().error_rate,
                    "total_calls": circuit.get_metrics().total_calls
                }
                for name, circuit in self.circuits.items()
            }
        }


# Decorator for easy circuit breaker usage
def circuit_breaker(
    name: str,
    manager: CircuitBreakerManager,
    config: Optional[CircuitConfig] = None
):
    """
    Decorator to wrap function with circuit breaker
    
    Usage:
        @circuit_breaker("my_service", manager)
        async def call_service():
            # Service call
            pass
    """
    def decorator(func):
        # Create circuit if not exists
        if name not in manager.circuits:
            manager.create_circuit(name, config)
        
        async def wrapper(*args, **kwargs):
            circuit = manager.get_circuit(name)
            if circuit is None:
                raise ValueError(f"Circuit breaker '{name}' not found")
            return await circuit.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    async def main():
        # Create manager
        manager = CircuitBreakerManager()
        
        # Create circuit
        circuit = manager.create_circuit(
            "api_service",
            CircuitConfig(
                failure_threshold=3,
                timeout_seconds=30
            )
        )
        
        # Simulate calls
        async def api_call():
            # Simulate API call
            import random
            if random.random() < 0.3:  # 30% failure rate
                raise Exception("API error")
            return "Success"
        
        # Make calls
        for i in range(20):
            try:
                result = await circuit.call(api_call)
                print(f"Call {i+1}: {result}")
            except CircuitBreakerError as e:
                print(f"Call {i+1}: Circuit open - {e}")
            except Exception as e:
                print(f"Call {i+1}: Failed - {e}")
            
            await asyncio.sleep(0.5)
        
        # Check metrics
        metrics = circuit.get_metrics()
        print("\nMetrics:")
        print(f"  Total calls: {metrics.total_calls}")
        print(f"  Successful: {metrics.successful_calls}")
        print(f"  Failed: {metrics.failed_calls}")
        print(f"  Rejected: {metrics.rejected_calls}")
        print(f"  Error rate: {metrics.error_rate*100:.1f}%")
        print(f"  State: {circuit.get_state().value}")
    
    asyncio.run(main())

# Made with Bob
