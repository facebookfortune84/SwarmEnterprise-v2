# Code Review Agent Team

Autonomous code review agents for quality assurance and security.

## Agents

### 1. Code Reviewer (`code_reviewer.py`)
**Purpose:** Comprehensive automated code review

**Capabilities:**
- Static code analysis (Python, JavaScript/TypeScript)
- Cyclomatic complexity calculation
- Function length analysis
- Missing docstring detection
- Bare except clause detection
- Mutable default argument detection
- Common anti-patterns
- AI-powered improvement suggestions

**Key Methods:**
- `review()` - Perform comprehensive code review
- `_review_python()` - Python-specific analysis
- `_review_javascript()` - JavaScript/TypeScript analysis
- `_calculate_complexity()` - Cyclomatic complexity
- `_calculate_score()` - Overall quality score (0-100)

**Usage:**
```python
from agents.code_review.code_reviewer import CodeReviewer

reviewer = CodeReviewer()
result = await reviewer.review(
    target="/path/to/project",
    file_patterns=["*.py", "*.js"]
)

print(f"Score: {result.score}/100")
print(f"Issues: {len(result.issues)}")
for issue in result.issues:
    print(f"  {issue.severity}: {issue.message}")
```

### 2. Style Checker (`style_checker.py`)
**Purpose:** Code style and formatting enforcement

**Capabilities:**
- PEP 8 compliance (Python)
- ESLint-style rules (JavaScript/TypeScript)
- Line length checking
- Indentation validation
- Trailing whitespace detection
- Import organization
- Naming convention validation
- Auto-fix for simple issues

**Key Methods:**
- `check()` - Check code style
- `_check_python_style()` - PEP 8 compliance
- `_check_javascript_style()` - JavaScript style
- `_auto_fix()` - Auto-fix fixable issues
- `_calculate_compliance_score()` - Compliance percentage

**Usage:**
```python
from agents.code_review.style_checker import StyleChecker

checker = StyleChecker()
report = await checker.check(
    target="/path/to/project",
    file_patterns=["*.py"],
    auto_fix=True  # Auto-fix simple issues
)

print(f"Compliance: {report.compliance_score:.1f}%")
print(f"Auto-fixable: {report.auto_fixable_count}")
```

**Style Rules:**

**Python (PEP 8):**
- Line length: 79 characters
- Indentation: 4 spaces
- No tabs
- 2 blank lines between top-level definitions
- Import grouping: stdlib → third-party → local
- snake_case for functions/variables
- PascalCase for classes
- UPPER_CASE for constants

**JavaScript:**
- Indentation: 2 spaces
- Semicolons required
- No `var` keyword (use `const`/`let`)
- camelCase for functions/variables
- PascalCase for classes

### 3. Security Auditor (`security_auditor.py`)
**Purpose:** Security vulnerability detection

**Capabilities:**
- Hardcoded secret detection
- SQL injection vulnerability scanning
- XSS vulnerability detection
- Insecure cryptography detection
- Path traversal vulnerability detection
- Command injection detection
- Weak random number generation detection
- Insecure transport detection
- CWE mapping
- AI-powered remediation guidance

**Key Methods:**
- `audit()` - Perform security audit
- `_check_secrets()` - Hardcoded credentials
- `_check_sql_injection()` - SQL injection
- `_check_xss()` - Cross-site scripting
- `_check_insecure_crypto()` - Weak cryptography
- `_calculate_risk_score()` - Risk score (0-100)

**Usage:**
```python
from agents.code_review.security_auditor import SecurityAuditor

auditor = SecurityAuditor()
report = await auditor.audit(
    target="/path/to/project",
    file_patterns=["*.py", "*.js"]
)

print(f"Risk Score: {report.risk_score}/100")
print(f"Critical: {report.critical_count}")
print(f"High: {report.high_count}")

for issue in report.issues:
    print(f"{issue.severity}: {issue.message}")
    print(f"  CWE: {issue.cwe_id}")
    print(f"  Fix: {issue.remediation}")
```

**Vulnerability Detection:**

- **Hardcoded Secrets** (CWE-798)
  - Passwords, API keys, tokens
  - AWS credentials, private keys
  
- **SQL Injection** (CWE-89)
  - String concatenation in queries
  - String formatting in queries
  
- **XSS** (CWE-79)
  - innerHTML assignment
  - document.write usage
  - eval() usage
  
- **Insecure Crypto** (CWE-327)
  - MD5, SHA1 usage
  - DES, RC4 usage
  
- **Path Traversal** (CWE-22)
  - Unsanitized file paths
  
- **Command Injection** (CWE-78)
  - os.system with concatenation
  - subprocess with user input
  
- **Weak Random** (CWE-338)
  - random.random() for security
  - Math.random() for security
  
- **Insecure Transport** (CWE-319)
  - HTTP URLs
  - SSL verification disabled

## Integration

### Complete Code Review Workflow

