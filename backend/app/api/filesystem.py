from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.core.paths import safe_resolve

router = APIRouter()


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


def _allowed_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in settings.allowed_image_roots():
        p = Path(raw).expanduser().resolve()
        if p not in seen:
            roots.append(p)
            seen.add(p)
    return roots


@router.get("/roots")
async def list_roots():
    """Return the configured image directories — the only paths the API will browse."""
    return {
        "roots": [
            {"path": str(p), "label": p.name or str(p)}
            for p in _allowed_roots()
        ]
    }


@router.get("/browse")
async def browse_directory(path: str = Query(..., description="Directory path to browse")):
    """List subdirectories and image files inside an allowed root."""
    resolved = safe_resolve(path, settings.allowed_image_roots())
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    try:
        for entry in sorted(resolved.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith(".") or entry.is_symlink():
                continue
            try:
                if entry.is_dir():
                    entries.append({"name": entry.name, "path": str(entry), "type": "directory"})
                elif entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES:
                    entries.append({"name": entry.name, "path": str(entry), "type": "image"})
            except PermissionError:
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Parent is only exposed if it is itself inside an allowed root.
    parent_path: str | None = None
    for root in _allowed_roots():
        try:
            if resolved.parent.resolve().relative_to(root) is not None:
                parent_path = str(resolved.parent)
                break
        except ValueError:
            continue

    image_count = sum(1 for e in entries if e["type"] == "image")
    return {
        "path": str(resolved),
        "exists": True,
        "is_dir": True,
        "parent": parent_path,
        "entries": entries,
        "image_count": image_count,
    }
