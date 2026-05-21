import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Replicator")

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUTPUT = _REPO_ROOT / "output"


def _output_root() -> Path:
    out = os.getenv("SWARM_OUTPUT_DIR", "").strip()
    return Path(out) if out else _DEFAULT_OUTPUT


class SwarmReplicator:
    """Packages the generated code into a sovereign downloadable asset."""

    @staticmethod
    def create_company_bundle(project_id: str, customer_email: Optional[str] = None):
        pkg_id = uuid.uuid4().hex[:6].upper()
        zip_name = f"SwarmOS_{project_id}_{pkg_id}"
        output_root = _output_root()
        src_dir = output_root / "src" / project_id
        zip_base = output_root / zip_name
        temp_dir = Path(tempfile.mkdtemp(prefix=f"swarm_{pkg_id}_"))

        try:
            if not src_dir.is_dir():
                raise FileNotFoundError(f"Project output not found: {src_dir}")

            shutil.copytree(src_dir, temp_dir, dirs_exist_ok=True)
            archive_path = shutil.make_archive(str(zip_base), "zip", str(temp_dir))
            shutil.rmtree(temp_dir, ignore_errors=True)

            download_url = f"https://corp.realms2riches.com/api/download/{zip_name}.zip"
            logger.info("BUNDLE READY: %s (%s)", download_url, archive_path)

            try:
                from backend.db.linear_engine import get_swarm_db

                db = get_swarm_db()
                db.create_project(
                    project_id,
                    stripe_session=None,
                    customer_email=customer_email,
                    product_id=None,
                    price_id=None,
                    metadata=None,
                )
            except Exception:
                logger.debug("No DB available or failed to persist project record")

            return {"status": "success", "download_url": download_url}
        except Exception as e:
            logger.error("Replication failed: %s", e)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {"status": "error", "message": str(e)}


replicator_engine = SwarmReplicator()