```python
from agents.code_review import CodeReviewer, StyleChecker, SecurityAuditor

async def full_code_review(project_path: str):
    """Perform complete code review"""
    
    # 1. Code quality review
    reviewer = CodeReviewer()
    quality_result = await reviewer.review(project_path)
    
    # 2. Style check
    style_checker = StyleChecker()
    style_report = await style_checker.check(
        project_path,
        auto_fix=True
    )
    
    # 3. Security audit
    auditor = SecurityAuditor()
    security_report = await auditor.audit(project_path)
    
    # Generate combined report
    return {
        "quality_score": quality_result.score,
        "style_compliance": style_report.compliance_score,
        "security_risk": security_report.risk_score,
        "total_issues": (
            len(quality_result.issues) +
            len(style_report.issues) +
            len(security_report.issues)
        ),
        "critical_security": security_report.critical_count,
    }
```

### CI/CD Integration

```python
# In CI/CD pipeline
from agents.code_review import CodeReviewer, SecurityAuditor

async def ci_code_review():
    """Run code review in CI/CD"""
    
    # Quality check
    reviewer = CodeReviewer()
    result = await reviewer.review(".")
    
    # Security check
    auditor = SecurityAuditor()
    security = await auditor.audit(".")
    
    # Fail if quality score < 70 or critical security issues
    if result.score < 70:
        print(f"❌ Quality score too low: {result.score}/100")
        exit(1)
    
    if security.critical_count > 0:
        print(f"❌ Critical security issues: {security.critical_count}")
        exit(1)
    
    print("✅ Code review passed")
```

### Pre-commit Hook

```python
# .git/hooks/pre-commit
#!/usr/bin/env python3
import asyncio
from agents.code_review import StyleChecker, SecurityAuditor

async def pre_commit_check():
    # Get staged files
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True
    )
    files = result.stdout.strip().split('\n')
    
    # Check each file
    for file in files:
        if file.endswith(('.py', '.js', '.ts')):
            # Style check
            checker = StyleChecker()
            await checker.check(file, auto_fix=True)
            
            # Security check
            auditor = SecurityAuditor()
            report = await auditor.audit(file)
            
            if report.critical_count > 0:
                print(f"❌ Critical security issues in {file}")
                exit(1)
    
    print("✅ Pre-commit checks passed")

if __name__ == "__main__":
    asyncio.run(pre_commit_check())
```

## Configuration

### Environment Variables

```bash
# Ollama LLM
OLLAMA_URL=http://192.168.1.100:11434
OLLAMA_MODEL=llama3

# Review thresholds
CODE_QUALITY_THRESHOLD=70
STYLE_COMPLIANCE_THRESHOLD=80
MAX_CRITICAL_SECURITY_ISSUES=0
```

### Custom Rules

```python
# Custom style rules
checker = StyleChecker()
checker.python_naming['function'] = r'^[a-z][a-z0-9_]*$'  # Custom pattern

# Custom security patterns
auditor = SecurityAuditor()
auditor.secret_patterns.append(
    (r'custom_secret\s*=\s*["\'][^"\']+["\']', "Custom secret")
)
```

## Reports

### Quality Report Format

```json
{
  "review_id": "review-project",
  "files_reviewed": 50,
  "score": 85.5,
  "issues": [
    {
      "file_path": "src/app.py",
      "line_number": 42,
      "severity": "high",
      "category": "maintainability",
      "message": "Function too complex (complexity: 15)",
      "suggestion": "Break into smaller functions"
    }
  ],
  "recommendations": [
    "Reduce function complexity in src/app.py",
    "Add docstrings to public methods",
    "Remove commented code"
  ]
}
```

### Security Report Format

```json
{
  "report_id": "security-project",
  "files_audited": 50,
  "risk_score": 35.0,
  "critical_count": 2,
  "high_count": 5,
  "issues": [
    {
      "file_path": "src/config.py",
      "line_number": 10,
      "severity": "critical",
      "vulnerability_type": "hardcoded_secret",
      "message": "Hardcoded API key detected",
      "cwe_id": "CWE-798",
      "remediation": "Use environment variables",
      "code_snippet": "api_key = 'sk-1234567890'"
    }
  ]
}
```

## Best Practices

1. **Run regularly** - Integrate into CI/CD pipeline
2. **Auto-fix when possible** - Use style checker auto-fix
3. **Prioritize security** - Address critical issues first
4. **Track metrics** - Monitor quality/security trends
5. **Customize rules** - Adapt to your coding standards
6. **Review AI suggestions** - Validate recommendations

## Testing

```bash
# Run agent tests
pytest tests/unit/agents/code_review/ -v

# Run with coverage
pytest tests/unit/agents/code_review/ --cov=agents.code_review --cov-report=html

# Test specific agent
pytest tests/unit/agents/code_review/test_security_auditor.py -v
```

## Troubleshooting

### Common Issues

1. **False positives**
   - Adjust patterns/thresholds
   - Add exceptions for specific cases
   - Use inline comments to suppress warnings

2. **Performance**
   - Process files in parallel
   - Cache results
   - Limit file patterns

3. **Ollama connection**
   - Verify Ollama is running
   - Check OLLAMA_URL
   - Test with simple prompt

## Future Enhancements

- [ ] Machine learning-based bug detection
- [ ] Automated refactoring suggestions
- [ ] Performance profiling integration
- [ ] Dependency vulnerability scanning
- [ ] License compliance checking
- [ ] Code duplication detection
- [ ] Test coverage analysis
- [ ] Documentation quality scoring

## License

MIT License - See LICENSE file for details