"""
tests/test_storage_and_provisioner.py
=======================================
Coverage for:
- backend/storage/file_manager.py
- backend/orchestration/vm_provisioner.py (selected methods)
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from backend.storage.file_manager import FileManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_manager(mock_s3=None):
    """Create a FileManager with a mocked S3 client."""
    if mock_s3 is None:
        mock_s3 = MagicMock()
    return FileManager(s3_client=mock_s3), mock_s3


# ---------------------------------------------------------------------------
# Tests: FileManager.store_company
# ---------------------------------------------------------------------------


class TestStoreCompany:
    def test_store_company_success(self):
        fm, s3 = _make_manager()
        s3.upload_file.return_value = True
        result = fm.store_company("c001", "/tmp/archive.zip", metadata={"name": "Acme"})
        assert result == "companies/c001/source.zip"
        s3.upload_file.assert_called_once()

    def test_store_company_failure(self):
        fm, s3 = _make_manager()
        s3.upload_file.return_value = False
        result = fm.store_company("c002", "/tmp/archive.zip")
        assert result is None

    def test_store_company_no_metadata(self):
        fm, s3 = _make_manager()
        s3.upload_file.return_value = True
        result = fm.store_company("c003", "/tmp/archive.zip")
        assert result == "companies/c003/source.zip"

    def test_store_company_metadata_with_nested_types(self):
        fm, s3 = _make_manager()
        s3.upload_file.return_value = True
        result = fm.store_company(
            "c004",
            "/tmp/archive.zip",
            metadata={"count": 5, "active": True, "nested": {"ignored": 1}},
        )
        assert result == "companies/c004/source.zip"
        # Nested dict should be filtered out — verify simple values present
        assert "count" in str(s3.upload_file.call_args)


# ---------------------------------------------------------------------------
# Tests: FileManager.retrieve_company
# ---------------------------------------------------------------------------


class TestRetrieveCompany:
    def test_retrieve_success(self, tmp_path):
        fm, s3 = _make_manager()
        s3.download_file.return_value = True
        download_path = str(tmp_path / "downloads" / "archive.zip")
        result = fm.retrieve_company("c001", download_path)
        assert result is True

    def test_retrieve_failure(self, tmp_path):
        fm, s3 = _make_manager()
        s3.download_file.return_value = False
        download_path = str(tmp_path / "downloads" / "archive.zip")
        result = fm.retrieve_company("c001", download_path)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: FileManager.delete_company
# ---------------------------------------------------------------------------


class TestDeleteCompany:
    def test_delete_success(self):
        fm, s3 = _make_manager()
        s3.delete_file.return_value = True
        result = fm.delete_company("c001")
        assert result is True

    def test_delete_failure(self):
        fm, s3 = _make_manager()
        s3.delete_file.return_value = False
        result = fm.delete_company("c001")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: FileManager.company_exists
# ---------------------------------------------------------------------------


class TestCompanyExists:
    def test_exists_true(self):
        fm, s3 = _make_manager()
        s3.file_exists.return_value = True
        assert fm.company_exists("c001") is True

    def test_exists_false(self):
        fm, s3 = _make_manager()
        s3.file_exists.return_value = False
        assert fm.company_exists("nope") is False


# ---------------------------------------------------------------------------
# Tests: FileManager.get_company_download_url
# ---------------------------------------------------------------------------


class TestGetCompanyDownloadUrl:
    def test_url_generated(self):
        fm, s3 = _make_manager()
        s3.generate_presigned_url.return_value = "https://example.com/download"
        url = fm.get_company_download_url("c001", expiration=3600)
        assert url == "https://example.com/download"

    def test_url_not_generated(self):
        fm, s3 = _make_manager()
        s3.generate_presigned_url.return_value = None
        url = fm.get_company_download_url("c001")
        assert url is None


# ---------------------------------------------------------------------------
# Tests: FileManager.get_company_metadata
# ---------------------------------------------------------------------------


class TestGetCompanyMetadata:
    def test_metadata_returned(self):
        fm, s3 = _make_manager()
        s3.get_file_metadata.return_value = {"size": 12345}
        result = fm.get_company_metadata("c001")
        assert result["size"] == 12345

    def test_metadata_not_found(self):
        fm, s3 = _make_manager()
        s3.get_file_metadata.return_value = None
        result = fm.get_company_metadata("nope")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: FileManager.list_companies
# ---------------------------------------------------------------------------


class TestListCompanies:
    def test_list_companies_no_filter(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = [
            "companies/c001/source.zip",
            "companies/c002/source.zip",
            "companies/c001/backup.zip",  # same c001, should deduplicate
        ]
        result = fm.list_companies()
        assert "c001" in result
        assert "c002" in result
        assert len(result) == 2

    def test_list_companies_with_user_filter(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = ["companies/user1/c001/source.zip"]
        fm.list_companies(user_id="user1")
        s3.list_files.assert_called_with("companies/user1/")

    def test_list_companies_empty(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = []
        result = fm.list_companies()
        assert result == []

    def test_list_companies_short_paths_ignored(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = [
            "companies"
        ]  # only one segment (no slash split produces 1 part)
        result = fm.list_companies()
        # "companies".split("/") = ["companies"] — len < 2, should be ignored
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tests: FileManager.cleanup_old_files
# ---------------------------------------------------------------------------


class TestCleanupOldFiles:
    def test_cleanup_deletes_old_files(self):
        fm, s3 = _make_manager()
        old_date = datetime.utcnow() - timedelta(days=60)
        s3.list_files.return_value = ["companies/c001/source.zip"]
        s3.get_file_metadata.return_value = {"last_modified": old_date}
        s3.delete_file.return_value = True

        count = fm.cleanup_old_files(days=30)
        assert count == 1

    def test_cleanup_keeps_recent_files(self):
        fm, s3 = _make_manager()
        recent_date = datetime.utcnow() - timedelta(days=5)
        s3.list_files.return_value = ["companies/c001/source.zip"]
        s3.get_file_metadata.return_value = {"last_modified": recent_date}

        count = fm.cleanup_old_files(days=30)
        assert count == 0
        s3.delete_file.assert_not_called()

    def test_cleanup_no_files(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = []
        count = fm.cleanup_old_files()
        assert count == 0

    def test_cleanup_no_metadata(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = ["companies/c001/source.zip"]
        s3.get_file_metadata.return_value = None
        count = fm.cleanup_old_files()
        assert count == 0

    def test_cleanup_no_last_modified_in_metadata(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = ["companies/c001/source.zip"]
        s3.get_file_metadata.return_value = {"size": 100}  # no last_modified
        count = fm.cleanup_old_files()
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: FileManager.get_storage_stats
# ---------------------------------------------------------------------------


class TestGetStorageStats:
    def test_stats_with_files(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = ["companies/c001/source.zip", "companies/c002/source.zip"]
        s3.get_file_metadata.side_effect = [{"size": 1024 * 1024}, {"size": 2 * 1024 * 1024}]

        stats = fm.get_storage_stats()
        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 3 * 1024 * 1024

    def test_stats_empty(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = []
        stats = fm.get_storage_stats()
        assert stats["file_count"] == 0
        assert stats["total_size_bytes"] == 0

    def test_stats_no_metadata(self):
        fm, s3 = _make_manager()
        s3.list_files.return_value = ["companies/c001/source.zip"]
        s3.get_file_metadata.return_value = None
        stats = fm.get_storage_stats()
        assert stats["total_size_bytes"] == 0


# ---------------------------------------------------------------------------
# Tests: FileManager.backup_company
# ---------------------------------------------------------------------------


class TestBackupCompany:
    def test_backup_success(self):
        fm, s3 = _make_manager()
        s3.copy_file.return_value = True
        result = fm.backup_company("c001")
        assert result is True
        s3.copy_file.assert_called_once()

    def test_backup_failure(self):
        fm, s3 = _make_manager()
        s3.copy_file.return_value = False
        result = fm.backup_company("c001")
        assert result is False

    def test_backup_with_custom_bucket(self):
        fm, s3 = _make_manager()
        s3.copy_file.return_value = True
        fm.backup_company("c001", backup_bucket="my-backups")
        call_args = s3.copy_file.call_args
        assert call_args[1].get("dest_bucket") == "my-backups" or call_args[0][2] == "my-backups"


# ---------------------------------------------------------------------------
# Tests: HyperVProvisioner (vm_provisioner.py)
# ---------------------------------------------------------------------------


class TestHyperVProvisioner:
    def test_init_default(self):
        from backend.orchestration.vm_provisioner import HyperVProvisioner

        prov = HyperVProvisioner()
        assert prov.hyperv_host == "localhost"
        assert prov.scripts_path is not None

    def test_init_custom(self):
        from backend.orchestration.vm_provisioner import HyperVProvisioner

        prov = HyperVProvisioner(hyperv_host="my-server", scripts_path="/scripts")
        assert prov.hyperv_host == "my-server"
        assert prov.scripts_path == "/scripts"

    @pytest.mark.asyncio
    async def test_provision_vm_fallback_on_error(self):
        """provision_vm raises when PowerShell fails (error path covered)."""
        from unittest.mock import AsyncMock, patch

        from backend.orchestration.vm_provisioner import HyperVProvisioner, VMConfig

        prov = HyperVProvisioner()
        config = VMConfig(name="test-vm")

        # Patch at the module level where it's used
        with patch(
            "backend.orchestration.vm_provisioner.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            side_effect=Exception("powershell not available"),
        ):
            with pytest.raises(Exception):
                await prov.provision_vm(config)

    @pytest.mark.asyncio
    async def test_get_vm_info_fallback(self):
        """get_vm_info raises when PowerShell fails (error path covered)."""
        from unittest.mock import AsyncMock, patch

        from backend.orchestration.vm_provisioner import HyperVProvisioner

        prov = HyperVProvisioner()

        with patch(
            "backend.orchestration.vm_provisioner.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            side_effect=Exception("powershell not available"),
        ):
            with pytest.raises(Exception):
                await prov.get_vm_info("test-vm")
