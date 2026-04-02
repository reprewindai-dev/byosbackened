"""
Migration System: Traditional Logs → Immutable Audit Fabric
==========================================================

Implementation of the migration system from classic logs to Seked's immutable
audit fabric as specified in the engineering brief.

Migration phases:
1. Instrumentation phase: Dual logging with correlation mapping
2. Canonical model enforcement: Schema validation and rejection
3. Append-only storage: Hash chaining and tamper-proofing
4. Merkle and anchoring: Batch processing and ledger commitments
5. Cutover and deprecation: Gradual migration with confidence monitoring

This ensures zero-downtime migration while maintaining compliance and auditability.
"""

import os
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings
from core.audit_fabric.canonical_event_model import (
    CanonicalAuditEvent, EventStream, canonical_event_factory
)
from core.audit_fabric.merkle_batching import merkle_batch_processor
from core.audit_fabric.blockchain_anchoring import blockchain_anchor


class MigrationPhase(BaseModel):
    """Migration phase configuration."""
    phase_id: str
    name: str
    description: str
    order: int
    enabled: bool = True
    start_date: Optional[str] = None
    completion_date: Optional[str] = None
    success_criteria: List[str] = []
    rollback_plan: str = ""


class LegacyLogMapping(BaseModel):
    """Mapping between legacy log fields and Seked canonical events."""
    legacy_source: str  # e.g., "application.log", "audit.db"
    legacy_format: str  # e.g., "json", "syslog", "database"
    event_type_mapping: Dict[str, str]  # Legacy event type -> Seked event type
    field_mappings: Dict[str, str]  # Legacy field -> Seked field
    correlation_id_field: Optional[str] = None  # Field for correlation
    transformation_rules: Dict[str, Any] = {}  # Custom transformation logic


class MigrationStatistics(BaseModel):
    """Migration progress and quality metrics."""
    total_legacy_events: int = 0
    migrated_events: int = 0
    failed_migrations: int = 0
    correlation_mappings: int = 0
    duplicate_events: int = 0
    validation_errors: int = 0
    hash_chain_breaks: int = 0
    last_migration_run: Optional[str] = None
    average_migration_time: float = 0.0
    migration_success_rate: float = 0.0


class LegacyLogAdapter:
    """Adapter for reading and transforming legacy log formats."""

    def __init__(self, mapping: LegacyLogMapping):
        self.mapping = mapping
        self.logger = structlog.get_logger(__name__).bind(
            legacy_source=mapping.legacy_source
        )

    def parse_legacy_event(self, raw_event: Any) -> Optional[CanonicalAuditEvent]:
        """
        Parse a legacy log event into Seked canonical format.

        Handles various legacy formats: JSON, syslog, database records, etc.
        """
        try:
            if self.mapping.legacy_format == "json":
                return self._parse_json_event(raw_event)
            elif self.mapping.legacy_format == "syslog":
                return self._parse_syslog_event(raw_event)
            elif self.mapping.legacy_format == "database":
                return self._parse_database_event(raw_event)
            else:
                self.logger.warning("Unsupported legacy format", format=self.mapping.legacy_format)
                return None

        except Exception as e:
            self.logger.error("Failed to parse legacy event", error=str(e))
            return None

    def _parse_json_event(self, raw_event: str) -> Optional[CanonicalAuditEvent]:
        """Parse JSON-formatted legacy event."""
        try:
            legacy_data = json.loads(raw_event)
        except json.JSONDecodeError:
            return None

        # Apply field mappings
        event_data = {}
        for seked_field, legacy_field in self.mapping.field_mappings.items():
            if legacy_field in legacy_data:
                event_data[seked_field] = legacy_data[legacy_field]

        # Determine event type
        legacy_event_type = legacy_data.get("event_type", "unknown")
        seked_event_type = self.mapping.event_type_mapping.get(legacy_event_type, "LEGACY_IMPORTED")

        # Create canonical event
        return canonical_event_factory.create_event(
            stream_type="system",  # Default for migrated events
            stream_id="legacy_migration",
            event_type=seked_event_type,
            payload=event_data
        )

    def _parse_syslog_event(self, raw_event: str) -> Optional[CanonicalAuditEvent]:
        """Parse syslog-formatted legacy event."""
        # Simplified syslog parsing - would need more sophisticated parsing in production
        parts = raw_event.split()
        if len(parts) < 5:
            return None

        # Extract basic fields
        timestamp = " ".join(parts[:3])
        hostname = parts[3]
        message = " ".join(parts[4:])

        return canonical_event_factory.create_event(
            stream_type="system",
            stream_id="legacy_migration",
            event_type="LEGACY_SYSLOG",
            payload={
                "original_timestamp": timestamp,
                "hostname": hostname,
                "message": message,
                "raw_event": raw_event
            }
        )

    def _parse_database_event(self, raw_event: Dict[str, Any]) -> Optional[CanonicalAuditEvent]:
        """Parse database record legacy event."""
        # Apply field mappings
        event_data = {}
        for seked_field, legacy_field in self.mapping.field_mappings.items():
            if legacy_field in raw_event:
                event_data[seked_field] = raw_event[legacy_field]

        # Determine event type
        legacy_event_type = raw_event.get("event_type", "database_record")
        seked_event_type = self.mapping.event_type_mapping.get(legacy_event_type, "LEGACY_DATABASE")

        return canonical_event_factory.create_event(
            stream_type="system",
            stream_id="legacy_migration",
            event_type=seked_event_type,
            payload=event_data
        )


