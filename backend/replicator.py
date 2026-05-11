import os
import shutil
import uuid
import logging

logger = logging.getLogger("Replicator")

class SwarmReplicator:
    """Packages the generated code into a sovereign downloadable asset."""
    
    @staticmethod
    def create_company_bundle(project_id: str):
        pkg_id = uuid.uuid4().hex[:6].upper()
        zip_name = f"SwarmOS_{project_id}_{pkg_id}"
        zip_output_path = f"/mnt/c/SwarmEnterprise_v2/output/{zip_name}"
        temp_dir = f"/tmp/{pkg_id}"
        
        try:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            # Copies the generated project output
            shutil.copytree(f"/mnt/c/SwarmEnterprise_v2/output/src/{project_id}", temp_dir)
            
            # Zip it up
            shutil.make_archive(zip_output_path, 'zip', temp_dir)
            shutil.rmtree(temp_dir)
            
            download_url = f"https://corp.realms2riches.com/api/download/{zip_name}.zip"
            logger.info(f"BUNDLE READY: {download_url}")
            return {"status": "success", "download_url": download_url}
        except Exception as e:
            logger.error(f"Replication failed: {e}")
            return {"status": "error", "message": str(e)}

replicator_engine = SwarmReplicator()
