"""
Template engine for processing and rendering code templates
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Service for loading and rendering code templates

    Supports Jinja2 templating for dynamic code generation
    """

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize template engine

        Args:
            templates_dir: Path to templates directory
        """
        if templates_dir is None:
            # Default to backend/templates/
            base_dir = Path(__file__).parent.parent
            templates_dir = str(base_dir / "templates")

        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,  # Don't escape code
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def load_template_config(self, tech_stack: str) -> Dict[str, Any]:
        """
        Load template configuration

        Args:
            tech_stack: Technology stack name

        Returns:
            Template configuration dictionary

        Raises:
            FileNotFoundError: If template config not found
        """
        config_path = os.path.join(self.templates_dir, tech_stack, "template_config.json")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Template config not found: {config_path}")

        with open(config_path, "r") as f:
            config = json.load(f)

        logger.info(f"Loaded template config for {tech_stack}")
        return config

    def render_template(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render a template with context

        Args:
            template_path: Path to template file (relative to templates_dir)
            context: Template context variables

        Returns:
            Rendered template string
        """
        try:
            template = self.env.get_template(template_path)
            rendered = template.render(**context)
            logger.debug(f"Rendered template: {template_path}")
            return rendered
        except Exception as e:
            logger.error(f"Failed to render template {template_path}: {str(e)}")
            raise

    def render_file(self, tech_stack: str, file_path: str, context: Dict[str, Any]) -> str:
        """
        Render a specific file from a tech stack template

        Args:
            tech_stack: Technology stack name
            file_path: File path within the template
            context: Template context variables

        Returns:
            Rendered file content
        """
        template_path = os.path.join(tech_stack, file_path)
        return self.render_template(template_path, context)

    def get_template_files(self, tech_stack: str) -> List[str]:
        """
        Get list of all template files for a tech stack

        Args:
            tech_stack: Technology stack name

        Returns:
            List of template file paths
        """
        template_dir = os.path.join(self.templates_dir, tech_stack)

        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        files = []
        for root, _, filenames in os.walk(template_dir):
            for filename in filenames:
                if filename.endswith(".template") or filename.endswith(".j2"):
                    rel_path = os.path.relpath(os.path.join(root, filename), template_dir)
                    files.append(rel_path)

        return files

    def render_all_files(self, tech_stack: str, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Render all template files for a tech stack

        Args:
            tech_stack: Technology stack name
            context: Template context variables

        Returns:
            Dictionary mapping output paths to rendered content
        """
        files = self.get_template_files(tech_stack)
        rendered_files = {}

        for file_path in files:
            try:
                # Remove .template or .j2 extension for output path
                output_path = file_path.replace(".template", "").replace(".j2", "")

                # Render the file
                content = self.render_file(tech_stack, file_path, context)
                rendered_files[output_path] = content

            except Exception as e:
                logger.error(f"Failed to render {file_path}: {str(e)}")
                # Continue with other files

        logger.info(f"Rendered {len(rendered_files)} files for {tech_stack}")
        return rendered_files

    def validate_template(self, tech_stack: str) -> bool:
        """
        Validate that a template is properly configured

        Args:
            tech_stack: Technology stack name

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if template directory exists
            template_dir = os.path.join(self.templates_dir, tech_stack)
            if not os.path.exists(template_dir):
                logger.error(f"Template directory not found: {template_dir}")
                return False

            # Check if config exists
            config = self.load_template_config(tech_stack)

            # Validate required config fields
            required_fields = ["name", "version", "description"]
            for field in required_fields:
                if field not in config:
                    logger.error(f"Missing required field in config: {field}")
                    return False

            # Check if template files exist
            files = self.get_template_files(tech_stack)
            if not files:
                logger.error(f"No template files found for {tech_stack}")
                return False

            logger.info(f"Template validation passed for {tech_stack}")
            return True

        except Exception as e:
            logger.error(f"Template validation failed: {str(e)}")
            return False

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        Get list of all available templates

        Returns:
            List of template info dictionaries
        """
        templates = []

        if not os.path.exists(self.templates_dir):
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return templates

        for item in os.listdir(self.templates_dir):
            item_path = os.path.join(self.templates_dir, item)
            if os.path.isdir(item_path):
                try:
                    config = self.load_template_config(item)
                    templates.append(
                        {
                            "id": item,
                            "name": config.get("name", item),
                            "version": config.get("version", "unknown"),
                            "description": config.get("description", ""),
                            "features": config.get("features", []),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Could not load template {item}: {str(e)}")

        return templates

    def create_context(
        self, company_name: str, description: str, features: List[str], **kwargs
    ) -> Dict[str, Any]:
        """
        Create template context from company parameters

        Args:
            company_name: Company name
            description: Company description
            features: List of features to include
            **kwargs: Additional context variables

        Returns:
            Template context dictionary
        """
        import re

        # Generate various name formats
        slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
        snake_case = re.sub(r"[^a-z0-9]+", "_", company_name.lower()).strip("_")
        pascal_case = "".join(word.capitalize() for word in company_name.split())

        context = {
            "company_name": company_name,
            "description": description,
            "slug": slug,
            "snake_case": snake_case,
            "pascal_case": pascal_case,
            "features": features,
            "has_auth": "authentication" in features,
            "has_database": "database" in features,
            "has_api": "api" in features,
            "has_frontend": "frontend" in features,
            **kwargs,
        }

        return context


# Made with Bob
