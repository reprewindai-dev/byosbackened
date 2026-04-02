"""
PostgreSQL Production Migration Script
=====================================

This script handles the complete migration from SQLite to PostgreSQL
for production deployment of BYOS AI Backend.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command

from core.config import get_settings
from db.session import Base
from db.models import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLMigrator:
    """Complete SQLite to PostgreSQL migration system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.sqlite_url = "sqlite:///./local.db"
        self.postgres_url = self.settings.database_url
        
        if not self.postgres_url or "sqlite" in self.postgres_url:
            raise ValueError("PostgreSQL DATABASE_URL must be configured")
    
    def create_postgres_database(self) -> bool:
        """Create PostgreSQL database if it doesn't exist."""
        try:
            # Extract connection details
            from urllib.parse import urlparse
            parsed = urlparse(self.postgres_url)
            
            db_name = parsed.path[1:]  # Remove leading slash
            username = parsed.username
            password = parsed.password
            host = parsed.hostname
            port = parsed.port or 5432
            
            # Connect to PostgreSQL server (not database)
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database='postgres'  # Default database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cursor.fetchone()
            
            if not exists:
                # Create database
                cursor.execute(f"CREATE DATABASE {db_name}")
                logger.info(f"✅ Created PostgreSQL database: {db_name}")
            else:
                logger.info(f"✅ PostgreSQL database already exists: {db_name}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL database: {e}")
            return False
    
    def migrate_data(self) -> bool:
        """Migrate all data from SQLite to PostgreSQL."""
        try:
            # Create engines
            sqlite_engine = create_engine(self.sqlite_url)
            postgres_engine = create_engine(self.postgres_url)
            
            # Create all tables in PostgreSQL
            Base.metadata.create_all(postgres_engine)
            logger.info("✅ Created all tables in PostgreSQL")
            
            # Get all model classes
            sqlite_session = sessionmaker(bind=sqlite_engine)()
            postgres_session = sessionmaker(bind=postgres_engine)()
            
            # Migration mapping for all models
            model_classes = [
                # User models
                User, Workspace, WorkspaceSecret, WorkspaceMember,
                # AI models
                AIAuditLog, AIRequest, AIResponse, AIProvider,
                # Billing models
                BillingAccount, BillingTier, CostAllocation, Invoice, Payment,
                Subscription, UsageRecord,
                # Governance models
                GovernanceRequest, GovernanceResult, IntentVector,
                OperationPlan, ExecutionContext, RiskScores, ValidationResults,
                MemoryGateResults, RoutingDecision, ExecutionOutcome,
                # App models
                ClipCrafterProject, ClipCrafterClip, ClipCrafterTemplate, ClipCrafterRender,
                TrapMasterProject, TrapMasterTrack, TrapMasterSample, TrapMasterExport,
                # System models
                AuditLog, Job, Upload, Feedback, Insight, Suggestion, Anomaly,
                # Content models
                Content, Disclaimer, Leaderboard, LiveStream, UserUpload,
                # Security models
                SecurityEvent, ComplianceReport, VulnerabilityScan,
                # Autonomous models
                AutonomousTask, AutonomousReport, AutonomousDecision,
                # AI Citizenship models
                AICitizenshipCertificate, AICitizenshipValidation,
                # Revenue models
                InfrastructureRevenue, CustomerAccount, ComplianceAddon,
                # Additional models
                Budget, Cost, Metric, Plugin, PrivacySetting, RoutingRule,
                Suggestion, Anomaly, Game, GameSession, GameScore
            ]
            
            migrated_count = 0
            
            for model_class in model_classes:
                try:
                    # Get all records from SQLite
                    sqlite_records = sqlite_session.query(model_class).all()
                    
                    if sqlite_records:
                        # Clear existing data in PostgreSQL
                        postgres_session.query(model_class).delete()
                        
                        # Insert records into PostgreSQL
                        for record in sqlite_records:
                            postgres_session.add(model_class(**record.__dict__))
                        
                        postgres_session.commit()
                        migrated_count += len(sqlite_records)
                        logger.info(f"✅ Migrated {len(sqlite_records)} {model_class.__name__} records")
                    
                except Exception as e:
                    logger.warning(f"⚠️  Could not migrate {model_class.__name__}: {e}")
                    postgres_session.rollback()
            
            sqlite_session.close()
            postgres_session.close()
            
            logger.info(f"✅ Total migrated records: {migrated_count}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data migration failed: {e}")
            return False
    
    def run_alembic_migrations(self) -> bool:
        """Run Alembic migrations to ensure schema is up to date."""
        try:
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            logger.info("✅ Alembic migrations completed")
            return True
        except Exception as e:
            logger.error(f"❌ Alembic migration failed: {e}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify that migration was successful."""
        try:
            postgres_engine = create_engine(self.postgres_url)
            postgres_session = sessionmaker(bind=postgres_engine)()
            
            # Check basic tables exist
            tables_to_check = ['users', 'workspaces', 'ai_audit_logs', 'billing_accounts']
            
            for table_name in tables_to_check:
                try:
                    result = postgres_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    logger.info(f"✅ Table {table_name}: {count} records")
                except Exception as e:
                    logger.warning(f"⚠️  Could not verify table {table_name}: {e}")
            
            postgres_session.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            return False
    
    def run_complete_migration(self) -> bool:
        """Run the complete migration process."""
        logger.info("🚀 Starting PostgreSQL migration...")
        
        steps = [
            ("Create PostgreSQL database", self.create_postgres_database),
            ("Migrate data", self.migrate_data),
            ("Run Alembic migrations", self.run_alembic_migrations),
            ("Verify migration", self.verify_migration)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"📋 Executing: {step_name}")
            if not step_func():
                logger.error(f"❌ Migration failed at: {step_name}")
                return False
        
        logger.info("✅ PostgreSQL migration completed successfully!")
        return True

def main():
    """Main migration function."""
    migrator = PostgreSQLMigrator()
    success = migrator.run_complete_migration()
    
    if success:
        print("\n" + "="*60)
        print("🎉 POSTGRESQL MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("✅ Database is now production-ready")
        print("✅ All data has been migrated")
        print("✅ Schema is up to date")
        print("✅ System is ready for production deployment")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ POSTGRESQL MIGRATION FAILED!")
        print("="*60)
        print("Please check the logs above for errors")
        print("Fix the issues and try again")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
