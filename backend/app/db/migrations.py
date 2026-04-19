"""Apply Alembic migrations at app startup.

Handles the one-off upgrade case for deployments that were created before
Alembic was introduced: if the iqa_* tables already exist but there's no
`alembic_version` row, stamp to head instead of trying to re-create them.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import engine

logger = get_logger("migrations")

_ALEMBIC_DIR = Path(__file__).resolve().parent.parent.parent / "alembic"


def _alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return cfg


def apply_migrations() -> None:
    cfg = _alembic_config()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "iqa_scans" in table_names and "alembic_version" not in table_names:
        logger.info("Existing iqa schema detected with no alembic_version — stamping to head")
        command.stamp(cfg, "head")
    else:
        logger.info("Running alembic upgrade head")
        command.upgrade(cfg, "head")
