# DevOps Agent Team

Autonomous DevOps agents for CI/CD, deployment, security, performance monitoring, and infrastructure management.

## Agents

### 1. CI/CD Manager (`ci_cd_manager.py`)
**Purpose:** Automated build, test, and deployment pipelines

**Capabilities:**
- 7-stage pipeline execution (Checkout → Build → Test → Quality → Security → Deploy → Verify)
- Parallel test execution
- Code quality checks (linters, formatters)
- Security scanning integration
- AI-powered failure analysis
- Deployment automation
- Health verification

**Key Methods:**
- `run_pipeline()` - Execute complete CI/CD pipeline
- `_analyze_failure()` - AI-powered failure diagnosis and recommendations

**Usage:**
```python
from agents.devops.ci_cd_manager import CICDManager

manager = CICDManager()
result = await manager.run_pipeline(
    repo_url="https://github.com/user/repo",
    branch="main",
    deployment_id="deploy-123"
)
```

### 2. Deployment Agent (`deployment_agent.py`)
**Purpose:** Advanced deployment strategies with zero-downtime

**Capabilities:**
- Blue-green deployment
- Canary deployment with gradual rollout
- Rolling updates
- Automatic rollback on failure
- Health monitoring
- Traffic shifting

**Key Methods:**
- `deploy()` - Execute deployment with specified strategy
- `_blue_green_deployment()` - Zero-downtime deployment
- `_canary_deployment()` - Gradual rollout with monitoring
- `_rollback()` - Automatic rollback

**Usage:**
```python
from agents.devops.deployment_agent import DeploymentAgent, DeploymentStrategy

agent = DeploymentAgent()
result = await agent.deploy(
    deployment_id="deploy-123",
    strategy=DeploymentStrategy.BLUE_GREEN,
    config={
        "image": "myapp:v2.0",
        "replicas": 3,
        "health_check_url": "/health"
    }
)
```

### 3. Security Scanner (`security_scanner.py`)
**Purpose:** Comprehensive security scanning and vulnerability detection

**Capabilities:**
- Dependency vulnerability scanning (safety, npm audit)
- Code security analysis (bandit, semgrep)
- Container vulnerability scanning (trivy, grype)
- Secret detection (gitleaks, trufflehog)
- Compliance checks (CIS benchmarks)
- AI-powered remediation guidance

**Key Methods:**
- `scan()` - Perform comprehensive security scan
- `_generate_remediation()` - AI-powered fix recommendations

**Usage:**
```python
from agents.devops.security_scanner import SecurityScanner

scanner = SecurityScanner()
result = await scanner.scan(
    target="/path/to/project",
    scan_types=["dependencies", "code", "secrets"]
)
```

### 4. Performance Monitor (`performance_monitor.py`)
**Purpose:** Real-time performance monitoring and optimization

**Capabilities:**
- Real-time metric collection (CPU, memory, disk, network, latency)
- Threshold-based alerting
- Anomaly detection using statistical analysis
- Bottleneck identification
- Performance scoring
- AI-powered optimization recommendations
- Auto-scaling triggers

**Key Methods:**
- `start_monitoring()` - Start continuous monitoring
- `generate_report()` - Generate performance analysis report
- `_detect_anomalies()` - Statistical anomaly detection

**Usage:**
```python
from agents.devops.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor(collection_interval=60)
await monitor.start_monitoring(deployment_id="deploy-123")

# Generate report
report = await monitor.generate_report(period_hours=24)
```

### 5. Infrastructure Agent (`infrastructure_agent.py`)
**Purpose:** Resource provisioning and auto-scaling

**Capabilities:**
- Resource provisioning (VMs, containers, databases, storage, network)
- Auto-scaling based on metrics
- Cost optimization analysis
- Capacity planning
- Resource utilization monitoring
- AI-powered recommendations

**Key Methods:**
- `provision_resource()` - Provision new infrastructure resource
- `create_scaling_policy()` - Create auto-scaling policy
- `start_auto_scaling()` - Start auto-scaling monitoring
- `optimize_costs()` - Analyze and optimize costs
- `generate_capacity_plan()` - Generate capacity forecast

**Usage:**
```python
from agents.devops.infrastructure_agent import InfrastructureAgent, ResourceType

agent = InfrastructureAgent()

# Provision resource
resource = await agent.provision_resource(
    resource_type=ResourceType.VM,
    name="app-server-1",
    specs={"cpu": 4, "memory_gb": 16, "disk_gb": 100}
)

# Create scaling policy
policy = await agent.create_scaling_policy(
    resource_type=ResourceType.CONTAINER,
    metric="cpu_usage",
    threshold_up=70.0,
    threshold_down=30.0,
    min_instances=2,
    max_instances=10
)

# Start auto-scaling
await agent.start_auto_scaling()
```

