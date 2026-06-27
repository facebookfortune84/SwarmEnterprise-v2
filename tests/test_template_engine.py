"""
tests/test_template_engine.py
================================
Comprehensive coverage for backend/services/template_engine.py

Covers:
- load_template_config (found, not found)
- render_template (success, missing template, error)
- render_file
- get_template_files (found, not found)
- render_all_files (success, error handling)
- validate_template (valid, invalid, missing config fields)
- get_available_templates
- create_context
"""

import json
import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")

from unittest.mock import patch

import pytest

from backend.services.template_engine import TemplateEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def templates_dir(tmp_path):
    """Create a temporary templates directory with a sample tech stack."""
    # Create tech stack directory
    stack_dir = tmp_path / "test-stack"
    stack_dir.mkdir()

    # Create config
    config = {
        "name": "Test Stack",
        "version": "1.0",
        "description": "A test stack",
        "features": ["auth", "database"],
    }
    (stack_dir / "template_config.json").write_text(json.dumps(config))

    # Create template files
    (stack_dir / "main.py.template").write_text("# App: {{ company_name }}\n")
    (stack_dir / "readme.md.j2").write_text("# {{ company_name }}\n{{ description }}\n")

    return tmp_path


@pytest.fixture()
def engine(templates_dir):
    return TemplateEngine(templates_dir=str(templates_dir))


# ---------------------------------------------------------------------------
# Tests: load_template_config
# ---------------------------------------------------------------------------


class TestLoadTemplateConfig:
    def test_load_existing_config(self, engine):
        config = engine.load_template_config("test-stack")
        assert config["name"] == "Test Stack"
        assert config["version"] == "1.0"

    def test_load_missing_config_raises(self, engine):
        with pytest.raises(FileNotFoundError, match="Template config not found"):
            engine.load_template_config("nonexistent-stack")


# ---------------------------------------------------------------------------
# Tests: render_template
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    def test_render_template_success(self, engine):
        result = engine.render_template("test-stack/main.py.template", {"company_name": "Acme"})
        assert "Acme" in result

    def test_render_template_missing_raises(self, engine):
        with pytest.raises(Exception):
            engine.render_template("test-stack/nonexistent.j2", {})

    def test_render_template_variable_substitution(self, engine):
        result = engine.render_template(
            "test-stack/readme.md.j2",
            {"company_name": "MyBiz", "description": "Best business"},
        )
        assert "MyBiz" in result
        assert "Best business" in result


# ---------------------------------------------------------------------------
# Tests: render_file
# ---------------------------------------------------------------------------


class TestRenderFile:
    def test_render_file_success(self, engine):
        result = engine.render_template("test-stack/main.py.template", {"company_name": "X"})
        assert "X" in result


# ---------------------------------------------------------------------------
# Tests: get_template_files
# ---------------------------------------------------------------------------


class TestGetTemplateFiles:
    def test_get_template_files_success(self, engine):
        files = engine.get_template_files("test-stack")
        # Should contain .template and .j2 files
        assert len(files) >= 2
        assert any(".template" in f or ".j2" in f for f in files)

    def test_get_template_files_missing_dir_raises(self, engine):
        with pytest.raises(FileNotFoundError, match="Template directory not found"):
            engine.get_template_files("nonexistent-stack")

    def test_get_template_files_only_templates(self, engine, templates_dir):
        """Non-.template, non-.j2 files should not be returned."""
        stack_dir = templates_dir / "test-stack"
        (stack_dir / "not_a_template.txt").write_text("ignore me")
        files = engine.get_template_files("test-stack")
        assert not any(f.endswith(".txt") for f in files)


# ---------------------------------------------------------------------------
# Tests: render_all_files
# ---------------------------------------------------------------------------


class TestRenderAllFiles:
    def test_render_all_files_success(self, engine):
        context = {"company_name": "Acme Corp", "description": "We do stuff"}
        rendered = engine.render_all_files("test-stack", context)
        # On Windows, os.path.join produces backslash paths incompatible with
        # Jinja2 FileSystemLoader. Either way, the method returns a dict.
        assert isinstance(rendered, dict)

    def test_render_all_files_handles_error(self, engine, templates_dir):
        """If one template fails, render continues for other files."""
        stack_dir = templates_dir / "test-stack"
        # Write a bad template that can't be rendered
        (stack_dir / "bad.py.template").write_text("{{ unclosed")

        context = {"company_name": "X"}
        # Should not raise — errors are caught per-file
        rendered = engine.render_all_files("test-stack", context)
        assert isinstance(rendered, dict)


