"""Helpers for auditing live Alembic migration state."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@dataclass(slots=True)
class MigrationAuditResult:
    current_revisions: list[str]
    head_revisions: list[str]

    @property
    def is_at_head(self) -> bool:
        return self.current_revisions == self.head_revisions

    @property
    def has_revision_table(self) -> bool:
        return bool(self.current_revisions)

    def summary(self) -> str:
        current = ", ".join(self.current_revisions) if self.current_revisions else "none"
        head = ", ".join(self.head_revisions) if self.head_revisions else "none"
        if self.is_at_head:
            return f"Alembic current={current} matches head={head}"
        return f"Alembic drift detected: current={current}, head={head}"


def _default_alembic_ini() -> Path:
    return Path(__file__).resolve().parents[2] / "alembic.ini"


def resolve_alembic_heads(alembic_ini_path: str | Path | None = None) -> list[str]:
    ini_path = Path(alembic_ini_path or _default_alembic_ini())
    cfg = Config(str(ini_path))
    script_location = cfg.get_main_option("script_location")
    if script_location and not Path(script_location).is_absolute():
        cfg.set_main_option("script_location", str((ini_path.parent / script_location).resolve()))
    script = ScriptDirectory.from_config(cfg)
    return sorted(script.get_heads())


def read_current_revisions(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        inspector = inspect(conn)
        if "alembic_version" not in inspector.get_table_names():
            return []
        rows = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
        return sorted(row[0] for row in rows if row[0])


def audit_migration_state(
    engine: Engine,
    *,
    alembic_ini_path: str | Path | None = None,
) -> MigrationAuditResult:
    return MigrationAuditResult(
        current_revisions=read_current_revisions(engine),
        head_revisions=resolve_alembic_heads(alembic_ini_path),
    )
