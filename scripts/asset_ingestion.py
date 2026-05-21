import os
import json
import shutil
from datetime import datetime

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_DIR = os.getenv("SWARM_ORACLE_SOURCE", os.path.join(os.path.dirname(_REPO), "oracle"))
TARGET_DIR = os.getenv("SWARM_ASSETS_DIR", os.path.join(_REPO, "assets"))
REGISTRY_FILE = os.path.join(TARGET_DIR, "registry.json")


def scan_and_ingest():
    print("==========================================")
    print(" SWARM OS: ORACLE ASSET INGESTION PIPELINE")
    print("==========================================")

    if not os.path.exists(SOURCE_DIR):
        print(f"[!] ERROR: Source directory {SOURCE_DIR} not found.")
        return

    registry = {
        "metadata": {"ingested_at": datetime.now().isoformat(), "version": "1.0"},
        "prompts": [],
        "sops": [],
        "tools": [],
    }

    stats = {"prompts": 0, "sops": 0, "tools": 0}

    for cat in ["prompts", "sops", "tools"]:
        cat_path = os.path.join(TARGET_DIR, cat)
        os.makedirs(cat_path, exist_ok=True)

    print("[*] Scanning Oracle Database...")

    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            source_path = os.path.join(root, file)
            file_ext = file.split(".")[-1].lower()

            if "prompts" in root.lower() or "prompt" in file.lower():
                category = "prompts"
            elif "sops" in root.lower() or "sop" in root.lower() or file_ext == "md":
                category = "sops"
            elif "tools" in root.lower() or file_ext == "json":
                category = "tools"
            else:
                continue

            target_path = os.path.join(TARGET_DIR, category, file)
            shutil.copy2(source_path, target_path)

            registry[category].append(
                {"name": file, "path": f"assets/{category}/{file}", "type": file_ext}
            )
            stats[category] += 1

    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=4)

    print("\n[✓] INGESTION COMPLETE!")
    print(f"    - Prompts processed: {stats['prompts']}")
    print(f"    - SOPs processed:    {stats['sops']}")
    print(f"    - Tools processed:   {stats['tools']}")
    print(f"    - Registry written:  {REGISTRY_FILE}")


if __name__ == "__main__":
    scan_and_ingest()
