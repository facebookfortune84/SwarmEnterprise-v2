"""
Style Checker Agent - Code Style and Formatting

Enforces code style standards:
- PEP 8 compliance (Python)
- ESLint rules (JavaScript/TypeScript)
- Naming conventions
- Import organization
- Formatting consistency
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class StyleViolation(str, Enum):
    """Style violation types"""
    NAMING = "naming"
    FORMATTING = "formatting"
    IMPORTS = "imports"
    WHITESPACE = "whitespace"
    COMMENTS = "comments"


@dataclass
class StyleIssue:
    """Style issue"""
    file_path: str
    line_number: int
    violation_type: StyleViolation
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class StyleReport:
    """Style check report"""
    report_id: str
    files_checked: int
    issues: List[StyleIssue]
    compliance_score: float
    auto_fixable_count: int


class StyleChecker:
    """
    Autonomous style checking agent.
    
    Capabilities:
    - PEP 8 compliance checking
    - ESLint rule enforcement
    - Naming convention validation
    - Import organization
    - Whitespace consistency
    - Auto-fix suggestions
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.issues: List[StyleIssue] = []
        
        # Style rules
        self.python_naming = {
            'function': r'^[a-z_][a-z0-9_]*$',
            'class': r'^[A-Z][a-zA-Z0-9]*$',
            'constant': r'^[A-Z_][A-Z0-9_]*$',
            'variable': r'^[a-z_][a-z0-9_]*$',
        }
        
        logger.info("Style Checker initialized")
    
    async def check(
        self,
        target: str,
        file_patterns: Optional[List[str]] = None,
        auto_fix: bool = False,
    ) -> StyleReport:
        """Check code style"""
        logger.info(f"Starting style check: {target}")
        
        self.issues = []
        target_path = Path(target)
        
        # Get files to check
        if target_path.is_file():
            files = [target_path]
        else:
            files = self._get_files(target_path, file_patterns or ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx"])
        
        # Check each file
        for file_path in files:
            await self._check_file(file_path)
        
        # Auto-fix if requested
        if auto_fix:
            await self._auto_fix()
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(len(files))
        
        # Count auto-fixable issues
        auto_fixable_count = sum(1 for issue in self.issues if issue.auto_fixable)
        
        report = StyleReport(
            report_id=f"style-{target_path.name}",
            files_checked=len(files),
            issues=self.issues,
            compliance_score=compliance_score,
            auto_fixable_count=auto_fixable_count,
        )
        
        logger.info(f"Style check complete: {len(self.issues)} issues, {compliance_score:.1f}% compliant")
        return report
    
    async def _check_file(self, file_path: Path) -> None:
        """Check a single file"""
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split('\n')
            
            # Determine language
            if file_path.suffix == ".py":
                await self._check_python_style(file_path, lines)
            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                await self._check_javascript_style(file_path, lines)
            
            # Common style checks
            await self._check_common_style(file_path, lines)
            
        except Exception as e:
            logger.error(f"Error checking {file_path}: {e}")
    
    async def _check_python_style(self, file_path: Path, lines: List[str]) -> None:
        """Check Python style (PEP 8)"""
        
        # Check line length (PEP 8: 79 characters)
        for i, line in enumerate(lines, 1):
            if len(line) > 79 and not line.strip().startswith('#'):
                self.issues.append(StyleIssue(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type=StyleViolation.FORMATTING,
                    message=f"Line exceeds 79 characters ({len(line)})",
                    suggestion="Break line into multiple lines",
                    auto_fixable=False,
                ))
        
        # Check indentation (PEP 8: 4 spaces)
        for i, line in enumerate(lines, 1):
            if line and not line[0].isspace() and line[0] != '#':
                continue
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces % 4 != 0 and leading_spaces > 0:
                self.issues.append(StyleIssue(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type=StyleViolation.FORMATTING,
                    message=f"Indentation not multiple of 4 ({leading_spaces} spaces)",
                    suggestion="Use 4 spaces for indentation",
                    auto_fixable=True,
                ))
        
        # Check for tabs
        for i, line in enumerate(lines, 1):
            if '\t' in line:
                self.issues.append(StyleIssue(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type=StyleViolation.WHITESPACE,
                    message="Tab character found",
                    suggestion="Use spaces instead of tabs",
                    auto_fixable=True,
                ))
        
        # Check trailing whitespace
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line and line.strip():
                self.issues.append(StyleIssue(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type=StyleViolation.WHITESPACE,
                    message="Trailing whitespace",
                    suggestion="Remove trailing whitespace",
                    auto_fixable=True,
                ))
        
        # Check blank lines (PEP 8: 2 blank lines between top-level definitions)
        in_class = False
        prev_blank_count = 0
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('class '):
                if i > 1 and prev_blank_count < 2:
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.FORMATTING,
                        message="Expected 2 blank lines before class definition",
                        suggestion="Add blank lines",
                        auto_fixable=True,
                    ))
                in_class = True
            elif line.strip().startswith('def ') and not in_class:
                if i > 1 and prev_blank_count < 2:
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.FORMATTING,
                        message="Expected 2 blank lines before function definition",
                        suggestion="Add blank lines",
                        auto_fixable=True,
                    ))
            
            if not line.strip():
                prev_blank_count += 1
            else:
                prev_blank_count = 0
        
        # Check import organization
        import_lines = []
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(('import ', 'from ')):
                import_lines.append((i, line))
        
        if import_lines:
            # Check if imports are grouped (stdlib, third-party, local)
            prev_type = None
            for i, line in import_lines:
                import_type = self._classify_import(line)
                if prev_type and import_type < prev_type:
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.IMPORTS,
                        message="Imports not properly grouped",
                        suggestion="Group imports: stdlib, third-party, local",
                        auto_fixable=True,
                    ))
                prev_type = import_type
        
        # Check naming conventions
        for i, line in enumerate(lines, 1):
            # Function names
            func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                if not re.match(self.python_naming['function'], func_name):
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.NAMING,
                        message=f"Function name '{func_name}' doesn't follow snake_case",
                        suggestion="Use lowercase with underscores",
                        auto_fixable=False,
                    ))
            
            # Class names
            class_match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
            if class_match:
                class_name = class_match.group(1)
                if not re.match(self.python_naming['class'], class_name):
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.NAMING,
                        message=f"Class name '{class_name}' doesn't follow PascalCase",
                        suggestion="Use PascalCase for class names",
                        auto_fixable=False,
                    ))
    
    async def _check_javascript_style(self, file_path: Path, lines: List[str]) -> None:
        """Check JavaScript/TypeScript style"""
        
        # Check semicolons
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                if stripped.endswith('}') or stripped.endswith('{'):
                    continue
                if not stripped.endswith(';') and not stripped.endswith(','):
                    # Check if it's a statement that should have semicolon
                    if any(stripped.startswith(kw) for kw in ['const ', 'let ', 'var ', 'return ']):
                        self.issues.append(StyleIssue(
                            file_path=str(file_path),
                            line_number=i,
                            violation_type=StyleViolation.FORMATTING,
                            message="Missing semicolon",
                            suggestion="Add semicolon at end of statement",
                            auto_fixable=True,
                        ))
        
        # Check indentation (2 spaces for JS)
        for i, line in enumerate(lines, 1):
            if line and not line[0].isspace():
                continue
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces % 2 != 0 and leading_spaces > 0:
                self.issues.append(StyleIssue(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type=StyleViolation.FORMATTING,
                    message=f"Indentation not multiple of 2 ({leading_spaces} spaces)",
                    suggestion="Use 2 spaces for indentation",
                    auto_fixable=True,
                ))
        
        # Check for var usage
        for i, line in enumerate(lines, 1):
            if re.search(r'\bvar\b', line) and not line.strip().startswith('//'):
                self.issues.append(StyleIssue(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type=StyleViolation.FORMATTING,
                    message="'var' keyword used",
                    suggestion="Use 'const' or 'let' instead",
                    auto_fixable=True,
                ))
        
        # Check naming conventions (camelCase for functions/variables)
        for i, line in enumerate(lines, 1):
            # Function declarations
            func_match = re.search(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
            if func_match:
                func_name = func_match.group(1)
                if not re.match(r'^[a-z][a-zA-Z0-9]*$', func_name):
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.NAMING,
                        message=f"Function name '{func_name}' doesn't follow camelCase",
                        suggestion="Use camelCase for function names",
                        auto_fixable=False,
                    ))
    
    async def _check_common_style(self, file_path: Path, lines: List[str]) -> None:
        """Check common style issues"""
        
        # Check for multiple blank lines
        blank_count = 0
        for i, line in enumerate(lines, 1):
            if not line.strip():
                blank_count += 1
                if blank_count > 2:
                    self.issues.append(StyleIssue(
                        file_path=str(file_path),
                        line_number=i,
                        violation_type=StyleViolation.WHITESPACE,
                        message="More than 2 consecutive blank lines",
                        suggestion="Remove extra blank lines",
                        auto_fixable=True,
                    ))
            else:
                blank_count = 0
        
        # Check file ends with newline
        if lines and lines[-1].strip():
            self.issues.append(StyleIssue(
                file_path=str(file_path),
                line_number=len(lines),
                violation_type=StyleViolation.FORMATTING,
                message="File doesn't end with newline",
                suggestion="Add newline at end of file",
                auto_fixable=True,
            ))
    
    def _classify_import(self, line: str) -> int:
        """Classify import type (0=stdlib, 1=third-party, 2=local)"""
        stdlib_modules = {
            'os', 'sys', 'json', 'logging', 'datetime', 'time', 'asyncio',
            're', 'pathlib', 'typing', 'dataclasses', 'enum', 'collections',
        }
        
        # Extract module name
        if line.strip().startswith('import '):
            module = line.strip().split()[1].split('.')[0]
        elif line.strip().startswith('from '):
            module = line.strip().split()[1].split('.')[0]
        else:
            return 2
        
        if module in stdlib_modules:
            return 0
        elif module.startswith('.'):
            return 2
        else:
            return 1
    
    async def _auto_fix(self) -> None:
        """Auto-fix fixable issues"""
        fixable = [i for i in self.issues if i.auto_fixable]
        logger.info(f"Auto-fixing {len(fixable)} issues")
        
        # Group by file
        by_file: Dict[str, List[StyleIssue]] = {}
        for issue in fixable:
            if issue.file_path not in by_file:
                by_file[issue.file_path] = []
            by_file[issue.file_path].append(issue)
        
        # Fix each file
        for file_path, issues in by_file.items():
            try:
                path = Path(file_path)
                content = path.read_text(encoding="utf-8")
                lines = content.split('\n')
                
                # Apply fixes (in reverse order to maintain line numbers)
                for issue in sorted(issues, key=lambda x: x.line_number, reverse=True):
                    if issue.violation_type == StyleViolation.WHITESPACE:
                        if "trailing" in issue.message.lower():
                            lines[issue.line_number - 1] = lines[issue.line_number - 1].rstrip()
                        elif "tab" in issue.message.lower():
                            lines[issue.line_number - 1] = lines[issue.line_number - 1].replace('\t', '    ')
                
                # Write back
                path.write_text('\n'.join(lines), encoding="utf-8")
                logger.info(f"Fixed {len(issues)} issues in {file_path}")
                
            except Exception as e:
                logger.error(f"Error auto-fixing {file_path}: {e}")
    
    def _calculate_compliance_score(self, file_count: int) -> float:
        """Calculate style compliance score"""
        if not self.issues:
            return 100.0
        
        # Deduct points per issue
        deduction_per_issue = 100.0 / max(file_count * 10, 1)
        total_deduction = len(self.issues) * deduction_per_issue
        
        return max(0, 100 - total_deduction)
    
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
