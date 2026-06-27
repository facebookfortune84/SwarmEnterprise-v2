"""
Documentation Generator Agent - Automated Documentation Creation

Generates comprehensive documentation:
- README files
- API documentation
- Code documentation
- User guides
- Architecture diagrams
"""

import logging
import ast
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class CodeElement:
    """Code element for documentation"""

    name: str
    type: str  # function, class, module
    docstring: Optional[str]
    signature: Optional[str]
    file_path: str
    line_number: int


@dataclass
class DocumentationResult:
    """Documentation generation result"""

    doc_id: str
    files_processed: int
    elements_documented: int
    content: str
    format: str  # markdown, rst, html


class DocGenerator:
    """
    Autonomous documentation generation agent.

    Capabilities:
    - README generation
    - API documentation
    - Code documentation extraction
    - User guide creation
    - Architecture documentation
    - AI-powered content generation
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.elements: List[CodeElement] = []

        logger.info("Documentation Generator initialized")

    async def generate_readme(
        self,
        project_path: str,
        project_name: str,
        description: Optional[str] = None,
    ) -> DocumentationResult:
        """Generate comprehensive README.md"""
        logger.info(f"Generating README for {project_name}")

        project_path_obj = Path(project_path)

        # Analyze project structure
        structure = self._analyze_structure(project_path_obj)

        # Extract code elements
        await self._extract_elements(project_path_obj)

        # Generate README content
        content = await self._generate_readme_content(
            project_name, description or "A Python project", structure, self.elements
        )

        return DocumentationResult(
            doc_id=f"readme-{project_name}",
            files_processed=len(list(project_path_obj.rglob("*.py"))),
            elements_documented=len(self.elements),
            content=content,
            format="markdown",
        )

    async def generate_api_docs(
        self,
        project_path: str,
        output_format: str = "markdown",
    ) -> DocumentationResult:
        """Generate API documentation"""
        logger.info(f"Generating API documentation: {project_path}")

        project_path_obj = Path(project_path)

        # Extract API elements
        await self._extract_elements(project_path_obj)

        # Generate API documentation
        content = await self._generate_api_content(self.elements, output_format)

        return DocumentationResult(
            doc_id=f"api-docs-{datetime.utcnow().strftime('%Y%m%d')}",
            files_processed=len(list(project_path_obj.rglob("*.py"))),
            elements_documented=len(self.elements),
            content=content,
            format=output_format,
        )

    async def generate_user_guide(
        self,
        project_name: str,
        features: List[str],
        examples: Optional[List[Dict[str, str]]] = None,
    ) -> DocumentationResult:
        """Generate user guide"""
        logger.info(f"Generating user guide for {project_name}")

        content = await self._generate_user_guide_content(project_name, features, examples or [])

        return DocumentationResult(
            doc_id=f"user-guide-{project_name}",
            files_processed=0,
            elements_documented=len(features),
            content=content,
            format="markdown",
        )

    def _analyze_structure(self, project_path: Path) -> Dict[str, Any]:
        """Analyze project structure"""
        structure = {
            "directories": [],
            "python_files": [],
            "config_files": [],
            "test_files": [],
        }

        for item in project_path.rglob("*"):
            if item.is_dir() and not item.name.startswith("."):
                structure["directories"].append(str(item.relative_to(project_path)))
            elif item.suffix == ".py":
                if "test" in item.name.lower():
                    structure["test_files"].append(str(item.relative_to(project_path)))
                else:
                    structure["python_files"].append(str(item.relative_to(project_path)))
            elif item.name in ["setup.py", "pyproject.toml", "requirements.txt", "Dockerfile"]:
                structure["config_files"].append(str(item.relative_to(project_path)))

        return structure

    async def _extract_elements(self, project_path: Path) -> None:
        """Extract code elements for documentation"""
        self.elements = []

        for py_file in project_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self.elements.append(
                            CodeElement(
                                name=node.name,
                                type="function",
                                docstring=ast.get_docstring(node),
                                signature=self._get_function_signature(node),
                                file_path=str(py_file.relative_to(project_path)),
                                line_number=node.lineno,
                            )
                        )
                    elif isinstance(node, ast.ClassDef):
                        self.elements.append(
                            CodeElement(
                                name=node.name,
                                type="class",
                                docstring=ast.get_docstring(node),
                                signature=None,
                                file_path=str(py_file.relative_to(project_path)),
                                line_number=node.lineno,
                            )
                        )
            except Exception as e:
                logger.error(f"Error extracting from {py_file}: {e}")

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature"""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        return f"{node.name}({', '.join(args)})"

    async def _generate_readme_content(
        self,
        project_name: str,
        description: str,
        structure: Dict[str, Any],
        elements: List[CodeElement],
    ) -> str:
        """Generate README content using AI"""

        # Get key classes and functions
        classes = [e for e in elements if e.type == "class"][:10]
        functions = [e for e in elements if e.type == "function"][:10]

        prompt = f"""
        Generate a comprehensive README.md for a project called "{project_name}".
        
        Description: {description}
        
        Project Structure:
        - Python files: {len(structure['python_files'])}
        - Test files: {len(structure['test_files'])}
        - Key directories: {', '.join(structure['directories'][:5])}
        
        Key Components:
        Classes: {', '.join([c.name for c in classes])}
        Functions: {', '.join([f.name for f in functions])}
        
        Include these sections:
        1. Project title and description
        2. Features
        3. Installation
        4. Quick Start
        5. Usage Examples
        6. API Reference (brief)
        7. Contributing
        8. License
        
        Use markdown format with proper headings, code blocks, and formatting.
        """

        content = await self.ollama.generate(
            prompt, system="You are a technical writer creating clear, comprehensive documentation."
        )

        return content

    async def _generate_api_content(
        self,
        elements: List[CodeElement],
        output_format: str,
    ) -> str:
        """Generate API documentation content"""

        # Group by file
        by_file: Dict[str, List[CodeElement]] = {}
        for element in elements:
            if element.file_path not in by_file:
                by_file[element.file_path] = []
            by_file[element.file_path].append(element)

        if output_format == "markdown":
            content = "# API Documentation\n\n"
            content += f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

            for file_path, file_elements in sorted(by_file.items()):
                content += f"## {file_path}\n\n"

                # Classes
                classes = [e for e in file_elements if e.type == "class"]
                if classes:
                    content += "### Classes\n\n"
                    for cls in classes:
                        content += f"#### `{cls.name}`\n\n"
                        if cls.docstring:
                            content += f"{cls.docstring}\n\n"
                        else:
                            content += "*No documentation available*\n\n"

                # Functions
                functions = [e for e in file_elements if e.type == "function"]
                if functions:
                    content += "### Functions\n\n"
                    for func in functions:
                        content += f"#### `{func.signature or func.name}`\n\n"
                        if func.docstring:
                            content += f"{func.docstring}\n\n"
                        else:
                            content += "*No documentation available*\n\n"

            return content

        return "Unsupported format"

    async def _generate_user_guide_content(
        self,
        project_name: str,
        features: List[str],
        examples: List[Dict[str, str]],
    ) -> str:
        """Generate user guide content"""

        prompt = f"""
        Create a comprehensive user guide for "{project_name}".
        
        Features:
        {chr(10).join([f"- {feature}" for feature in features])}
        
        Include:
        1. Introduction
        2. Getting Started
        3. Feature explanations with examples
        4. Best practices
        5. Troubleshooting
        6. FAQ
        
        Make it beginner-friendly with clear explanations and examples.
        Use markdown format.
        """

        content = await self.ollama.generate(
            prompt, system="You are a technical writer creating user-friendly documentation."
        )

        # Add examples if provided
        if examples:
            content += "\n\n## Examples\n\n"
            for i, example in enumerate(examples, 1):
                content += f"### Example {i}: {example.get('title', 'Usage')}\n\n"
                content += f"{example.get('description', '')}\n\n"
                content += f"```python\n{example.get('code', '')}\n```\n\n"

        return content

    async def generate_architecture_doc(
        self,
        project_name: str,
        components: List[Dict[str, str]],
    ) -> DocumentationResult:
        """Generate architecture documentation"""
        logger.info(f"Generating architecture documentation for {project_name}")

        prompt = f"""
        Create architecture documentation for "{project_name}".
        
        Components:
        {chr(10).join([f"- {c['name']}: {c.get('description', '')}" for c in components])}
        
        Include:
        1. System Overview
        2. Architecture Diagram (describe in text)
        3. Component Descriptions
        4. Data Flow
        5. Technology Stack
        6. Deployment Architecture
        7. Security Considerations
        8. Scalability
        
        Use markdown format with clear sections.
        """

        content = await self.ollama.generate(
            prompt, system="You are a software architect documenting system architecture."
        )

        return DocumentationResult(
            doc_id=f"architecture-{project_name}",
            files_processed=0,
            elements_documented=len(components),
            content=content,
            format="markdown",
        )

    async def update_docstrings(
        self,
        file_path: str,
    ) -> Dict[str, Any]:
        """Generate missing docstrings for a file"""
        logger.info(f"Updating docstrings: {file_path}")

        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)

        updates = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    # Generate docstring
                    docstring = await self._generate_docstring(node, content)
                    updates.append(
                        {
                            "name": node.name,
                            "type": node.__class__.__name__,
                            "line": node.lineno,
                            "docstring": docstring,
                        }
                    )

        return {
            "file": file_path,
            "updates": updates,
            "count": len(updates),
        }

    async def _generate_docstring(
        self,
        node: ast.FunctionDef | ast.ClassDef,
        file_content: str,
    ) -> str:
        """Generate docstring for a code element"""

        lines = file_content.split("\n")
        if isinstance(node, ast.FunctionDef):
            # Get function code
            start = node.lineno - 1
            end = node.end_lineno if node.end_lineno else start + 10
            code = "\n".join(lines[start:end])

            prompt = f"""
            Generate a clear, concise docstring for this Python function:
            
            ```python
            {code}
            ```
            
            Follow Google style docstring format.
            Include: brief description, Args, Returns, Raises (if applicable).
            """
        else:  # isinstance(node, ast.ClassDef)
            # Class
            code = "\n".join(lines[node.lineno - 1 : min(node.lineno + 20, len(lines))])

            prompt = f"""
            Generate a clear, concise docstring for this Python class:
            
            ```python
            {code}
            ```
            
            Follow Google style docstring format.
            Include: brief description, Attributes (if applicable).
            """

        docstring = await self.ollama.generate(
            prompt, system="You are a Python documentation expert."
        )

        return docstring.strip()

    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.ollama.close()


# Made with Bob
