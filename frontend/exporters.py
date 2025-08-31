"""Export helpers for saving rendered diagram bytes to files for download."""
from __future__ import annotations
from typing import Dict
import tempfile
import os


EXT_MAP = {
    "pdf": "pdf",
    "tex": "tikz",  # raw tikz/latex content saved with .tikz extension
    "jpeg": "jpeg",
}

def save_outputs(outputs: Dict[str, bytes]) -> Dict[str, str]:
    paths: Dict[str, str] = {}
    base_dir = tempfile.mkdtemp(prefix="archgen_")
    for key, data in outputs.items():
        ext = EXT_MAP.get(key, key)
        path = os.path.join(base_dir, f"diagram.{ext}")
        try:
            with open(path, "wb") as f:
                f.write(data)
            paths[key] = path
        except Exception:
            # Skip file on error
            pass
    return paths

__all__ = ["save_outputs"]
