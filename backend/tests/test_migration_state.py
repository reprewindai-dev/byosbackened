from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from core.services.migration_state import audit_migration_state


ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _seed_revision(engine, revisions: list[str]) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        for revision in revisions:
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )


def test_audit_migration_state_passes_when_current_matches_head():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _seed_revision(engine, ["013"])

    result = audit_migration_state(engine, alembic_ini_path=ALEMBIC_INI)

    assert result.current_revisions == ["013"]
    assert result.head_revisions == ["013"]
    assert result.is_at_head is True


def test_audit_migration_state_flags_drift():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _seed_revision(engine, ["012"])

    result = audit_migration_state(engine, alembic_ini_path=ALEMBIC_INI)

    assert result.current_revisions == ["012"]
    assert result.head_revisions == ["013"]
    assert result.is_at_head is False
    assert "drift detected" in result.summary().lower()


def test_audit_migration_state_handles_missing_revision_table():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    result = audit_migration_state(engine, alembic_ini_path=ALEMBIC_INI)

    assert result.current_revisions == []
    assert result.head_revisions == ["013"]
    assert result.has_revision_table is False
