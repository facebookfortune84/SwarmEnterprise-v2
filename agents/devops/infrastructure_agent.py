"""
Infrastructure Agent - Resource Provisioning and Auto-Scaling

Manages infrastructure resources:
- Resource provisioning
- Auto-scaling
- Cost optimization
- Capacity planning
- Infrastructure as Code
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Infrastructure resource types"""
    VM = "vm"
    CONTAINER = "container"
    DATABASE = "database"
    STORAGE = "storage"
    NETWORK = "network"


class ScalingAction(str, Enum):
    """Scaling actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_OUT = "scale_out"
    SCALE_IN = "scale_in"


class ResourceStatus(str, Enum):
    """Resource status"""
    PROVISIONING = "provisioning"
    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class Resource:
    """Infrastructure resource"""
    resource_id: str
    resource_type: ResourceType
    name: str
    status: ResourceStatus
    specs: Dict[str, Any]
    cost_per_hour: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ScalingPolicy:
    """Auto-scaling policy"""
    policy_id: str
    resource_type: ResourceType
    metric: str
    threshold_up: float
    threshold_down: float
    cooldown_minutes: int
    min_instances: int
    max_instances: int
    enabled: bool


@dataclass
class ScalingEvent:
    """Scaling event record"""
    event_id: str
    resource_id: str
    action: ScalingAction
    reason: str
    timestamp: datetime
    old_capacity: int
    new_capacity: int
    success: bool


class InfrastructureAgent:
    """
    Autonomous infrastructure management agent.
    
    Capabilities:
    - Resource provisioning
    - Auto-scaling based on metrics
    - Cost optimization
    - Capacity planning
    - Infrastructure as Code generation
    - AI-powered recommendations
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        check_interval: int = 300,  # 5 minutes
    ):
        self.ollama = ollama_client or OllamaClient()
        self.check_interval = check_interval
        self.resources: Dict[str, Resource] = {}
        self.policies: Dict[str, ScalingPolicy] = {}
        self.scaling_events: List[ScalingEvent] = []
        self.monitoring = False
        
        logger.info("Infrastructure Agent initialized")
    
    async def provision_resource(
        self,
        resource_type: ResourceType,
        name: str,
        specs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Resource:
        """Provision new infrastructure resource"""
        logger.info(f"Provisioning {resource_type}: {name}")
        
        resource_id = f"{resource_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate cost
        cost_per_hour = self._calculate_cost(resource_type, specs)
        
        # Create resource
        resource = Resource(
            resource_id=resource_id,
            resource_type=resource_type,
            name=name,
            status=ResourceStatus.PROVISIONING,
            specs=specs,
            cost_per_hour=cost_per_hour,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        
        # Provision based on type
        if resource_type == ResourceType.VM:
            await self._provision_vm(resource)
        elif resource_type == ResourceType.CONTAINER:
            await self._provision_container(resource)
        elif resource_type == ResourceType.DATABASE:
            await self._provision_database(resource)
        elif resource_type == ResourceType.STORAGE:
            await self._provision_storage(resource)
        elif resource_type == ResourceType.NETWORK:
            await self._provision_network(resource)
        
        resource.status = ResourceStatus.RUNNING
        self.resources[resource_id] = resource
        
        logger.info(f"Resource provisioned: {resource_id}")
        return resource
    
    async def terminate_resource(self, resource_id: str) -> bool:
        """Terminate infrastructure resource"""
        if resource_id not in self.resources:
            logger.error(f"Resource not found: {resource_id}")
            return False
        
        resource = self.resources[resource_id]
        logger.info(f"Terminating resource: {resource_id}")
        
        # Terminate based on type
        if resource.resource_type == ResourceType.VM:
            await self._terminate_vm(resource)
        elif resource.resource_type == ResourceType.CONTAINER:
            await self._terminate_container(resource)
        elif resource.resource_type == ResourceType.DATABASE:
            await self._terminate_database(resource)
        elif resource.resource_type == ResourceType.STORAGE:
            await self._terminate_storage(resource)
        elif resource.resource_type == ResourceType.NETWORK:
            await self._terminate_network(resource)
        
        resource.status = ResourceStatus.TERMINATED
        logger.info(f"Resource terminated: {resource_id}")
        return True
    
    async def create_scaling_policy(
        self,
        resource_type: ResourceType,
        metric: str,
        threshold_up: float,
        threshold_down: float,
        min_instances: int = 1,
        max_instances: int = 10,
        cooldown_minutes: int = 5,
    ) -> ScalingPolicy:
        """Create auto-scaling policy"""
        policy_id = f"policy-{resource_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        policy = ScalingPolicy(
            policy_id=policy_id,
            resource_type=resource_type,
            metric=metric,
            threshold_up=threshold_up,
            threshold_down=threshold_down,
            cooldown_minutes=cooldown_minutes,
            min_instances=min_instances,
            max_instances=max_instances,
            enabled=True,
        )
        
        self.policies[policy_id] = policy
        logger.info(f"Scaling policy created: {policy_id}")
        return policy
    
    async def start_auto_scaling(self) -> None:
        """Start auto-scaling monitoring"""
        self.monitoring = True
        logger.info("Auto-scaling monitoring started")
        
        while self.monitoring:
            try:
                # Check all policies
                for policy in self.policies.values():
                    if policy.enabled:
                        await self._check_scaling_policy(policy)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop_auto_scaling(self) -> None:
        """Stop auto-scaling monitoring"""
        self.monitoring = False
        logger.info("Auto-scaling monitoring stopped")
    
    async def _check_scaling_policy(self, policy: ScalingPolicy) -> None:
        """Check if scaling action is needed"""
        # Get resources of this type
        resources = [
            r for r in self.resources.values()
            if r.resource_type == policy.resource_type
            and r.status == ResourceStatus.RUNNING
        ]
        
        if not resources:
            return
        
        # Get current metric value
        metric_value = await self._get_metric_value(policy.metric, resources)
        
        # Check if scaling is needed
        current_count = len(resources)
        
        if metric_value > policy.threshold_up and current_count < policy.max_instances:
            # Scale up/out
            action = ScalingAction.SCALE_OUT if policy.resource_type in [ResourceType.CONTAINER, ResourceType.VM] else ScalingAction.SCALE_UP
            await self._execute_scaling(policy, resources, action, metric_value)
            
        elif metric_value < policy.threshold_down and current_count > policy.min_instances:
            # Scale down/in
            action = ScalingAction.SCALE_IN if policy.resource_type in [ResourceType.CONTAINER, ResourceType.VM] else ScalingAction.SCALE_DOWN
            await self._execute_scaling(policy, resources, action, metric_value)
    
    async def _execute_scaling(
        self,
        policy: ScalingPolicy,
        resources: List[Resource],
        action: ScalingAction,
        metric_value: float,
    ) -> None:
        """Execute scaling action"""
        # Check cooldown
        recent_events = [
            e for e in self.scaling_events
            if e.resource_id in [r.resource_id for r in resources]
            and (datetime.utcnow() - e.timestamp).total_seconds() < policy.cooldown_minutes * 60
        ]
        
        if recent_events:
            logger.info(f"Scaling cooldown active for {policy.policy_id}")
            return
        
        old_capacity = len(resources)
        new_capacity = old_capacity
        success = False
        
        try:
            if action in [ScalingAction.SCALE_OUT, ScalingAction.SCALE_UP]:
                # Add resource
                new_resource = await self.provision_resource(
                    resource_type=policy.resource_type,
                    name=f"{policy.resource_type}-auto-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    specs=resources[0].specs,  # Use same specs as existing
                    metadata={"auto_scaled": True, "policy_id": policy.policy_id},
                )
                new_capacity = old_capacity + 1
                success = True
                logger.info(f"Scaled out: {new_resource.resource_id}")
                
            elif action in [ScalingAction.SCALE_IN, ScalingAction.SCALE_DOWN]:
                # Remove resource (prefer auto-scaled ones)
                auto_scaled = [r for r in resources if r.metadata.get("auto_scaled")]
                resource_to_remove = auto_scaled[0] if auto_scaled else resources[-1]
                
                await self.terminate_resource(resource_to_remove.resource_id)
                new_capacity = old_capacity - 1
                success = True
                logger.info(f"Scaled in: {resource_to_remove.resource_id}")
            
            # Record event
            event = ScalingEvent(
                event_id=f"event-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                resource_id=resources[0].resource_id,
                action=action,
                reason=f"{policy.metric}={metric_value:.2f} (threshold: {policy.threshold_up if 'UP' in action.name else policy.threshold_down})",
                timestamp=datetime.utcnow(),
                old_capacity=old_capacity,
                new_capacity=new_capacity,
                success=success,
            )
            self.scaling_events.append(event)
            
        except Exception as e:
            logger.error(f"Scaling failed: {e}")
            success = False
    
    async def optimize_costs(self) -> Dict[str, Any]:
        """Analyze and optimize infrastructure costs"""
        logger.info("Analyzing infrastructure costs")
        
        # Calculate current costs
        total_cost = sum(r.cost_per_hour for r in self.resources.values() if r.status == ResourceStatus.RUNNING)
        
        # Identify optimization opportunities
        opportunities = []
        
        # Check for underutilized resources
        for resource in self.resources.values():
            if resource.status != ResourceStatus.RUNNING:
                continue
            
            utilization = await self._get_resource_utilization(resource)
            
            if utilization < 20:
                opportunities.append({
                    "resource_id": resource.resource_id,
                    "type": "underutilized",
                    "utilization": utilization,
                    "potential_savings": resource.cost_per_hour * 0.8,
                    "recommendation": "Consider downsizing or terminating",
                })
        
        # Check for oversized resources
        for resource in self.resources.values():
            if resource.status != ResourceStatus.RUNNING:
                continue
            
            utilization = await self._get_resource_utilization(resource)
            
            if utilization > 90:
                opportunities.append({
                    "resource_id": resource.resource_id,
                    "type": "oversized",
                    "utilization": utilization,
                    "potential_cost": resource.cost_per_hour * 0.5,
                    "recommendation": "Consider upgrading to prevent performance issues",
                })
        
        # Generate AI recommendations
        recommendations = await self._generate_cost_recommendations(
            total_cost,
            opportunities
        )
        
        return {
            "total_cost_per_hour": total_cost,
            "total_cost_per_month": total_cost * 24 * 30,
            "opportunities": opportunities,
            "potential_savings": sum(o.get("potential_savings", 0) for o in opportunities),
            "recommendations": recommendations,
        }
    
    async def _generate_cost_recommendations(
        self,
        total_cost: float,
        opportunities: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate AI-powered cost optimization recommendations"""
        if not opportunities:
            return ["Infrastructure is well-optimized. No immediate cost savings identified."]
        
        prompt = f"""
        Infrastructure Cost Analysis:
        
        Total Cost: ${total_cost:.2f}/hour (${total_cost * 24 * 30:.2f}/month)
        Optimization Opportunities: {len(opportunities)}
        
        Opportunities:
        {chr(10).join([f"- {o['resource_id']}: {o['type']} ({o.get('utilization', 0):.1f}% utilization)" for o in opportunities[:5]])}
        
        Provide specific cost optimization recommendations:
        1. Immediate actions to reduce costs
        2. Resource rightsizing strategies
        3. Long-term cost optimization
        """
        
        response = await self.ollama.generate(
            prompt,
            system="You are an infrastructure cost optimization expert."
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    async def generate_capacity_plan(
        self,
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """Generate capacity planning forecast"""
        logger.info(f"Generating {forecast_days}-day capacity plan")
        
        # Analyze historical scaling events
        recent_events = [
            e for e in self.scaling_events
            if (datetime.utcnow() - e.timestamp).days <= 30
        ]
        
        # Calculate growth rate
        if len(recent_events) >= 2:
            scale_out_events = [e for e in recent_events if e.action in [ScalingAction.SCALE_OUT, ScalingAction.SCALE_UP]]
            growth_rate = len(scale_out_events) / 30  # events per day
        else:
            growth_rate = 0
        
        # Forecast capacity needs
        current_capacity = len([r for r in self.resources.values() if r.status == ResourceStatus.RUNNING])
        forecasted_capacity = int(current_capacity + (growth_rate * forecast_days))
        
        # Generate recommendations
        recommendations = await self._generate_capacity_recommendations(
            current_capacity,
            forecasted_capacity,
            growth_rate
        )
        
        return {
            "current_capacity": current_capacity,
            "forecasted_capacity": forecasted_capacity,
            "growth_rate_per_day": growth_rate,
            "forecast_days": forecast_days,
            "recommendations": recommendations,
        }
    
    async def _generate_capacity_recommendations(
        self,
        current: int,
        forecasted: int,
        growth_rate: float
    ) -> List[str]:
        """Generate capacity planning recommendations"""
        prompt = f"""
        Capacity Planning Analysis:
        
        Current Capacity: {current} resources
        Forecasted Capacity: {forecasted} resources (30 days)
        Growth Rate: {growth_rate:.2f} resources/day
        
        Provide capacity planning recommendations:
        1. Resource provisioning strategy
        2. Scaling thresholds
        3. Budget planning
        """
        
        response = await self.ollama.generate(
            prompt,
            system="You are a capacity planning expert."
        )
        
        return [line.strip() for line in response.split('\n') if line.strip()]
    
    # Resource provisioning methods (TODO: Implement actual provisioning)
    
    async def _provision_vm(self, resource: Resource) -> None:
        """Provision virtual machine"""
        # TODO: Implement Hyper-V VM provisioning
        logger.info(f"Provisioning VM: {resource.name}")
        await asyncio.sleep(1)
    
    async def _provision_container(self, resource: Resource) -> None:
        """Provision container"""
        # TODO: Implement Docker container provisioning
        logger.info(f"Provisioning container: {resource.name}")
        await asyncio.sleep(1)
    
    async def _provision_database(self, resource: Resource) -> None:
        """Provision database"""
        # TODO: Implement database provisioning
        logger.info(f"Provisioning database: {resource.name}")
        await asyncio.sleep(1)
    
    async def _provision_storage(self, resource: Resource) -> None:
        """Provision storage"""
        # TODO: Implement storage provisioning
        logger.info(f"Provisioning storage: {resource.name}")
        await asyncio.sleep(1)
    
    async def _provision_network(self, resource: Resource) -> None:
        """Provision network"""
        # TODO: Implement network provisioning
        logger.info(f"Provisioning network: {resource.name}")
        await asyncio.sleep(1)
    
    # Resource termination methods
    
    async def _terminate_vm(self, resource: Resource) -> None:
        """Terminate virtual machine"""
        # TODO: Implement VM termination
        logger.info(f"Terminating VM: {resource.name}")
        await asyncio.sleep(1)
    
    async def _terminate_container(self, resource: Resource) -> None:
        """Terminate container"""
        # TODO: Implement container termination
        logger.info(f"Terminating container: {resource.name}")
        await asyncio.sleep(1)
    
    async def _terminate_database(self, resource: Resource) -> None:
        """Terminate database"""
        # TODO: Implement database termination
        logger.info(f"Terminating database: {resource.name}")
        await asyncio.sleep(1)
    
    async def _terminate_storage(self, resource: Resource) -> None:
        """Terminate storage"""
        # TODO: Implement storage termination
        logger.info(f"Terminating storage: {resource.name}")
        await asyncio.sleep(1)
    
    async def _terminate_network(self, resource: Resource) -> None:
        """Terminate network"""
        # TODO: Implement network termination
        logger.info(f"Terminating network: {resource.name}")
        await asyncio.sleep(1)
    
    # Helper methods
    
    def _calculate_cost(self, resource_type: ResourceType, specs: Dict[str, Any]) -> float:
        """Calculate resource cost per hour"""
        # Self-hosted costs are minimal (electricity, hardware depreciation)
        base_costs = {
            ResourceType.VM: 0.05,  # $0.05/hour
            ResourceType.CONTAINER: 0.01,  # $0.01/hour
            ResourceType.DATABASE: 0.03,  # $0.03/hour
            ResourceType.STORAGE: 0.001,  # $0.001/hour per GB
            ResourceType.NETWORK: 0.005,  # $0.005/hour
        }
        
        base_cost = base_costs.get(resource_type, 0.01)
        
        # Adjust based on specs
        if resource_type == ResourceType.STORAGE:
            storage_gb = specs.get("size_gb", 100)
            return base_cost * storage_gb
        
        return base_cost
    
    async def _get_metric_value(self, metric: str, resources: List[Resource]) -> float:
        """Get current metric value"""
        # TODO: Implement actual metric collection
        return 50.0
    
    async def _get_resource_utilization(self, resource: Resource) -> float:
        """Get resource utilization percentage"""
        # TODO: Implement actual utilization monitoring
        return 45.0
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop_auto_scaling()
        await self.ollama.close()

# Made with Bob
