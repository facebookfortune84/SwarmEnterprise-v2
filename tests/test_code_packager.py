"""
tests/test_code_packager.py
=============================
Comprehensive coverage for backend/services/code_packager.py

Covers:
- create_archive
- extract_archive
- validate_archive
- get_archive_info
- _generate_readme
- _generate_deploy_script
- _generate_env_example (postgres, mongo, react stacks)
"""

import json
import os
import zipfile

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")

import pytest

from backend.services.code_packager import CodePackager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def packager(tmp_path):
    return CodePackager(output_dir=str(tmp_path))


def _sample_files():
    return {
        "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "frontend/index.html": "<html><body>Hello</body></html>\n",
        "docker-compose.yml": "version: '3'\nservices:\n  web:\n    image: nginx\n",
    }


def _sample_metadata(tech_stack="fastapi-react-postgres"):
    return {
        "name": "Test Company",
        "description": "A test company",
        "tech_stack": tech_stack,
        "features": ["auth", "database"],
    }


# ---------------------------------------------------------------------------
# Tests: create_archive
# ---------------------------------------------------------------------------


class TestCreateArchive:
    def test_create_archive_success(self, packager, tmp_path):
        files = _sample_files()
        metadata = _sample_metadata()
        path = packager.create_archive("company-001", files, metadata)

        assert os.path.exists(path)
        assert path.endswith(".zip")

        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            assert "README.md" in names
            assert "deploy.sh" in names
            assert "metadata.json" in names
            assert ".env.example" in names
            assert "backend/main.py" in names

    def test_create_archive_all_source_files_present(self, packager, tmp_path):
        files = _sample_files()
        path = packager.create_archive("c001", files, _sample_metadata())

        with zipfile.ZipFile(path, "r") as zf:
            for file_path in files:
                assert file_path in zf.namelist()

    def test_create_archive_readme_content(self, packager, tmp_path):
        metadata = _sample_metadata()
        path = packager.create_archive("c002", {}, metadata)

        with zipfile.ZipFile(path, "r") as zf:
            readme = zf.read("README.md").decode()
        assert "Test Company" in readme
        assert "fastapi-react-postgres" in readme

    def test_create_archive_metadata_json_content(self, packager, tmp_path):
        metadata = _sample_metadata()
        path = packager.create_archive("c003", {}, metadata)

        with zipfile.ZipFile(path, "r") as zf:
            meta_content = json.loads(zf.read("metadata.json"))
        assert meta_content["name"] == "Test Company"

    def test_create_archive_empty_files(self, packager, tmp_path):
        """Archive with no source files still has README/metadata."""
        path = packager.create_archive("c-err", {}, _sample_metadata())
        with zipfile.ZipFile(path, "r") as zf:
            assert "README.md" in zf.namelist()


# ---------------------------------------------------------------------------
# Tests: _generate_env_example (tech stack variations)
# ---------------------------------------------------------------------------


class TestGenerateEnvExample:
    def test_postgres_stack(self, packager):
        env = packager._generate_env_example({"tech_stack": "fastapi-postgres"})
        assert "POSTGRES_VERSION" in env

    def test_mongo_stack(self, packager):
        env = packager._generate_env_example({"tech_stack": "fastapi-mongo"})
        assert "MONGO_URL" in env

    def test_react_stack(self, packager):
        env = packager._generate_env_example({"tech_stack": "fastapi-react"})
        assert "REACT_APP_API_URL" in env

    def test_plain_stack(self, packager):
        env = packager._generate_env_example({"tech_stack": "plain"})
        assert "DATABASE_URL" in env
        assert "POSTGRES_VERSION" not in env

    def test_empty_tech_stack(self, packager):
        env = packager._generate_env_example({})
        assert "DATABASE_URL" in env


# ---------------------------------------------------------------------------
# Tests: _generate_readme
# ---------------------------------------------------------------------------


