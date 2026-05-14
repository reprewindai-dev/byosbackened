"""Test migration reversibility - upgrade → downgrade → upgrade."""
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db.session import Base
from core.config import get_settings
import os
import tempfile
import shutil

settings = get_settings()


@pytest.fixture
def temp_db():
    """Create temporary database for migration testing."""
    if not settings.database_url.startswith("postgresql"):
        pytest.skip("Migration reversibility tests require a PostgreSQL test database")

    # Create temporary database URL
    db_url = settings.database_url.replace("/", "/test_migration_")
    
    # Create engine
    engine = create_engine(db_url)
    
    # Drop all tables if they exist
    Base.metadata.drop_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def alembic_cfg(temp_db):
    """Create Alembic config for testing."""
    # Get alembic.ini path
    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    
    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", str(temp_db.url))
    
    return cfg


def test_migration_reversibility(temp_db, alembic_cfg):
    """
    Test that migration can be reversed and reapplied.
    
    Steps:
    1. Run upgrade to head
    2. Verify tables exist
    3. Run downgrade
    4. Verify tables are removed
    5. Run upgrade again
    6. Verify tables exist again
    """
    Session = sessionmaker(bind=temp_db)
    session = Session()
    
    try:
        # Step 1: Run upgrade to head
        command.upgrade(alembic_cfg, "head")
        
        # Step 2: Verify tables exist
        tables_to_check = [
            "routing_strategies",
            "traffic_patterns",
            "anomalies",
            "savings_reports",
        ]
        
        for table_name in tables_to_check:
            result = session.execute(
                text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            )
            exists = result.scalar()
            assert exists, f"Table {table_name} should exist after upgrade"
        
        # Verify indexes exist
        indexes_to_check = [
            ("routing_strategies", "ix_routing_strategies_workspace_id"),
            ("routing_strategies", "idx_routing_strategies_workspace_op"),
            ("traffic_patterns", "ix_traffic_patterns_workspace_id"),
            ("traffic_patterns", "idx_traffic_patterns_workspace_op"),
            ("anomalies", "ix_anomalies_workspace_id"),
            ("anomalies", "idx_anomalies_workspace_detected"),
            ("savings_reports", "ix_savings_reports_workspace_id"),
            ("savings_reports", "idx_savings_reports_workspace_period"),
        ]
        
        for table_name, index_name in indexes_to_check:
            result = session.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_indexes 
                        WHERE tablename = '{table_name}' AND indexname = '{index_name}'
                    )
                """)
            )
            exists = result.scalar()
            assert exists, f"Index {index_name} on {table_name} should exist after upgrade"
        
        # Verify foreign keys exist
        fk_to_check = [
            ("routing_strategies", "workspace_id", "workspaces", "id"),
            ("traffic_patterns", "workspace_id", "workspaces", "id"),
            ("anomalies", "workspace_id", "workspaces", "id"),
            ("savings_reports", "workspace_id", "workspaces", "id"),
        ]
        
        for table_name, column_name, ref_table, ref_column in fk_to_check:
            result = session.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                            ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.table_name = '{table_name}'
                            AND kcu.column_name = '{column_name}'
                            AND tc.constraint_type = 'FOREIGN KEY'
                            AND kcu.referenced_table_name = '{ref_table}'
                            AND kcu.referenced_column_name = '{ref_column}'
                    )
                """)
            )
            exists = result.scalar()
            assert exists, (
                f"Foreign key {table_name}.{column_name} -> {ref_table}.{ref_column} "
                f"should exist after upgrade"
            )
        
        # Step 3: Run downgrade
        command.downgrade(alembic_cfg, "-1")
        
        # Step 4: Verify tables are removed
        for table_name in tables_to_check:
            result = session.execute(
                text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            )
            exists = result.scalar()
            assert not exists, f"Table {table_name} should not exist after downgrade"
        
        # Step 5: Run upgrade again
        command.upgrade(alembic_cfg, "head")
        
        # Step 6: Verify tables exist again
        for table_name in tables_to_check:
            result = session.execute(
                text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            )
            exists = result.scalar()
            assert exists, f"Table {table_name} should exist after second upgrade"
        
    finally:
        session.close()


def test_migration_enum_types(temp_db, alembic_cfg):
    """Test that enum types are created and dropped correctly."""
    Session = sessionmaker(bind=temp_db)
    session = Session()
    
    try:
        # Run upgrade
        command.upgrade(alembic_cfg, "head")
        
        # Verify enum types exist
        enum_types = [
            "anomalyseverity",
            "anomalytype",
            "anomalystatus",
        ]
        
        for enum_name in enum_types:
            result = session.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_type WHERE typname = '{enum_name}'
                    )
                """)
            )
            exists = result.scalar()
            assert exists, f"Enum type {enum_name} should exist after upgrade"
        
        # Run downgrade
        command.downgrade(alembic_cfg, "-1")
        
        # Verify enum types are removed
        for enum_name in enum_types:
            result = session.execute(
                text(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_type WHERE typname = '{enum_name}'
                    )
                """)
            )
            exists = result.scalar()
            assert not exists, f"Enum type {enum_name} should not exist after downgrade"
        
    finally:
        session.close()