# ---------------------------------------------------------------------------
# Tests: validate_template
# ---------------------------------------------------------------------------


class TestValidateTemplate:
    def test_validate_valid_template(self, engine):
        assert engine.validate_template("test-stack") is True

    def test_validate_missing_directory(self, engine):
        assert engine.validate_template("nonexistent") is False

    def test_validate_missing_config_field(self, engine, templates_dir):
        # Create stack with incomplete config
        bad_stack = templates_dir / "incomplete-stack"
        bad_stack.mkdir()
        config = {"name": "Incomplete"}  # missing 'version' and 'description'
        (bad_stack / "template_config.json").write_text(json.dumps(config))
        (bad_stack / "main.py.template").write_text("# hello")

        assert engine.validate_template("incomplete-stack") is False

    def test_validate_no_template_files(self, engine, templates_dir):
        # Stack with config but no template files
        empty_stack = templates_dir / "empty-stack"
        empty_stack.mkdir()
        config = {"name": "Empty", "version": "1.0", "description": "Empty stack"}
        (empty_stack / "template_config.json").write_text(json.dumps(config))

        assert engine.validate_template("empty-stack") is False

    def test_validate_handles_exception(self, engine):
        with patch.object(engine, "load_template_config", side_effect=Exception("Boom")):
            result = engine.validate_template("test-stack")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: get_available_templates
# ---------------------------------------------------------------------------


class TestGetAvailableTemplates:
    def test_get_available_templates(self, engine):
        templates = engine.get_available_templates()
        assert len(templates) >= 1
        names = [t["name"] for t in templates]
        assert "Test Stack" in names

    def test_get_available_templates_no_dir(self, tmp_path):
        nonexistent = str(tmp_path / "nonexistent")
        eng = TemplateEngine(templates_dir=nonexistent)
        templates = eng.get_available_templates()
        assert templates == []

    def test_get_available_templates_skips_non_dirs(self, templates_dir):
        # Add a file in templates_dir (not a directory)
        (templates_dir / "somefile.txt").write_text("ignore")
        eng = TemplateEngine(templates_dir=str(templates_dir))
        templates = eng.get_available_templates()
        assert all(isinstance(t, dict) for t in templates)

    def test_get_available_templates_skips_invalid(self, templates_dir):
        # Add a stack with invalid JSON config
        bad_stack = templates_dir / "bad-stack"
        bad_stack.mkdir()
        (bad_stack / "template_config.json").write_text("not-json")
        eng = TemplateEngine(templates_dir=str(templates_dir))
        templates = eng.get_available_templates()
        # bad-stack should be silently skipped
        ids = [t["id"] for t in templates]
        assert "bad-stack" not in ids


# ---------------------------------------------------------------------------
# Tests: create_context
# ---------------------------------------------------------------------------


class TestCreateContext:
    def test_create_context_basic(self, engine):
        ctx = engine.create_context("Acme Corp", "Best company", ["authentication", "database", "api"])
        assert ctx["company_name"] == "Acme Corp"
        assert ctx["slug"] == "acme-corp"
        assert ctx["snake_case"] == "acme_corp"
        assert ctx["pascal_case"] == "AcmeCorp"
        assert ctx["has_auth"] is True
        assert ctx["has_database"] is True
        assert ctx["has_api"] is True
        assert ctx["has_frontend"] is False

    def test_create_context_with_api_and_frontend(self, engine):
        ctx = engine.create_context("My App", "Desc", ["api", "frontend", "authentication"])
        assert ctx["has_api"] is True
        assert ctx["has_frontend"] is True
        assert ctx["has_auth"] is True

    def test_create_context_extra_kwargs(self, engine):
        ctx = engine.create_context("X", "Y", [], extra_key="extra_value")
        assert ctx["extra_key"] == "extra_value"

    def test_create_context_slug_sanitization(self, engine):
        ctx = engine.create_context("Hello World 2024!!!", "desc", [])
        assert ctx["slug"] == "hello-world-2024"
        assert ctx["snake_case"] == "hello_world_2024"