class TestGenerateReadme:
    def test_readme_with_all_fields(self, packager):
        meta = {
            "name": "MyApp",
            "description": "Amazing app",
            "tech_stack": "django-react",
            "features": ["auth", "billing"],
        }
        readme = packager._generate_readme(meta)
        assert "MyApp" in readme
        assert "Amazing app" in readme
        assert "django-react" in readme
        assert "auth" in readme

    def test_readme_empty_features(self, packager):
        meta = {"name": "X", "description": "Y", "tech_stack": "Z", "features": []}
        readme = packager._generate_readme(meta)
        assert "Standard features" in readme

    def test_readme_minimal_metadata(self, packager):
        readme = packager._generate_readme({})
        assert "Generated Company" in readme


# ---------------------------------------------------------------------------
# Tests: _generate_deploy_script
# ---------------------------------------------------------------------------


class TestGenerateDeployScript:
    def test_deploy_script_contains_docker(self, packager):
        script = packager._generate_deploy_script({})
        assert "docker" in script.lower()
        assert "docker-compose" in script


# ---------------------------------------------------------------------------
# Tests: extract_archive
# ---------------------------------------------------------------------------


class TestExtractArchive:
    def test_extract_archive_success(self, packager, tmp_path):
        # First create an archive
        files = {"src/app.py": "print('hello')"}
        metadata = _sample_metadata()
        archive_path = packager.create_archive("ext-001", files, metadata)

        extract_dir = str(tmp_path / "extracted")
        extracted = packager.extract_archive(archive_path, extract_dir)

        assert len(extracted) > 0
        assert "src/app.py" in extracted
        assert os.path.exists(os.path.join(extract_dir, "src/app.py"))

    def test_extract_archive_not_found_raises(self, packager, tmp_path):
        with pytest.raises(Exception):
            packager.extract_archive("/nonexistent/file.zip", str(tmp_path / "out"))


# ---------------------------------------------------------------------------
# Tests: validate_archive
# ---------------------------------------------------------------------------


class TestValidateArchive:
    def test_validate_valid_archive(self, packager, tmp_path):
        files = {}
        metadata = _sample_metadata()
        archive_path = packager.create_archive("val-001", files, metadata)
        assert packager.validate_archive(archive_path) is True

    def test_validate_missing_readme(self, packager, tmp_path):
        archive_path = str(tmp_path / "missing-readme.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("metadata.json", json.dumps({"name": "x"}))
        assert packager.validate_archive(archive_path) is False

    def test_validate_missing_metadata(self, packager, tmp_path):
        archive_path = str(tmp_path / "missing-meta.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("README.md", "# Hello")
        assert packager.validate_archive(archive_path) is False

    def test_validate_metadata_missing_name_field(self, packager, tmp_path):
        archive_path = str(tmp_path / "no-name.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("README.md", "# Hello")
            zf.writestr("metadata.json", json.dumps({"version": "1.0"}))
        assert packager.validate_archive(archive_path) is False

    def test_validate_non_zip_raises_false(self, packager, tmp_path):
        bad_path = str(tmp_path / "bad.zip")
        with open(bad_path, "w") as f:
            f.write("not a zip file")
        result = packager.validate_archive(bad_path)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: get_archive_info
# ---------------------------------------------------------------------------


class TestGetArchiveInfo:
    def test_get_archive_info_success(self, packager, tmp_path):
        files = {"src/app.py": "print('hi')"}
        metadata = _sample_metadata()
        archive_path = packager.create_archive("info-001", files, metadata)

        info = packager.get_archive_info(archive_path)
        assert "metadata" in info
        assert info["file_count"] > 0
        assert info["size_bytes"] > 0
        assert info["size_mb"] >= 0
        assert isinstance(info["files"], list)

    def test_get_archive_info_error_raises(self, packager, tmp_path):
        with pytest.raises(Exception):
            packager.get_archive_info("/nonexistent/file.zip")
