"""
Code Reviewer Agent - Automated Code Review

Performs comprehensive code reviews:
- Code quality analysis
- Best practices validation
- Bug detection
- Performance issues
- Maintainability assessment
- AI-powered suggestions
"""

import logging
import ast
import re
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Issue severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Issue categories"""

    BUG = "bug"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    STYLE = "style"
    DOCUMENTATION = "documentation"


@dataclass
class ReviewIssue:
    """Code review issue"""

    file_path: str
    line_number: int
    severity: Severity
    category: Category
    message: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class ReviewResult:
    """Code review result"""

    review_id: str
    files_reviewed: int
    issues: List[ReviewIssue]
    score: float
    summary: str
    recommendations: List[str]


class CodeReviewer:
    """
    Autonomous code review agent.

    Capabilities:
    - Static code analysis
    - Pattern detection
    - Complexity analysis
    - Best practices validation
    - AI-powered suggestions
    - Automated fix recommendations
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.issues: List[ReviewIssue] = []

        logger.info("Code Reviewer initialized")

    async def review(
        self,
        target: str,
        file_patterns: Optional[List[str]] = None,
    ) -> ReviewResult:
        """Perform comprehensive code review"""
        logger.info(f"Starting code review: {target}")

        self.issues = []
        target_path = Path(target)

        # Get files to review
        if target_path.is_file():
            files = [target_path]
        else:
            files = self._get_files(
                target_path, file_patterns or ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"]
            )

        # Review each file
        for file_path in files:
            await self._review_file(file_path)

        # Calculate score
        score = self._calculate_score()

        # Generate summary
        summary = await self._generate_summary()

        # Generate recommendations
        recommendations = await self._generate_recommendations()

        result = ReviewResult(
            review_id=f"review-{target_path.name}",
            files_reviewed=len(files),
            issues=self.issues,
            score=score,
            summary=summary,
            recommendations=recommendations,
        )

        logger.info(
            f"Code review complete: {len(self.issues)} issues found, score: {score:.1f}/100"
        )
        return result

    async def _review_file(self, file_path: Path) -> None:
        """Review a single file"""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Determine language
            if file_path.suffix == ".py":
                await self._review_python(file_path, content)
            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                await self._review_javascript(file_path, content)

            # Common checks for all languages
            await self._check_common_issues(file_path, content)

        except Exception as e:
            logger.error(f"Error reviewing {file_path}: {e}")

    async def _review_python(self, file_path: Path, content: str) -> None:
        """Review Python code"""
        try:
            tree = ast.parse(content)

            # Check complexity
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_complexity(node)
                    if complexity > 10:
                        self.issues.append(
                            ReviewIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                severity=Severity.MEDIUM,
                                category=Category.MAINTAINABILITY,
                                message=f"Function '{node.name}' has high complexity ({complexity})",
                                suggestion="Consider breaking down into smaller functions",
                            )
                        )

                # Check for long functions
                if isinstance(node, ast.FunctionDef):
                    if node.end_lineno and node.lineno:
                        func_lines = node.end_lineno - node.lineno
                    else:
                        func_lines = 0
                    if func_lines > 50:
                        self.issues.append(
                            ReviewIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                severity=Severity.LOW,
                                category=Category.MAINTAINABILITY,
                                message=f"Function '{node.name}' is too long ({func_lines} lines)",
                                suggestion="Consider splitting into smaller functions",
                            )
                        )

                # Check for missing docstrings
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        self.issues.append(
                            ReviewIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                severity=Severity.LOW,
                                category=Category.DOCUMENTATION,
                                message=f"{node.__class__.__name__} '{node.name}' missing docstring",
                                suggestion="Add docstring describing purpose and parameters",
                            )
                        )

                # Check for bare except
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        self.issues.append(
                            ReviewIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                severity=Severity.HIGH,
                                category=Category.BUG,
                                message="Bare except clause catches all exceptions",
                                suggestion="Catch specific exceptions instead",
                            )
                        )

                # Check for mutable default arguments
                if isinstance(node, ast.FunctionDef):
                    for default in node.args.defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            self.issues.append(
                                ReviewIssue(
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    severity=Severity.HIGH,
                                    category=Category.BUG,
                                    message=f"Function '{node.name}' has mutable default argument",
                                    suggestion="Use None as default and initialize inside function",
                                )
                            )

        except SyntaxError as e:
            self.issues.append(
                ReviewIssue(
                    file_path=str(file_path),
                    line_number=e.lineno or 0,
                    severity=Severity.CRITICAL,
                    category=Category.BUG,
                    message=f"Syntax error: {e.msg}",
                )
            )

    async def _review_javascript(self, file_path: Path, content: str) -> None:
        """Review JavaScript/TypeScript code"""
        lines = content.split("\n")

        # Check for console.log
        for i, line in enumerate(lines, 1):
            if "console.log" in line and not line.strip().startswith("//"):
                self.issues.append(
                    ReviewIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=Severity.LOW,
                        category=Category.MAINTAINABILITY,
                        message="console.log statement found",
                        suggestion="Remove debug statements or use proper logging",
                    )
                )

        # Check for var usage
        for i, line in enumerate(lines, 1):
            if re.search(r"\bvar\b", line) and not line.strip().startswith("//"):
                self.issues.append(
                    ReviewIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=Severity.MEDIUM,
                        category=Category.MAINTAINABILITY,
                        message="'var' keyword used",
                        suggestion="Use 'const' or 'let' instead",
                    )
                )

        # Check for == instead of ===
        for i, line in enumerate(lines, 1):
            if re.search(r"[^=!]==[^=]", line) and not line.strip().startswith("//"):
                self.issues.append(
                    ReviewIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=Severity.MEDIUM,
                        category=Category.BUG,
                        message="Loose equality (==) used",
                        suggestion="Use strict equality (===) instead",
                    )
                )

    async def _check_common_issues(self, file_path: Path, content: str) -> None:
        """Check for common issues across all languages"""
        lines = content.split("\n")

        # Check file length
        if len(lines) > 500:
            self.issues.append(
                ReviewIssue(
                    file_path=str(file_path),
                    line_number=1,
                    severity=Severity.LOW,
                    category=Category.MAINTAINABILITY,
                    message=f"File is too long ({len(lines)} lines)",
                    suggestion="Consider splitting into multiple files",
                )
            )

        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                self.issues.append(
                    ReviewIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=Severity.LOW,
                        category=Category.STYLE,
                        message=f"Line too long ({len(line)} characters)",
                        suggestion="Break into multiple lines",
                    )
                )

        # Check for TODO/FIXME comments
        for i, line in enumerate(lines, 1):
            if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE):
                self.issues.append(
                    ReviewIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=Severity.INFO,
                        category=Category.MAINTAINABILITY,
                        message="TODO/FIXME comment found",
                        suggestion="Create a ticket to track this work",
                    )
                )

        # Check for hardcoded credentials
        for i, line in enumerate(lines, 1):
            if re.search(
                r'(password|secret|api[_-]?key|token)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE
            ):
                self.issues.append(
                    ReviewIssue(
                        file_path=str(file_path),
                        line_number=i,
                        severity=Severity.CRITICAL,
                        category=Category.SECURITY,
                        message="Potential hardcoded credential",
                        suggestion="Use environment variables or secret management",
                    )
                )

        # Check for commented code
        comment_lines = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                comment_lines += 1

        if comment_lines > len(lines) * 0.3:
            self.issues.append(
                ReviewIssue(
                    file_path=str(file_path),
                    line_number=1,
                    severity=Severity.LOW,
                    category=Category.MAINTAINABILITY,
                    message=f"High ratio of comments ({comment_lines}/{len(lines)} lines)",
                    suggestion="Remove commented code or improve documentation",
                )
            )

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _calculate_score(self) -> float:
        """Calculate overall code quality score"""
        if not self.issues:
            return 100.0

        # Deduct points based on severity
        deductions = {
            Severity.CRITICAL: 20,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 0.5,
        }

        total_deduction = sum(deductions[issue.severity] for issue in self.issues)
        score = max(0, 100 - total_deduction)

        return score

    async def _generate_summary(self) -> str:
        """Generate review summary"""
        if not self.issues:
            return "Code quality is excellent. No issues found."

        # Count by severity
        severity_counts = {}
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        # Count by category
        category_counts = {}
        for issue in self.issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        summary_parts = [
            f"Found {len(self.issues)} issues:",
            f"- Critical: {severity_counts.get(Severity.CRITICAL, 0)}",
            f"- High: {severity_counts.get(Severity.HIGH, 0)}",
            f"- Medium: {severity_counts.get(Severity.MEDIUM, 0)}",
            f"- Low: {severity_counts.get(Severity.LOW, 0)}",
            "",
            "Top categories:",
        ]

        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[
            :3
        ]:
            summary_parts.append(f"- {category}: {count}")

        return "\n".join(summary_parts)

    async def _generate_recommendations(self) -> List[str]:
        """Generate AI-powered recommendations"""
        if not self.issues:
            return ["Continue maintaining high code quality standards"]

        # Get top issues
        critical_issues = [i for i in self.issues if i.severity == Severity.CRITICAL]
        high_issues = [i for i in self.issues if i.severity == Severity.HIGH]

        prompt = f"""
        Code Review Analysis:
        
        Total Issues: {len(self.issues)}
        Critical: {len(critical_issues)}
        High: {len(high_issues)}
        
        Top Issues:
        {chr(10).join([f"- {i.category}: {i.message}" for i in (critical_issues + high_issues)[:5]])}
        
        Provide 5 specific, actionable recommendations to improve code quality.
        Focus on the most impactful changes.
        """

        response = await self.ollama.generate(
            prompt, system="You are a senior software engineer providing code review feedback."
        )

        recommendations = [
            line.strip()
            for line in response.split("\n")
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
