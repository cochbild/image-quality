import shutil
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger("file_manager")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


def list_images(directory: str) -> list[Path]:
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    # Skip symlinks — safe_resolve at the API layer ensures the directory is
    # inside an allowed root, but entries inside could still be symlinks
    # pointing elsewhere.
    images = [
        f for f in dir_path.iterdir()
        if f.is_file() and not f.is_symlink() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda p: p.name)


def move_image(src: str, dest_dir: str) -> str:
    src_path = Path(src)
    if src_path.is_symlink():
        raise ValueError(f"Refusing to move symlink: {src_path}")
    dest_dir_path = Path(dest_dir)
    dest_dir_path.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir_path / src_path.name
    if dest_path.exists():
        stem, suffix = src_path.stem, src_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = dest_dir_path / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.move(str(src_path), str(dest_path))
    logger.info(f"Moved {src_path.name} -> {dest_path}")
    return str(dest_path)
