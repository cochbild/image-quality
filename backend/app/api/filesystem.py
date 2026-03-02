import os
import sys
import string
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/drives")
async def list_drives():
    """List available drives (Windows) or root mounts."""
    if sys.platform == "win32":
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append({"path": drive, "label": f"{letter}:"})
        return {"drives": drives}
    return {"drives": [{"path": "/", "label": "/"}]}


@router.get("/browse")
async def browse_directory(path: str = Query(..., description="Directory path to browse")):
    """List subdirectories and image count in a given directory."""
    dir_path = Path(path)
    if not dir_path.exists():
        return {"path": str(dir_path), "exists": False, "parent": str(dir_path.parent), "entries": []}
    if not dir_path.is_dir():
        return {"path": str(dir_path), "exists": True, "is_dir": False, "parent": str(dir_path.parent), "entries": []}

    entries = []
    try:
        for entry in sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                        "type": "directory",
                    })
                elif entry.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}:
                    entries.append({
                        "name": entry.name,
                        "path": str(entry),
                        "type": "image",
                    })
            except PermissionError:
                continue
    except PermissionError:
        return {"path": str(dir_path), "exists": True, "is_dir": True, "error": "Permission denied", "parent": str(dir_path.parent), "entries": []}

    image_count = sum(1 for e in entries if e["type"] == "image")

    return {
        "path": str(dir_path),
        "exists": True,
        "is_dir": True,
        "parent": str(dir_path.parent),
        "entries": entries,
        "image_count": image_count,
    }
