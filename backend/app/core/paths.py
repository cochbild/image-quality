from pathlib import Path
from typing import Iterable

from fastapi import HTTPException


def safe_resolve(path: str | Path, allowed_roots: Iterable[str | Path]) -> Path:
    """Resolve `path` and verify it falls inside one of `allowed_roots`.

    Returns the resolved Path on success. Raises HTTPException(400) if the
    path escapes every allowed root (or if no roots were supplied).
    """
    resolved = Path(path).expanduser().resolve()
    roots = [Path(r).expanduser().resolve() for r in allowed_roots if r]
    if not roots:
        raise HTTPException(status_code=500, detail="No allowed roots configured")
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail="Path is outside the allowed directories")


def contains_symlink(path: Path, up_to_root: Path) -> bool:
    """Walk `path` upward until `up_to_root` and return True if any segment is a symlink."""
    p = path
    root = up_to_root.resolve()
    while True:
        if p.is_symlink():
            return True
        if p == root or p.parent == p:
            return False
        p = p.parent
