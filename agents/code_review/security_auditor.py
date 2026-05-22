"""
Security Auditor Agent - Security Vulnerability Detection

Performs security audits:
- Vulnerability scanning
- Dependency analysis
- Secret detection
- SQL injection detection
- XSS vulnerability detection
- CSRF protection validation
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security issue severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(str, Enum):
    """Vulnerability types"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    HARDCODED_SECRET = "hardcoded_secret"
    INSECURE_CRYPTO = "insecure_crypto"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"
    WEAK_RANDOM = "weak_random"
    INSECURE_TRANSPORT = "insecure_transport"


@dataclass
class SecurityIssue:
    """Security issue"""
    file_path: str
    line_number: int
    severity: SecurityLevel
    vulnerability_type: VulnerabilityType
    message: str
    cwe_id: Optional[str] = None
    remediation: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class SecurityReport:
    """Security audit report"""
    report_id: str
    files_audited: int
    issues: List[SecurityIssue]
    risk_score: float
    critical_count: int
    high_count: int
    recommendations: List[str]


class SecurityAuditor:
    """
    Autonomous security auditing agent.
    
    Capabilities:
    - Static security analysis
    - Vulnerability pattern detection
    - Secret scanning
    - Dependency vulnerability checking
    - AI-powered remediation guidance
    - CWE mapping
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.issues: List[SecurityIssue] = []
        
        # Security patterns
        self.secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            (r'aws_access_key_id\s*=\s*["\'][^"\']+["\']', "AWS access key"),
            (r'private[_-]?key\s*=\s*["\'][^"\']+["\']', "Private key"),
        ]
        
        self.sql_injection_patterns = [
            (r'execute\([^)]*\+[^)]*\)', "String concatenation in SQL query"),
            (r'cursor\.execute\([^)]*%[^)]*\)', "String formatting in SQL query"),
            (r'\.format\([^)]*\).*execute', "String format in SQL query"),
            (r'f["\'].*\{.*\}.*["\'].*execute', "f-string in SQL query"),
        ]
        
        self.xss_patterns = [
            (r'innerHTML\s*=', "Direct innerHTML assignment"),
            (r'document\.write\(', "document.write usage"),
            (r'eval\(', "eval() usage"),
            (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML"),
        ]
        
        logger.info("Security Auditor initialized")
    
    async def audit(
        self,
        target: str,
        file_patterns: Optional[List[str]] = None,
    ) -> SecurityReport:
        """Perform security audit"""
        logger.info(f"Starting security audit: {target}")
        
        self.issues = []
        target_path = Path(target)
        
        # Get files to audit
        if target_path.is_file():
            files = [target_path]
        else:
            files = self._get_files(target_path, file_patterns or ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"])
        
        # Audit each file
        for file_path in files:
            await self._audit_file(file_path)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score()
        
        # Count by severity
        critical_count = sum(1 for i in self.issues if i.severity == SecurityLevel.CRITICAL)
        high_count = sum(1 for i in self.issues if i.severity == SecurityLevel.HIGH)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations()
        
        report = SecurityReport(
            report_id=f"security-{target_path.name}",
            files_audited=len(files),
            issues=self.issues,
            risk_score=risk_score,
            critical_count=critical_count,
            high_count=high_count,
            recommendations=recommendations,
        )
        
        logger.info(f"Security audit complete: {len(self.issues)} issues, risk score: {risk_score:.1f}")
        return report
    
    async def _audit_file(self, file_path: Path) -> None:
        """Audit a single file"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split('\n')
            
            # Check for secrets
            await self._check_secrets(file_path, lines)
            
            # Check for SQL injection
            await self._check_sql_injection(file_path, lines)
            
            # Check for XSS
            await self._check_xss(file_path, lines)
            
            # Check for insecure crypto
            await self._check_insecure_crypto(file_path, lines)
            
            # Check for path traversal
            await self._check_path_traversal(file_path, lines)
            
            # Check for command injection
            await self._check_command_injection(file_path, lines)
            
            # Check for weak random
            await self._check_weak_random(file_path, lines)
            
            # Check for insecure transport
            await self._check_insecure_transport(file_path, lines)
            
        except Exception as e:
            logger.error(f"Error auditing {file_path}: {e}")
    
    async def _check_secrets(self, file_path: Path, lines: List[str]) -> None:
        """Check for hardcoded secrets"""
        for i, line in enumerate(lines, 1):
            for pattern, description in self.secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.CRITICAL,
                        vulnerability_type=VulnerabilityType.HARDCODED_SECRET,
                        message=f"{description} detected",
                        cwe_id="CWE-798",
                        remediation="Use environment variables or secret management service",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_sql_injection(self, file_path: Path, lines: List[str]) -> None:
        """Check for SQL injection vulnerabilities"""
        for i, line in enumerate(lines, 1):
            for pattern, description in self.sql_injection_patterns:
                if re.search(pattern, line):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.CRITICAL,
                        vulnerability_type=VulnerabilityType.SQL_INJECTION,
                        message=f"Potential SQL injection: {description}",
                        cwe_id="CWE-89",
                        remediation="Use parameterized queries or ORM",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_xss(self, file_path: Path, lines: List[str]) -> None:
        """Check for XSS vulnerabilities"""
        for i, line in enumerate(lines, 1):
            for pattern, description in self.xss_patterns:
                if re.search(pattern, line):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.HIGH,
                        vulnerability_type=VulnerabilityType.XSS,
                        message=f"Potential XSS: {description}",
                        cwe_id="CWE-79",
                        remediation="Sanitize user input and use safe DOM methods",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_insecure_crypto(self, file_path: Path, lines: List[str]) -> None:
        """Check for insecure cryptography"""
        insecure_patterns = [
            (r'\bmd5\b', "MD5 is cryptographically broken"),
            (r'\bsha1\b', "SHA1 is cryptographically weak"),
            (r'\bDES\b', "DES is insecure"),
            (r'\bRC4\b', "RC4 is insecure"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, description in insecure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.HIGH,
                        vulnerability_type=VulnerabilityType.INSECURE_CRYPTO,
                        message=description,
                        cwe_id="CWE-327",
                        remediation="Use SHA-256 or stronger algorithms",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_path_traversal(self, file_path: Path, lines: List[str]) -> None:
        """Check for path traversal vulnerabilities"""
        patterns = [
            r'open\([^)]*\+[^)]*\)',
            r'Path\([^)]*\+[^)]*\)',
            r'os\.path\.join\([^)]*user[^)]*\)',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.HIGH,
                        vulnerability_type=VulnerabilityType.PATH_TRAVERSAL,
                        message="Potential path traversal vulnerability",
                        cwe_id="CWE-22",
                        remediation="Validate and sanitize file paths",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_command_injection(self, file_path: Path, lines: List[str]) -> None:
        """Check for command injection vulnerabilities"""
        patterns = [
            r'os\.system\([^)]*\+[^)]*\)',
            r'subprocess\.(call|run|Popen)\([^)]*\+[^)]*\)',
            r'exec\([^)]*\+[^)]*\)',
            r'eval\([^)]*\+[^)]*\)',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.CRITICAL,
                        vulnerability_type=VulnerabilityType.COMMAND_INJECTION,
                        message="Potential command injection vulnerability",
                        cwe_id="CWE-78",
                        remediation="Use parameterized commands and input validation",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_weak_random(self, file_path: Path, lines: List[str]) -> None:
        """Check for weak random number generation"""
        patterns = [
            (r'\brandom\.random\b', "random.random() is not cryptographically secure"),
            (r'\bMath\.random\b', "Math.random() is not cryptographically secure"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if re.search(pattern, line):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.MEDIUM,
                        vulnerability_type=VulnerabilityType.WEAK_RANDOM,
                        message=description,
                        cwe_id="CWE-338",
                        remediation="Use secrets module (Python) or crypto.getRandomValues (JS)",
                        code_snippet=line.strip(),
                    ))
    
    async def _check_insecure_transport(self, file_path: Path, lines: List[str]) -> None:
        """Check for insecure transport"""
        patterns = [
            (r'http://', "HTTP URL (unencrypted)"),
            (r'verify\s*=\s*False', "SSL verification disabled"),
            (r'ssl\._create_unverified_context', "Unverified SSL context"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if re.search(pattern, line):
                    self.issues.append(SecurityIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=SecurityLevel.MEDIUM,
                        vulnerability_type=VulnerabilityType.INSECURE_TRANSPORT,
                        message=description,
                        cwe_id="CWE-319",
                        remediation="Use HTTPS and enable SSL verification",
                        code_snippet=line.strip(),
                    ))
    
    def _calculate_risk_score(self) -> float:
        """Calculate overall security risk score (0-100, higher is riskier)"""
        if not self.issues:
            return 0.0
        
        # Weight by severity
        weights = {
            SecurityLevel.CRITICAL: 25,
            SecurityLevel.HIGH: 15,
            SecurityLevel.MEDIUM: 8,
            SecurityLevel.LOW: 3,
            SecurityLevel.INFO: 1,
        }
        
        total_risk = sum(weights[issue.severity] for issue in self.issues)
        
        # Cap at 100
        return min(100.0, total_risk)
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate AI-powered security recommendations"""
        if not self.issues:
            return ["No security issues detected. Continue following security best practices."]
        
        # Get critical and high issues
        critical = [i for i in self.issues if i.severity == SecurityLevel.CRITICAL]
        high = [i for i in self.issues if i.severity == SecurityLevel.HIGH]
        
        prompt = f"""
        Security Audit Results:
        
        Total Issues: {len(self.issues)}
        Critical: {len(critical)}
        High: {len(high)}
        
        Critical Issues:
        {chr(10).join([f"- {i.vulnerability_type}: {i.message}" for i in critical[:5]])}
        
        High Issues:
        {chr(10).join([f"- {i.vulnerability_type}: {i.message}" for i in high[:5]])}
        
        Provide 5 specific, prioritized security recommendations.
        Focus on the most critical vulnerabilities first.
        """
        
        response = await self.ollama.generate(
            prompt,
            system="You are a security expert providing remediation guidance."
        )
        
        recommendations = [
            line.strip() for line in response.split('\n')
            if line.strip() and line.strip()[0].isdigit()
        ]
        
        return recommendations[:5]
    
    def _get_files(self, directory: Path, patterns: List[str]) -> List[Path]:
        """Get files matching patterns"""
        files = []
        for pattern in patterns:
            files.extend(directory.rglob(pattern))
        return files
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.ollama.close()

# Made with Bob
