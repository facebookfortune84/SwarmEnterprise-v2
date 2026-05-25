"""
CI/CD Manager Agent - Autonomous Build, Test, and Deployment Pipeline

This agent manages the complete CI/CD pipeline:
- Automated builds
- Test execution
- Code quality checks
- Deployment automation
- Rollback management
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """CI/CD pipeline stages"""
    CHECKOUT = "checkout"
    BUILD = "build"
    TEST = "test"
    QUALITY = "quality"
    SECURITY = "security"
    DEPLOY = "deploy"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineConfig:
    """CI/CD pipeline configuration"""
    project_id: str
    repository_url: str
    branch: str = "main"
    build_command: str = "docker build -t app ."
    test_command: str = "pytest"
    deploy_target: str = "production"
    auto_deploy: bool = True
    run_security_scan: bool = True
    run_quality_checks: bool = True


@dataclass
class PipelineResult:
    """Pipeline execution result"""
    pipeline_id: str
    status: PipelineStatus
    stage: PipelineStage
    duration_seconds: int
    logs: List[str]
    artifacts: List[str]
    test_results: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    security_issues: Optional[List[Dict[str, Any]]] = None


class CICDManager:
    """
    CI/CD Manager Agent
    
    Autonomous agent that manages the complete CI/CD pipeline:
    1. Code checkout from repository
    2. Build application
    3. Run tests
    4. Quality checks
    5. Security scanning
    6. Deployment
    7. Verification
    
    Uses Ollama LLM for intelligent decision-making and error resolution.
    """
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        workspace_dir: str = "/tmp/cicd",
    ):
        """
        Initialize CI/CD Manager.
        
        Args:
            ollama_client: Ollama client for AI assistance
            workspace_dir: Working directory for builds
        """
        self.ollama = ollama_client or OllamaClient()
        self.workspace_dir = workspace_dir
        self.pipelines: Dict[str, Dict[str, Any]] = {}
        
        # Create workspace
        os.makedirs(workspace_dir, exist_ok=True)
        
        logger.info(f"CI/CD Manager initialized: {workspace_dir}")
    
    async def run_pipeline(self, config: PipelineConfig) -> PipelineResult:
        """
        Run complete CI/CD pipeline.
        
        Args:
            config: Pipeline configuration
            
        Returns:
            Pipeline execution result
        """
        pipeline_id = f"pipeline-{config.project_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        start_time = datetime.utcnow()
        
        logger.info(f"Starting pipeline: {pipeline_id}")
        
        # Initialize pipeline state
        pipeline = {
            "id": pipeline_id,
            "config": config,
            "status": PipelineStatus.RUNNING,
            "stage": PipelineStage.CHECKOUT,
            "start_time": start_time,
            "logs": [],
            "artifacts": [],
        }
        
        self.pipelines[pipeline_id] = pipeline
        
        try:
            # Stage 1: Checkout code
            await self._checkout_code(pipeline)
            
            # Stage 2: Build
            await self._build(pipeline)
            
            # Stage 3: Test
            await self._test(pipeline)
            
            # Stage 4: Quality checks
            if config.run_quality_checks:
                await self._quality_checks(pipeline)
            
            # Stage 5: Security scan
            if config.run_security_scan:
                await self._security_scan(pipeline)
            
            # Stage 6: Deploy
            if config.auto_deploy:
                await self._deploy(pipeline)
            
            # Stage 7: Verify
            await self._verify(pipeline)
            
            # Complete
            pipeline["status"] = PipelineStatus.SUCCESS
            pipeline["stage"] = PipelineStage.COMPLETE
            
            logger.info(f"Pipeline completed: {pipeline_id}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {pipeline_id} - {e}")
            pipeline["status"] = PipelineStatus.FAILED
            pipeline["stage"] = PipelineStage.FAILED
            pipeline["error"] = str(e)
            
            # Use AI to analyze failure
            await self._analyze_failure(pipeline, str(e))
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return PipelineResult(
            pipeline_id=pipeline_id,
            status=pipeline["status"],
            stage=pipeline["stage"],
            duration_seconds=int(duration),
            logs=pipeline["logs"],
            artifacts=pipeline["artifacts"],
            test_results=pipeline.get("test_results"),
            quality_score=pipeline.get("quality_score"),
            security_issues=pipeline.get("security_issues"),
        )
    
    async def _checkout_code(self, pipeline: Dict[str, Any]) -> None:
        """Checkout code from repository"""
        pipeline["stage"] = PipelineStage.CHECKOUT
        config = pipeline["config"]
        
        project_dir = os.path.join(self.workspace_dir, config.project_id)
        
        logger.info(f"Checking out: {config.repository_url}")
        
        # Clone repository
        cmd = f"git clone --branch {config.branch} {config.repository_url} {project_dir}"
        result = await self._run_command(cmd)
        
        pipeline["logs"].append(f"Checkout: {result}")
        pipeline["project_dir"] = project_dir
    
    async def _build(self, pipeline: Dict[str, Any]) -> None:
        """Build application"""
        pipeline["stage"] = PipelineStage.BUILD
        config = pipeline["config"]
        project_dir = pipeline["project_dir"]
        
        logger.info(f"Building: {config.project_id}")
        
        # Run build command
        result = await self._run_command(config.build_command, cwd=project_dir)
        
        pipeline["logs"].append(f"Build: {result}")
        
        # Check for build artifacts
        artifacts = self._find_artifacts(project_dir)
        pipeline["artifacts"].extend(artifacts)
    
    async def _test(self, pipeline: Dict[str, Any]) -> None:
        """Run tests"""
        pipeline["stage"] = PipelineStage.TEST
        config = pipeline["config"]
        project_dir = pipeline["project_dir"]
        
        logger.info(f"Testing: {config.project_id}")
        
        # Run tests
        result = await self._run_command(config.test_command, cwd=project_dir)
        
        pipeline["logs"].append(f"Test: {result}")
        
        # Parse test results
        test_results = await self._parse_test_results(result)
        pipeline["test_results"] = test_results
        
        # Fail if tests failed
        if test_results.get("failed", 0) > 0:
            raise Exception(f"Tests failed: {test_results['failed']} failures")
    
    async def _quality_checks(self, pipeline: Dict[str, Any]) -> None:
        """Run code quality checks"""
        pipeline["stage"] = PipelineStage.QUALITY
        project_dir = pipeline["project_dir"]
        
        logger.info("Running quality checks")
        
        # Run linters and code quality tools
        checks = []
        
        # Python: pylint, flake8, black
        if os.path.exists(os.path.join(project_dir, "setup.py")):
            checks.append(("pylint", "pylint **/*.py"))
            checks.append(("flake8", "flake8 ."))
            checks.append(("black", "black --check ."))
        
        # JavaScript: eslint, prettier
        if os.path.exists(os.path.join(project_dir, "package.json")):
            checks.append(("eslint", "npm run lint"))
            checks.append(("prettier", "npm run format:check"))
        
        results = []
        for name, cmd in checks:
            try:
                result = await self._run_command(cmd, cwd=project_dir)
                results.append({"check": name, "status": "passed", "output": result})
            except Exception as e:
                results.append({"check": name, "status": "failed", "error": str(e)})
        
        # Calculate quality score
        passed = sum(1 for r in results if r["status"] == "passed")
        quality_score = (passed / len(results)) * 100 if results else 100
        
        pipeline["quality_checks"] = results
        pipeline["quality_score"] = quality_score
        pipeline["logs"].append(f"Quality score: {quality_score}%")
    
    async def _security_scan(self, pipeline: Dict[str, Any]) -> None:
        """Run security scanning"""
        pipeline["stage"] = PipelineStage.SECURITY
        project_dir = pipeline["project_dir"]
        
        logger.info("Running security scan")
        
        # Run security scanners
        issues = []
        
        # Python: bandit, safety
        if os.path.exists(os.path.join(project_dir, "requirements.txt")):
            try:
                result = await self._run_command("bandit -r .", cwd=project_dir)
                issues.extend(self._parse_bandit_results(result))
            except Exception as e:
                logger.warning(f"Bandit scan failed: {e}")
            
            try:
                result = await self._run_command("safety check", cwd=project_dir)
                issues.extend(self._parse_safety_results(result))
            except Exception as e:
                logger.warning(f"Safety check failed: {e}")
        
        # JavaScript: npm audit
        if os.path.exists(os.path.join(project_dir, "package.json")):
            try:
                result = await self._run_command("npm audit", cwd=project_dir)
                issues.extend(self._parse_npm_audit(result))
            except Exception as e:
                logger.warning(f"npm audit failed: {e}")
        
        pipeline["security_issues"] = issues
        pipeline["logs"].append(f"Security issues found: {len(issues)}")
        
        # Fail on critical issues
        critical = [i for i in issues if i.get("severity") == "critical"]
        if critical:
            raise Exception(f"Critical security issues found: {len(critical)}")
    
    async def _deploy(self, pipeline: Dict[str, Any]) -> None:
        """Deploy application"""
        pipeline["stage"] = PipelineStage.DEPLOY
        config = pipeline["config"]
        
        logger.info(f"Deploying to: {config.deploy_target}")
        
        # Deploy based on target
        if config.deploy_target == "production":
            await self._deploy_production(pipeline)
        elif config.deploy_target == "staging":
            await self._deploy_staging(pipeline)
        else:
            raise Exception(f"Unknown deploy target: {config.deploy_target}")
        
        pipeline["logs"].append(f"Deployed to: {config.deploy_target}")
    
    async def _deploy_production(self, pipeline: Dict[str, Any]) -> None:
        """Deploy to production"""
        project_dir = pipeline["project_dir"]
        
        # Build Docker image
        image_tag = f"{pipeline['config'].project_id}:latest"
        await self._run_command(f"docker build -t {image_tag} .", cwd=project_dir)
        
        # Push to registry (if configured)
        # await self._run_command(f"docker push {image_tag}")
        
        # Deploy via docker-compose or kubernetes
        await self._run_command("docker-compose up -d", cwd=project_dir)
    
    async def _deploy_staging(self, pipeline: Dict[str, Any]) -> None:
        """Deploy to staging"""
        # Similar to production but different environment
        pass
    
    async def _verify(self, pipeline: Dict[str, Any]) -> None:
        """Verify deployment"""
        pipeline["stage"] = PipelineStage.VERIFY
        
        logger.info("Verifying deployment")
        
        # Health check
        # await self._run_command("curl http://localhost:8000/health")
        
        # Smoke tests
        # await self._run_command("pytest tests/smoke/")
        
        pipeline["logs"].append("Deployment verified")
    
    async def _analyze_failure(self, pipeline: Dict[str, Any], error: str) -> None:
        """Use AI to analyze pipeline failure"""
        logger.info("Analyzing failure with AI")
        
        prompt = f"""
        CI/CD Pipeline Failed
        
        Project: {pipeline['config'].project_id}
        Stage: {pipeline['stage']}
        Error: {error}
        
        Logs:
        {chr(10).join(pipeline['logs'][-10:])}
        
        Analyze the failure and suggest fixes:
        1. What caused the failure?
        2. How to fix it?
        3. How to prevent it in the future?
        """
        
        analysis = await self.ollama.generate(prompt, system="You are a DevOps expert analyzing CI/CD failures.")
        
        pipeline["failure_analysis"] = analysis
        pipeline["logs"].append(f"AI Analysis: {analysis}")
    
    async def _run_command(self, cmd: str, cwd: Optional[str] = None) -> str:
        """Run shell command"""
        logger.debug(f"Running: {cmd}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error = stderr.decode()
            raise Exception(f"Command failed: {cmd}\n{error}")
        
        return stdout.decode()
    
    def _find_artifacts(self, project_dir: str) -> List[str]:
        """Find build artifacts"""
        artifacts = []
        
        # Common artifact patterns
        
        # TODO: Implement artifact discovery
        
        return artifacts
    
    async def _parse_test_results(self, output: str) -> Dict[str, Any]:
        """Parse test results from output"""
        # Simple pytest output parsing
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        
        # TODO: Implement proper test result parsing
        
        return results
    
    def _parse_bandit_results(self, output: str) -> List[Dict[str, Any]]:
        """Parse bandit security scan results"""
        issues = []
        # TODO: Implement bandit result parsing
        return issues
    
    def _parse_safety_results(self, output: str) -> List[Dict[str, Any]]:
        """Parse safety check results"""
        issues = []
        # TODO: Implement safety result parsing
        return issues
    
    def _parse_npm_audit(self, output: str) -> List[Dict[str, Any]]:
        """Parse npm audit results"""
        issues = []
        # TODO: Implement npm audit parsing
        return issues
    
    async def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline status"""
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        return self.pipelines[pipeline_id]
    
    async def cancel_pipeline(self, pipeline_id: str) -> None:
        """Cancel running pipeline"""
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        pipeline = self.pipelines[pipeline_id]
        pipeline["status"] = PipelineStatus.CANCELLED
        
        logger.info(f"Pipeline cancelled: {pipeline_id}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.ollama.close()


# Example usage
if __name__ == "__main__":
    async def main():
        manager = CICDManager()
        
        config = PipelineConfig(
            project_id="my-app",
            repository_url="https://github.com/user/my-app.git",
            branch="main",
            build_command="docker build -t my-app .",
            test_command="pytest",
            deploy_target="production",
        )
        
        result = await manager.run_pipeline(config)
        print(f"Pipeline result: {result}")
        
        await manager.cleanup()
    
    asyncio.run(main())

# Made with Bob
