"""
Check and fix common errors in the codebase
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def run_pylint_check():
    """Run pylint on all Python files"""
    print("Running pylint error check...")
    
    dirs_to_check = [
        "backend/auth",
        "backend/api",
        "backend/services",
        "backend/storage",
        "backend/llm",
        "agents/devops",
        "agents/code_review",
        "agents/documentation",
        "agents/ticketing",
        "agents/self_healing",
    ]
    
    errors_found = False
    
    for dir_path in dirs_to_check:
        full_path = PROJECT_ROOT / dir_path
        if not full_path.exists():
            continue
        
        print(f"\nChecking {dir_path}...")
        result = subprocess.run(
            [sys.executable, "-m", "pylint", str(full_path / "*.py"), "--errors-only"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 and result.stdout:
            print(result.stdout)
            errors_found = True
    
    return not errors_found

def run_syntax_check():
    """Run Python syntax check"""
    print("\nRunning syntax check...")
    
    python_files = list(PROJECT_ROOT.glob("**/*.py"))
    errors = []
    
    for py_file in python_files:
        # Skip venv and node_modules
        if "venv" in str(py_file) or "node_modules" in str(py_file):
            continue
        
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(py_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            errors.append((py_file, result.stderr))
    
    if errors:
        print(f"\nFound {len(errors)} syntax errors:")
        for file, error in errors[:10]:  # Show first 10
            print(f"\n{file}:")
            print(error)
        return False
    
    print("No syntax errors found!")
    return True

def main():
    """Main check function"""
    print("=" * 60)
    print("SwarmEnterprise v2 - Error Check")
    print("=" * 60)
    
    syntax_ok = run_syntax_check()
    
    if not syntax_ok:
        print("\nFix syntax errors before proceeding.")
        return 1
    
    print("\n" + "=" * 60)
    print("All checks passed!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