## Integration

### With Backend Services

All agents integrate with:
- **Ollama LLM Client** - AI-powered analysis and recommendations
- **Deployment Service** - Deployment orchestration
- **Monitoring Stack** - Prometheus, Grafana, Loki
- **Storage Service** - Artifact storage

### With CI/CD Pipeline

```python
# Complete CI/CD workflow
from agents.devops.ci_cd_manager import CICDManager
from agents.devops.deployment_agent import DeploymentAgent
from agents.devops.security_scanner import SecurityScanner

# 1. Run CI/CD pipeline
ci_cd = CICDManager()
pipeline_result = await ci_cd.run_pipeline(
    repo_url="https://github.com/user/repo",
    branch="main",
    deployment_id="deploy-123"
)

# 2. Security scan
scanner = SecurityScanner()
scan_result = await scanner.scan(
    target="/tmp/repo",
    scan_types=["dependencies", "code", "container", "secrets"]
)

# 3. Deploy if all checks pass
if pipeline_result["success"] and scan_result["passed"]:
    deployer = DeploymentAgent()
    deploy_result = await deployer.deploy(
        deployment_id="deploy-123",
        strategy=DeploymentStrategy.BLUE_GREEN,
        config={"image": "myapp:latest"}
    )
```

## Configuration

### Environment Variables

```bash
# Ollama LLM
OLLAMA_URL=http://192.168.1.100:11434
OLLAMA_MODEL=llama3

# Monitoring
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_URL=http://grafana:3000

# Docker
DOCKER_HOST=unix:///var/run/docker.sock

# Hyper-V (Windows Server)
HYPERV_HOST=192.168.1.200
HYPERV_USER=Administrator
```

### Thresholds

Default performance thresholds:
- CPU: Warning 70%, Critical 90%
- Memory: Warning 75%, Critical 90%
- Disk: Warning 80%, Critical 95%
- Latency: Warning 500ms, Critical 1000ms
- Error Rate: Warning 1%, Critical 5%

## Monitoring

All agents emit metrics to Prometheus:
- `devops_pipeline_duration_seconds` - CI/CD pipeline duration
- `devops_deployment_success_total` - Successful deployments
- `devops_security_vulnerabilities_total` - Vulnerabilities found
- `devops_performance_score` - Performance score (0-100)
- `devops_resource_cost_per_hour` - Infrastructure cost

## Alerting

Agents send alerts to:
- Slack (via webhooks)
- Email (via SMTP)
- PagerDuty (for critical issues)
- Grafana (for visualization)

## Self-Hosted Setup

All agents run on self-hosted infrastructure:
- **Laptop** - Ollama LLM inference
- **Windows Server 2025** - Hyper-V VMs
- **WSL2** - Docker containers
- **MinIO** - S3-compatible storage
- **PostgreSQL** - Database
- **Redis** - Cache and queues

Zero cloud costs, complete control.

## Testing

```bash
# Run agent tests
pytest tests/unit/agents/devops/ -v

# Run integration tests
pytest tests/integration/test_devops_workflow.py -v

# Run with coverage
pytest tests/unit/agents/devops/ --cov=agents.devops --cov-report=html
```

## Troubleshooting

### Common Issues

1. **Ollama connection failed**
   - Ensure Ollama is running: `ollama serve`
   - Check OLLAMA_URL environment variable
   - Verify network connectivity

2. **Docker connection failed**
   - Check Docker daemon is running
   - Verify DOCKER_HOST environment variable
   - Check user permissions

3. **Hyper-V provisioning failed**
   - Verify Hyper-V is enabled on Windows Server
   - Check PowerShell remoting is configured
   - Verify credentials

4. **Performance metrics not collected**
   - Check Prometheus is running
   - Verify metric exporters are configured
   - Check firewall rules

## Future Enhancements

- [ ] Kubernetes support
- [ ] Multi-cloud provisioning
- [ ] Advanced ML-based anomaly detection
- [ ] Automated incident response
- [ ] Cost prediction models
- [ ] Infrastructure as Code generation
- [ ] Compliance automation (SOC2, HIPAA, PCI-DSS)

## License

MIT License - See LICENSE file for details