class MigrationEngine:
    """Core migration engine for phased transition to immutable audit fabric."""

    def __init__(self):
        self.settings = get_settings()
        self.migration_path = os.path.join(self.settings.DATA_DIR, "migration")
        self.migration_db_path = os.path.join(self.migration_path, "migration.db")
        self.logger = structlog.get_logger(__name__)

        # Migration phases as defined in the brief
        self.phases = self._init_migration_phases()

        # Legacy log adapters
        self.legacy_adapters: Dict[str, LegacyLogAdapter] = {}

        # Migration statistics
        self.stats = MigrationStatistics()

        self._init_migration_storage()

    def _init_migration_phases(self) -> Dict[str, MigrationPhase]:
        """Initialize migration phases from the engineering brief."""
        return {
            "instrumentation": MigrationPhase(
                phase_id="instrumentation",
                name="Instrumentation Phase",
                description="Dual logging with correlation mapping",
                order=1,
                success_criteria=[
                    "All application components emit both legacy and Seked events",
                    "Correlation IDs established for 100% of events",
                    "Zero production impact during instrumentation"
                ],
                rollback_plan="Remove Seked instrumentation, revert to legacy logging only"
            ),
            "canonical_enforcement": MigrationPhase(
                phase_id="canonical_enforcement",
                name="Canonical Model Enforcement",
                description="Schema validation and malformed event rejection",
                order=2,
                success_criteria=[
                    "100% of events pass Seked schema validation",
                    "Malformed events properly rejected and logged",
                    "Event transformation accuracy > 99%"
                ],
                rollback_plan="Disable schema validation, allow flexible event formats"
            ),
            "append_only_storage": MigrationPhase(
                phase_id="append_only_storage",
                name="Append-Only Storage",
                description="Hash chaining and tamper-proof storage",
                order=3,
                success_criteria=[
                    "All events stored with cryptographic hash chains",
                    "Zero unauthorized modifications detected",
                    "Storage performance meets production requirements"
                ],
                rollback_plan="Disable hash chaining, allow mutable storage"
            ),
            "merkle_anchoring": MigrationPhase(
                phase_id="merkle_anchoring",
                name="Merkle and Anchoring",
                description="Batch processing and ledger commitments",
                order=4,
                success_criteria=[
                    "Merkle trees generated for all event batches",
                    "Blockchain anchoring operational",
                    "Independent verification working"
                ],
                rollback_plan="Disable Merkle batching, continue with hash chains only"
            ),
            "cutover_deprecation": MigrationPhase(
                phase_id="cutover_deprecation",
                name="Cutover and Deprecation",
                description="Gradual migration with confidence monitoring",
                order=5,
                success_criteria=[
                    "Legacy systems fully deprecated",
                    "Seked audit fabric primary source of truth",
                    "Regulatory compliance maintained throughout"
                ],
                rollback_plan="Restore legacy logging as backup, dual logging mode"
            )
        }

    def _init_migration_storage(self) -> None:
        """Initialize migration tracking storage."""
        os.makedirs(self.migration_path, exist_ok=True)

        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)

        # Migration phases tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migration_phases (
                phase_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                order_num INTEGER NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                start_date TEXT,
                completion_date TEXT,
                success_criteria TEXT NOT NULL,  -- JSON
                rollback_plan TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                updated_at TEXT NOT NULL
            )
        """)

        # Legacy event correlations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS legacy_correlations (
                correlation_id TEXT PRIMARY KEY,
                legacy_event_id TEXT NOT NULL,
                legacy_source TEXT NOT NULL,
                seked_event_id TEXT,
                migration_status TEXT NOT NULL DEFAULT 'pending',
                migration_attempts INTEGER NOT NULL DEFAULT 0,
                last_attempt TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Migration statistics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migration_stats (
                stat_date TEXT NOT NULL,
                total_legacy_events INTEGER NOT NULL DEFAULT 0,
                migrated_events INTEGER NOT NULL DEFAULT 0,
                failed_migrations INTEGER NOT NULL DEFAULT 0,
                correlation_mappings INTEGER NOT NULL DEFAULT 0,
                duplicate_events INTEGER NOT NULL DEFAULT 0,
                validation_errors INTEGER NOT NULL DEFAULT 0,
                hash_chain_breaks INTEGER NOT NULL DEFAULT 0,
                average_migration_time REAL NOT NULL DEFAULT 0.0,
                migration_success_rate REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                PRIMARY KEY (stat_date)
            )
        """)

        # Insert migration phases
        for phase in self.phases.values():
            conn.execute("""
                INSERT OR REPLACE INTO migration_phases (
                    phase_id, name, description, order_num, enabled,
                    success_criteria, rollback_plan, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                phase.phase_id, phase.name, phase.description, phase.order,
                phase.enabled, json.dumps(phase.success_criteria),
                phase.rollback_plan, datetime.utcnow().isoformat() + "Z"
            ))

        conn.commit()
        conn.close()
        self.logger.info("Migration storage initialized")

    def register_legacy_adapter(self, mapping: LegacyLogMapping) -> None:
        """Register a legacy log adapter for migration."""
        adapter = LegacyLogAdapter(mapping)
        self.legacy_adapters[mapping.legacy_source] = adapter
        self.logger.info("Legacy adapter registered", source=mapping.legacy_source)

    def start_migration_phase(self, phase_id: str) -> bool:
        """Start a migration phase."""
        if phase_id not in self.phases:
            self.logger.error("Unknown migration phase", phase_id=phase_id)
            return False

        phase = self.phases[phase_id]

        # Check if previous phases are complete
        for other_phase in self.phases.values():
            if other_phase.order < phase.order and not self._is_phase_complete(other_phase.phase_id):
                self.logger.error("Previous phase not complete",
                                phase_id=phase_id,
                                previous_phase=other_phase.phase_id)
                return False

        # Start the phase
        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)
        conn.execute("""
            UPDATE migration_phases
            SET status = 'active', start_date = ?
            WHERE phase_id = ?
        """, (datetime.utcnow().isoformat() + "Z", phase_id))
        conn.commit()
        conn.close()

        self.logger.info("Migration phase started", phase_id=phase_id, phase_name=phase.name)
        return True

    def complete_migration_phase(self, phase_id: str) -> bool:
        """Complete a migration phase."""
        if phase_id not in self.phases:
            return False

        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)
        conn.execute("""
            UPDATE migration_phases
            SET status = 'completed', completion_date = ?
            WHERE phase_id = ?
        """, (datetime.utcnow().isoformat() + "Z", phase_id))
        conn.commit()
        conn.close()

        self.logger.info("Migration phase completed", phase_id=phase_id)
        return True

    def _is_phase_complete(self, phase_id: str) -> bool:
        """Check if a migration phase is complete."""
        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)
        cursor = conn.execute("""
            SELECT status FROM migration_phases WHERE phase_id = ?
        """, (phase_id,))
        row = cursor.fetchone()
        conn.close()

        return row and row[0] == 'completed'

    def migrate_legacy_event(self, legacy_source: str, raw_event: Any,
                           correlation_id: Optional[str] = None) -> Optional[str]:
        """
        Migrate a single legacy event to Seked canonical format.

        Returns the Seked event ID if successful, None otherwise.
        """
        start_time = datetime.utcnow()

        # Get adapter for this source
        adapter = self.legacy_adapters.get(legacy_source)
        if not adapter:
            self.logger.error("No adapter registered for legacy source", source=legacy_source)
            return None

        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = hashlib.sha256(f"{legacy_source}:{raw_event}".encode()).hexdigest()

        # Check if already migrated
        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)
        cursor = conn.execute("""
            SELECT seked_event_id, migration_status FROM legacy_correlations
            WHERE correlation_id = ?
        """, (correlation_id,))
        existing = cursor.fetchone()

        if existing and existing[1] == 'completed':
            conn.close()
            return existing[0]  # Already migrated

        # Parse legacy event
        canonical_event = adapter.parse_legacy_event(raw_event)
        if not canonical_event:
            # Record failed migration
            conn.execute("""
                INSERT OR REPLACE INTO legacy_correlations (
                    correlation_id, legacy_event_id, legacy_source,
                    migration_status, migration_attempts, last_attempt,
                    error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                correlation_id, str(raw_event)[:255], legacy_source,
                'failed', 1, datetime.utcnow().isoformat() + "Z",
                'Failed to parse legacy event', datetime.utcnow().isoformat() + "Z"
            ))
            conn.commit()
            conn.close()
            return None

        try:
            # Create event stream for migration
            stream = EventStream("system", "legacy_migration",
                               os.path.join(self.settings.DATA_DIR, "audit_fabric",
                                          "system_legacy_migration.db"))

            # Append event with hash chaining
            migrated_event = stream.append_event(canonical_event)

            # Record successful migration
            conn.execute("""
                INSERT OR REPLACE INTO legacy_correlations (
                    correlation_id, legacy_event_id, legacy_source,
                    seked_event_id, migration_status, migration_attempts,
                    last_attempt, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                correlation_id, str(raw_event)[:255], legacy_source,
                migrated_event.event_id, 'completed', 1,
                datetime.utcnow().isoformat() + "Z",
                datetime.utcnow().isoformat() + "Z"
            ))
            conn.commit()
            conn.close()

            # Update statistics
            migration_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_migration_stats(success=True, migration_time=migration_time)

            self.logger.info("Legacy event migrated successfully",
                           correlation_id=correlation_id[:8],
                           seked_event_id=migrated_event.event_id,
                           migration_time=migration_time)

            return migrated_event.event_id

        except Exception as e:
            # Record failed migration
            conn.execute("""
                INSERT OR REPLACE INTO legacy_correlations (
                    correlation_id, legacy_event_id, legacy_source,
                    migration_status, migration_attempts, last_attempt,
                    error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                correlation_id, str(raw_event)[:255], legacy_source,
                'failed', 1, datetime.utcnow().isoformat() + "Z",
                str(e), datetime.utcnow().isoformat() + "Z"
            ))
            conn.commit()
            conn.close()

            self._update_migration_stats(success=False)
            self.logger.error("Legacy event migration failed",
                            correlation_id=correlation_id[:8],
                            error=str(e))

            return None

    def bulk_migrate_legacy_logs(self, legacy_source: str, event_stream: List[Any],
                               batch_size: int = 100) -> Dict[str, Any]:
        """
        Bulk migrate a stream of legacy log events.

        Args:
            legacy_source: Source identifier for the legacy logs
            event_stream: Stream of raw legacy events
            batch_size: Number of events to process in each batch

        Returns:
            Migration results summary
        """
        results = {
            "total_events": len(event_stream),
            "successful_migrations": 0,
            "failed_migrations": 0,
            "duplicate_events": 0,
            "processing_time": 0.0,
            "events_per_second": 0.0
        }

        start_time = datetime.utcnow()

        for i in range(0, len(event_stream), batch_size):
            batch = event_stream[i:i + batch_size]

            for raw_event in batch:
                seked_event_id = self.migrate_legacy_event(legacy_source, raw_event)

                if seked_event_id:
                    results["successful_migrations"] += 1
                else:
                    results["failed_migrations"] += 1

        end_time = datetime.utcnow()
        results["processing_time"] = (end_time - start_time).total_seconds()
        results["events_per_second"] = results["total_events"] / results["processing_time"] if results["processing_time"] > 0 else 0

        self.logger.info("Bulk migration completed",
                        source=legacy_source,
                        **results)

        return results

    def _update_migration_stats(self, success: bool, migration_time: float = 0.0) -> None:
        """Update migration statistics."""
        today = datetime.utcnow().date().isoformat()

        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)

        # Get current stats
        cursor = conn.execute("""
            SELECT total_legacy_events, migrated_events, failed_migrations,
                   average_migration_time, migration_success_rate
            FROM migration_stats WHERE stat_date = ?
        """, (today,))

        row = cursor.fetchone()

        if row:
            total_legacy, migrated, failed, avg_time, success_rate = row
            total_legacy += 1
            if success:
                migrated += 1
            else:
                failed += 1

            # Update running averages
            if success and migration_time > 0:
                avg_time = (avg_time + migration_time) / 2

            if total_legacy > 0:
                success_rate = (migrated / total_legacy) * 100

            conn.execute("""
                UPDATE migration_stats
                SET total_legacy_events = ?, migrated_events = ?, failed_migrations = ?,
                    average_migration_time = ?, migration_success_rate = ?,
                    last_migration_run = ?
                WHERE stat_date = ?
            """, (total_legacy, migrated, failed, avg_time, success_rate,
                  datetime.utcnow().isoformat() + "Z", today))
        else:
            # Insert new stats record
            conn.execute("""
                INSERT INTO migration_stats (
                    stat_date, total_legacy_events, migrated_events, failed_migrations,
                    average_migration_time, migration_success_rate, last_migration_run, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, 1, 1 if success else 0, 0 if success else 1,
                  migration_time if success else 0.0,
                  100.0 if success else 0.0,
                  datetime.utcnow().isoformat() + "Z",
                  datetime.utcnow().isoformat() + "Z"))

        conn.commit()
        conn.close()

    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status."""
        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)

        # Get phase status
        phases = {}
        cursor = conn.execute("""
            SELECT phase_id, name, status, start_date, completion_date
            FROM migration_phases ORDER BY order_num
        """)
        for row in cursor.fetchall():
            phases[row[0]] = {
                "name": row[1],
                "status": row[2],
                "start_date": row[3],
                "completion_date": row[4]
            }

        # Get latest statistics
        cursor = conn.execute("""
            SELECT total_legacy_events, migrated_events, failed_migrations,
                   correlation_mappings, duplicate_events, validation_errors,
                   hash_chain_breaks, average_migration_time, migration_success_rate
            FROM migration_stats
            ORDER BY stat_date DESC LIMIT 1
        """)
        stats_row = cursor.fetchone()

        stats = {}
        if stats_row:
            stats = {
                "total_legacy_events": stats_row[0],
                "migrated_events": stats_row[1],
                "failed_migrations": stats_row[2],
                "correlation_mappings": stats_row[3],
                "duplicate_events": stats_row[4],
                "validation_errors": stats_row[5],
                "hash_chain_breaks": stats_row[6],
                "average_migration_time": stats_row[7],
                "migration_success_rate": stats_row[8]
            }

        # Get correlation status
        cursor = conn.execute("""
            SELECT migration_status, COUNT(*) as count
            FROM legacy_correlations
            GROUP BY migration_status
        """)

        correlations = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            "migration_phases": phases,
            "current_statistics": stats,
            "correlation_status": correlations,
            "overall_progress": self._calculate_overall_progress(phases),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }

    def _calculate_overall_progress(self, phases: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall migration progress."""
        total_phases = len(phases)
        completed_phases = sum(1 for p in phases.values() if p["status"] == "completed")
        active_phases = sum(1 for p in phases.values() if p["status"] == "active")

        completion_percentage = (completed_phases / total_phases) * 100 if total_phases > 0 else 0

        status = "not_started"
        if active_phases > 0:
            status = "in_progress"
        elif completed_phases == total_phases:
            status = "completed"

        return {
            "completion_percentage": completion_percentage,
            "completed_phases": completed_phases,
            "total_phases": total_phases,
            "active_phases": active_phases,
            "status": status
        }

    def validate_migration_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of the migration process.

        Checks hash chains, correlations, and data consistency.
        """
        validation_results = {
            "hash_chain_validation": False,
            "correlation_consistency": False,
            "data_integrity": False,
            "issues_found": [],
            "validated_at": datetime.utcnow().isoformat() + "Z"
        }

        try:
            # Validate hash chains in migrated streams
            stream = EventStream("system", "legacy_migration",
                               os.path.join(self.settings.DATA_DIR, "audit_fabric",
                                          "system_legacy_migration.db"))

            chain_valid, invalid_sequence = stream.verify_chain_integrity()
            validation_results["hash_chain_validation"] = chain_valid

            if not chain_valid:
                validation_results["issues_found"].append(
                    f"Hash chain break detected at sequence {invalid_sequence}"
                )

            # Validate correlation consistency
            import sqlite3
            conn = sqlite3.connect(self.migration_db_path)
            cursor = conn.execute("""
                SELECT COUNT(*) FROM legacy_correlations
                WHERE migration_status = 'completed' AND seked_event_id IS NULL
            """)
            orphaned_correlations = cursor.fetchone()[0]

            if orphaned_correlations > 0:
                validation_results["correlation_consistency"] = False
                validation_results["issues_found"].append(
                    f"{orphaned_correlations} completed correlations missing Seked event IDs"
                )
            else:
                validation_results["correlation_consistency"] = True

            conn.close()

            # Overall data integrity
            validation_results["data_integrity"] = (
                validation_results["hash_chain_validation"] and
                validation_results["correlation_consistency"]
            )

        except Exception as e:
            validation_results["issues_found"].append(f"Validation error: {str(e)}")

        self.logger.info("Migration integrity validation completed",
                        **{k: v for k, v in validation_results.items() if k != "issues_found"})

        return validation_results

    def rollback_migration_phase(self, phase_id: str) -> bool:
        """Rollback a migration phase."""
        if phase_id not in self.phases:
            return False

        phase = self.phases[phase_id]

        # Execute rollback plan (would be customized per phase)
        self.logger.warning("Migration phase rollback initiated",
                          phase_id=phase_id,
                          rollback_plan=phase.rollback_plan)

        # Mark phase as rolled back
        import sqlite3
        conn = sqlite3.connect(self.migration_db_path)
        conn.execute("""
            UPDATE migration_phases
            SET status = 'rolled_back', completion_date = ?
            WHERE phase_id = ?
        """, (datetime.utcnow().isoformat() + "Z", phase_id))
        conn.commit()
        conn.close()

        return True


# Global migration engine instance
migration_engine = MigrationEngine()


# Utility functions for migration operations
def create_legacy_adapter(mapping: LegacyLogMapping) -> None:
    """Create and register a legacy log adapter."""
    migration_engine.register_legacy_adapter(mapping)


def migrate_single_event(legacy_source: str, raw_event: Any) -> Optional[str]:
    """Migrate a single legacy event."""
    return migration_engine.migrate_legacy_event(legacy_source, raw_event)


def start_migration_phase(phase_id: str) -> bool:
    """Start a migration phase."""
    return migration_engine.start_migration_phase(phase_id)


def get_migration_status() -> Dict[str, Any]:
    """Get current migration status."""
    return migration_engine.get_migration_status()


def validate_migration() -> Dict[str, Any]:
    """Validate migration integrity."""
    return migration_engine.validate_migration_integrity()
