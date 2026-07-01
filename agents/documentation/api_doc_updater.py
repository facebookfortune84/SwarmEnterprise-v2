"""
API Documentation Updater Agent - Automated API Doc Maintenance

Updates and maintains API documentation:
- OpenAPI/Swagger spec generation
- Endpoint documentation
- Request/response examples
- Authentication documentation
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    """API endpoint information"""

    path: str
    method: str
    function_name: str
    description: Optional[str]
    parameters: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    auth_required: bool


@dataclass
class APIDocResult:
    """API documentation update result"""

    doc_id: str
    endpoints_documented: int
    spec_version: str
    content: str
    format: str  # openapi, markdown


class APIDocUpdater:
    """
    Autonomous API documentation updater agent.

    Capabilities:
    - OpenAPI/Swagger spec generation
    - Endpoint documentation extraction
    - Request/response example generation
    - Authentication documentation
    - API versioning support
    - AI-powered descriptions
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama = ollama_client or OllamaClient()
        self.endpoints: List[APIEndpoint] = []

        logger.info("API Documentation Updater initialized")

    async def update_openapi_spec(
        self,
        api_path: str,
        title: str,
        version: str = "1.0.0",
    ) -> APIDocResult:
        """Generate/update OpenAPI specification"""
        logger.info(f"Updating OpenAPI spec for {title}")

        # Extract endpoints
        await self._extract_endpoints(Path(api_path))

        # Generate OpenAPI spec
        spec = await self._generate_openapi_spec(title, version)

        return APIDocResult(
            doc_id=f"openapi-{title.lower().replace(' ', '-')}",
            endpoints_documented=len(self.endpoints),
            spec_version=version,
            content=json.dumps(spec, indent=2),
            format="openapi",
        )

    async def generate_endpoint_docs(
        self,
        api_path: str,
    ) -> APIDocResult:
        """Generate markdown documentation for endpoints"""
        logger.info(f"Generating endpoint documentation: {api_path}")

        # Extract endpoints
        await self._extract_endpoints(Path(api_path))

        # Generate markdown
        content = await self._generate_endpoint_markdown()

        return APIDocResult(
            doc_id=f"endpoints-{datetime.utcnow().strftime('%Y%m%d')}",
            endpoints_documented=len(self.endpoints),
            spec_version="1.0.0",
            content=content,
            format="markdown",
        )

    async def _extract_endpoints(self, api_path: Path) -> None:
        """Extract API endpoints from code"""
        self.endpoints = []

        for py_file in api_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")

                # Find FastAPI route decorators
                routes = re.findall(
                    r'@(?:router|app)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)\s*(?:async\s+)?def\s+(\w+)',
                    content,
                    re.DOTALL,
                )

                for method, path, func_name in routes:
                    # Extract function details
                    func_match = re.search(
                        rf"def\s+{func_name}\s*\([^)]*\).*?(?=\n(?:@|def|class|\Z))",
                        content,
                        re.DOTALL,
                    )

                    if func_match:
                        func_code = func_match.group(0)

                        # Extract docstring
                        doc_match = re.search(r'"""(.*?)"""', func_code, re.DOTALL)
                        description = doc_match.group(1).strip() if doc_match else None

                        # Check for auth
                        auth_required = "Depends(" in func_code or "auth" in func_code.lower()

                        # Extract parameters from function signature
                        params: List[Dict[str, Any]] = []
                        param_match = re.search(
                            rf"def\s+{func_name}\s*\(([^)]*)\)", func_code
                        )
                        if param_match:
                            raw_params = param_match.group(1)
                            for param_str in raw_params.split(","):
                                param_str = param_str.strip()
                                if not param_str or param_str in ("self", "request"):
                                    continue
                                # Skip Depends(...) injections
                                if "Depends(" in param_str or param_str.startswith("db"):
                                    continue
                                name_part = param_str.split(":")[0].strip()
                                type_part = (
                                    param_str.split(":")[1].split("=")[0].strip()
                                    if ":" in param_str
                                    else "Any"
                                )
                                if name_part:
                                    params.append({"name": name_part, "type": type_part})

                        # Extract response types from return annotation or docstring
                        responses: List[Dict[str, Any]] = []
                        return_match = re.search(
                            rf"def\s+{func_name}\s*\([^)]*\)\s*->\s*([^\n:]+)", func_code
                        )
                        if return_match:
                            responses.append({
                                "status": 200,
                                "type": return_match.group(1).strip(),
                            })
                        # Always document 422 for FastAPI endpoints
                        responses.append({"status": 422, "type": "ValidationError"})

                        self.endpoints.append(
                            APIEndpoint(
                                path=path,
                                method=method.upper(),
                                function_name=func_name,
                                description=description,
                                parameters=params,
                                responses=responses,
                                auth_required=auth_required,
                            )
                        )

            except Exception as e:
                logger.error(f"Error extracting from {py_file}: {e}")

    async def _generate_openapi_spec(
        self,
        title: str,
        version: str,
    ) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification"""

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version,
                "description": f"API documentation for {title}",
            },
            "servers": [
                {"url": "http://localhost:8000", "description": "Development"},
                {"url": "https://api.example.com", "description": "Production"},
            ],
            "paths": {},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                }
            },
        }

        # Add endpoints
        for endpoint in self.endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}

            # Generate description if missing
            if not endpoint.description:
                endpoint.description = await self._generate_endpoint_description(endpoint)

            operation = {
                "summary": endpoint.description or f"{endpoint.method} {endpoint.path}",
                "operationId": endpoint.function_name,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            }

            if endpoint.auth_required:
                operation["security"] = [{"bearerAuth": []}]

            spec["paths"][endpoint.path][endpoint.method.lower()] = operation

        return spec

    async def _generate_endpoint_markdown(self) -> str:
        """Generate markdown documentation for endpoints"""

        content = "# API Endpoints\n\n"
        content += f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        content += f"Total Endpoints: {len(self.endpoints)}\n\n"

        # Group by path prefix
        by_prefix: Dict[str, List[APIEndpoint]] = {}
        for endpoint in self.endpoints:
            prefix = endpoint.path.split("/")[1] if "/" in endpoint.path else "root"
            if prefix not in by_prefix:
                by_prefix[prefix] = []
            by_prefix[prefix].append(endpoint)

        for prefix, endpoints in sorted(by_prefix.items()):
            content += f"## {prefix.capitalize()}\n\n"

            for endpoint in sorted(endpoints, key=lambda e: e.path):
                # Generate description if missing
                if not endpoint.description:
                    endpoint.description = await self._generate_endpoint_description(endpoint)

                content += f"### `{endpoint.method} {endpoint.path}`\n\n"
                content += f"{endpoint.description}\n\n"

                if endpoint.auth_required:
                    content += "**Authentication:** Required\n\n"

                content += "**Request:**\n```http\n"
                content += f"{endpoint.method} {endpoint.path} HTTP/1.1\n"
                if endpoint.auth_required:
                    content += "Authorization: Bearer <token>\n"
                content += "```\n\n"

                content += "**Response:**\n```json\n"
                content += '{\n  "status": "success",\n  "data": {}\n}\n'
                content += "```\n\n"

        return content

    async def _generate_endpoint_description(self, endpoint: APIEndpoint) -> str:
        """Generate AI-powered endpoint description"""

        prompt = f"""
        Generate a clear, concise description for this API endpoint:
        
        Method: {endpoint.method}
        Path: {endpoint.path}
        Function: {endpoint.function_name}
        Auth Required: {endpoint.auth_required}
        
        Provide a 1-2 sentence description of what this endpoint does.
        """

        description = await self.ollama.generate(
            prompt, system="You are an API documentation expert."
        )

        return description.strip()

    async def generate_postman_collection(
        self,
        api_path: str,
        collection_name: str,
    ) -> Dict[str, Any]:
        """Generate Postman collection"""
        logger.info(f"Generating Postman collection: {collection_name}")

        # Extract endpoints
        await self._extract_endpoints(Path(api_path))

        collection = {
            "info": {
                "name": collection_name,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [],
        }

        for endpoint in self.endpoints:
            item = {
                "name": f"{endpoint.method} {endpoint.path}",
                "request": {
                    "method": endpoint.method,
                    "header": [],
                    "url": {
                        "raw": f"{{{{base_url}}}}{endpoint.path}",
                        "host": ["{{base_url}}"],
                        "path": endpoint.path.split("/")[1:],
                    },
                },
            }

            if endpoint.auth_required:
                item["request"]["header"].append(
                    {
                        "key": "Authorization",
                        "value": "Bearer {{token}}",
                    }
                )

            collection["item"].append(item)

        return collection

    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.ollama.close()


# Made with Bob
