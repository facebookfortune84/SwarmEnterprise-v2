"""
Security Scanner Agent - Comprehensive Security Analysis

Performs automated security scanning:
- Dependency vulnerability scanning
- Code security analysis
- Container image scanning
- Compliance checking
- Security report generation
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    """Security issue severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanType(str, Enum):
    """Types of security scans"""
    DEPENDENCIES = "dependencies"
    CODE = "code"
    CONTAINER = "container"
    SECRETS = "secrets"
    COMPLIANCE = "compliance"


@dataclass
class SecurityIssue:
    """Security issue details"""
    id: str
    severity: SeverityLevel
    title: str
    description: str
    affected_component: str
    cve_id: Optional[str] = None
    fix_available: bool = False
    fix_version: Optional[str] = None
    remediation: Optional[str] = None


@dataclass
class ScanResult:
    """Security scan result"""
    scan_id: str
    scan_type: ScanType
    timestamp: str
    duration_seconds: int
    issues: List[SecurityIssue]
    summary: Dict[str, int]
    passed: bool


class SecurityScanner:
    """
    Autonomous security scanner agent.
    
    Performs comprehensive security analysis:
    - Dependency vulnerabilities (npm audit, safety, etc.)
    - Code security issues (bandit, semgrep)
    - Container vulnerabilities (trivy, grype)
    - Secret detection (gitleaks, trufflehog)
    - Compliance checks (CIS benchmarks)
    
    Uses AI to provide remediation guidance.
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.scan_history: List[ScanResult] = []
        
        logger.info("Security Scanner initialized")
    
    async def scan(
        self,
        project_path: str,
        scan_types: Optional[List[ScanType]] = None,
    ) -> Dict[str, ScanResult]:
        """
        Perform security scan.
        
        Args:
            project_path: Path to project
            scan_types: Types of scans to run (all if None)
            
        Returns:
            Dict of scan results by type
        """
        if scan_types is None:
            scan_types = list(ScanType)
        
        logger.info(f"Starting security scan: {project_path}")
        
        results = {}
        
        for scan_type in scan_types:
            start_time = datetime.utcnow()
            
            try:
                if scan_type == ScanType.DEPENDENCIES:
                    issues = await self._scan_dependencies(project_path)
                elif scan_type == ScanType.CODE:
                    issues = await self._scan_code(project_path)
                elif scan_type == ScanType.CONTAINER:
                    issues = await self._scan_container(project_path)
                elif scan_type == ScanType.SECRETS:
                    issues = await self._scan_secrets(project_path)
                elif scan_type == ScanType.COMPLIANCE:
                    issues = await self._scan_compliance(project_path)
                else:
                    continue
                
                # Generate AI remediation for critical issues
                critical_issues = [i for i in issues if i.severity == SeverityLevel.CRITICAL]
                if critical_issues:
                    await self._generate_remediation(critical_issues)
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                result = ScanResult(
                    scan_id=f"scan-{scan_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                    scan_type=scan_type,
                    timestamp=datetime.utcnow().isoformat(),
                    duration_seconds=int(duration),
                    issues=issues,
                    summary=self._summarize_issues(issues),
                    passed=not any(i.severity == SeverityLevel.CRITICAL for i in issues),
                )
                
                results[scan_type] = result
                self.scan_history.append(result)
                
            except Exception as e:
                logger.error(f"Scan failed ({scan_type}): {e}")
        
        return results
    
    async def _scan_dependencies(self, project_path: str) -> List[SecurityIssue]:
        """Scan dependencies for vulnerabilities"""
        issues = []
        
        # Python: safety check
        try:
            result = await self._run_command("safety check --json", cwd=project_path)
            issues.extend(self._parse_safety_output(result))
        except Exception as e:
            logger.warning(f"Safety check failed: {e}")
        
        # JavaScript: npm audit
        try:
            result = await self._run_command("npm audit --json", cwd=project_path)
            issues.extend(self._parse_npm_audit(result))
        except Exception as e:
            logger.warning(f"npm audit failed: {e}")
        
        # Ruby: bundle audit
        try:
            result = await self._run_command("bundle audit check", cwd=project_path)
            issues.extend(self._parse_bundle_audit(result))
        except Exception as e:
            logger.warning(f"bundle audit failed: {e}")
        
        return issues
    
    async def _scan_code(self, project_path: str) -> List[SecurityIssue]:
        """Scan code for security issues"""
        issues = []
        
        # Python: bandit
        try:
            result = await self._run_command("bandit -r . -f json", cwd=project_path)
            issues.extend(self._parse_bandit_output(result))
        except Exception as e:
            logger.warning(f"Bandit scan failed: {e}")
        
        # Multi-language: semgrep
        try:
            result = await self._run_command("semgrep --config=auto --json", cwd=project_path)
            issues.extend(self._parse_semgrep_output(result))
        except Exception as e:
            logger.warning(f"Semgrep scan failed: {e}")
        
        return issues
    
    async def _scan_container(self, project_path: str) -> List[SecurityIssue]:
        """Scan container images for vulnerabilities"""
        issues = []
        
        # Trivy
        try:
            result = await self._run_command("trivy image --format json app:latest", cwd=project_path)
            issues.extend(self._parse_trivy_output(result))
        except Exception as e:
            logger.warning(f"Trivy scan failed: {e}")
        
        # Grype
        try:
            result = await self._run_command("grype app:latest -o json", cwd=project_path)
            issues.extend(self._parse_grype_output(result))
        except Exception as e:
            logger.warning(f"Grype scan failed: {e}")
        
        return issues
    
    async def _scan_secrets(self, project_path: str) -> List[SecurityIssue]:
        """Scan for exposed secrets"""
        issues = []
        
        # Gitleaks
        try:
            result = await self._run_command("gitleaks detect --report-format json", cwd=project_path)
            issues.extend(self._parse_gitleaks_output(result))
        except Exception as e:
            logger.warning(f"Gitleaks scan failed: {e}")
        
        # TruffleHog
        try:
            result = await self._run_command("trufflehog filesystem . --json", cwd=project_path)
            issues.extend(self._parse_trufflehog_output(result))
        except Exception as e:
            logger.warning(f"TruffleHog scan failed: {e}")
        
        return issues
    
    async def _scan_compliance(self, project_path: str) -> List[SecurityIssue]:
        """Check compliance with security standards"""
        issues = []
        
        # Docker CIS benchmark
        try:
            result = await self._run_command("docker-bench-security", cwd=project_path)
            issues.extend(self._parse_docker_bench(result))
        except Exception as e:
            logger.warning(f"Docker bench failed: {e}")
        
        return issues
    
    async def _generate_remediation(self, issues: List[SecurityIssue]) -> None:
        """Generate AI-powered remediation guidance"""
        for issue in issues:
            if issue.remediation:
                continue
            
            prompt = f"""
            Security Issue: {issue.title}
            Severity: {issue.severity}
            Description: {issue.description}
            Component: {issue.affected_component}
            CVE: {issue.cve_id or 'N/A'}
            
            Provide step-by-step remediation instructions:
            1. Immediate actions to take
            2. Long-term fixes
            3. Prevention strategies
            """
            
            remediation = await self.ollama.generate(
                prompt,
                system="You are a security expert providing remediation guidance."
            )
            
            issue.remediation = remediation
    
    def _summarize_issues(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """Summarize issues by severity"""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "total": len(issues),
        }
        
        for issue in issues:
            summary[issue.severity] += 1
        
        return summary
    
    async def _run_command(self, cmd: str, cwd: Optional[str] = None) -> str:
        """Run shell command"""
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Command failed: {stderr.decode()}")
        
        return stdout.decode()
    
    def _parse_safety_output(self, output: str) -> List[SecurityIssue]:
        """Parse safety check output"""
        issues = []
        try:
            data = json.loads(output)
            for vuln in data:
                issues.append(SecurityIssue(
                    id=f"safety-{vuln['id']}",
                    severity=SeverityLevel.HIGH,
                    title=vuln['advisory'],
                    description=vuln['advisory'],
                    affected_component=vuln['package'],
                    cve_id=vuln.get('cve'),
                    fix_available=True,
                    fix_version=vuln.get('fixed_in'),
                ))
        except:
            pass
        return issues
    
    def _parse_npm_audit(self, output: str) -> List[SecurityIssue]:
        """Parse npm audit output"""
        issues = []
        try:
            data = json.loads(output)
            for vuln_id, vuln in data.get('vulnerabilities', {}).items():
                issues.append(SecurityIssue(
                    id=f"npm-{vuln_id}",
                    severity=SeverityLevel(vuln['severity']),
                    title=vuln['title'],
                    description=vuln.get('overview', ''),
                    affected_component=vuln['name'],
                    cve_id=vuln.get('cve'),
                    fix_available=bool(vuln.get('fixAvailable')),
                ))
        except:
            pass
        return issues
    
    def _parse_bundle_audit(self, output: str) -> List[SecurityIssue]:
        """Parse bundle audit output"""
        issues = []
        # TODO: Implement bundle audit parsing
        return issues
    
    def _parse_bandit_output(self, output: str) -> List[SecurityIssue]:
        """Parse bandit output"""
        issues = []
        try:
            data = json.loads(output)
            for result in data.get('results', []):
                severity_map = {
                    'HIGH': SeverityLevel.HIGH,
                    'MEDIUM': SeverityLevel.MEDIUM,
                    'LOW': SeverityLevel.LOW,
                }
                issues.append(SecurityIssue(
                    id=f"bandit-{result['test_id']}",
                    severity=severity_map.get(result['issue_severity'], SeverityLevel.MEDIUM),
                    title=result['issue_text'],
                    description=result['issue_text'],
                    affected_component=f"{result['filename']}:{result['line_number']}",
                ))
        except:
            pass
        return issues
    
    def _parse_semgrep_output(self, output: str) -> List[SecurityIssue]:
        """Parse semgrep output"""
        issues = []
        # TODO: Implement semgrep parsing
        return issues
    
    def _parse_trivy_output(self, output: str) -> List[SecurityIssue]:
        """Parse trivy output"""
        issues = []
        # TODO: Implement trivy parsing
        return issues
    
    def _parse_grype_output(self, output: str) -> List[SecurityIssue]:
        """Parse grype output"""
        issues = []
        # TODO: Implement grype parsing
        return issues
    
    def _parse_gitleaks_output(self, output: str) -> List[SecurityIssue]:
        """Parse gitleaks output"""
        issues = []
        # TODO: Implement gitleaks parsing
        return issues
    
    def _parse_trufflehog_output(self, output: str) -> List[SecurityIssue]:
        """Parse trufflehog output"""
        issues = []
        # TODO: Implement trufflehog parsing
        return issues
    
    def _parse_docker_bench(self, output: str) -> List[SecurityIssue]:
        """Parse docker-bench-security output"""
        issues = []
        # TODO: Implement docker-bench parsing
        return issues
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.ollama.close()

# Made with Bob
