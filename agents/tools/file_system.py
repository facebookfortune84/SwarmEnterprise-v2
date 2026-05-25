import hashlib
import os

from langchain.tools import tool

BASE_OUTPUT_DIR = os.path.join(
    os.getenv("SWARM_OUTPUT_DIR", os.path.join(os.getcwd(), "output")),
    "src",
)


@tool("write_enterprise_file")
def write_enterprise_file(path: str, content: str) -> str:
    """Physically writes source code to disk."""
    try:
        full_path = os.path.join(BASE_OUTPUT_DIR, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        file_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"SUCCESS: Wrote {path}. SHA256: {file_hash}"
    except Exception as e:
        return f"ERROR: Write failed. {str(e)}"


@tool("read_enterprise_file")
def read_enterprise_file(path: str) -> str:
    """Reads code from the disk for auditing."""
    try:
        full_path = os.path.join(BASE_OUTPUT_DIR, path)
        if not os.path.exists(full_path):
            return f"ERROR: {path} not found on disk."
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: Read failed. {str(e)}"
