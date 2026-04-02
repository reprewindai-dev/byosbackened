"""
Immutable Audit Fabric
======================

This module implements the core of Seked's Immutable Audit Fabric - a blockchain-style
audit trail system that provides cryptographically verifiable, independently checkable
history of AI behavior and governance decisions.

The audit fabric underpins citizenship, policy, and AI-to-AI traffic with:
- Append-only event model with cryptographic chaining
- Hybrid ledger (off-chain events + on-chain hashes)
- Distributed streams (per citizen, per tenant, global)
- Merkle tree proofs for batch verification
- Consensus-backed decision artifacts

This transforms Seked from "we log" to "we provide cryptographically verifiable,
independently checkable history of AI behavior."
"""

import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings


class AuditEvent(BaseModel):
    """Canonical audit event object."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # citizenship_issued, policy_evaluated, execution_allowed, etc.
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    actor_id: str  # Who performed the action
    actor_type: str  # citizen, human, system
    subject_id: Optional[str] = None  # What the action was performed on
    subject_type: Optional[str] = None  # citizenship, policy, execution, etc.
    jurisdiction: str  # Legal jurisdiction context
    trust_level: str  # Trust tier context
    capabilities: List[str] = []  # Capabilities involved
    policy_version: Optional[str] = None  # Policy version used
    constitution_snapshot: Optional[str] = None  # Constitution state
    decision: Optional[str] = None  # allow/deny/override
    metadata: Dict[str, Any] = {}  # Additional context
    content_hash: Optional[str] = None  # Hash of event content
    previous_hash: Optional[str] = None  # Hash pointer to previous event
    signature: Optional[str] = None  # Event signature


class MerkleNode(BaseModel):
    """Merkle tree node for batch verification."""
    left_hash: Optional[str] = None
    right_hash: Optional[str] = None
    hash_value: str
    event_ids: List[str] = []  # Events in this subtree


class AuditBatch(BaseModel):
    """Batch of events for ledger commitment."""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    stream_type: str  # citizen, tenant, global
    stream_id: str  # citizen_id, tenant_id, or "global"
    merkle_root: str
    event_count: int
    previous_batch_hash: Optional[str] = None
    batch_hash: Optional[str] = None
    consensus_signatures: List[str] = []  # From governance cluster


class ImmutableAuditFabric:
    """Core audit fabric implementation."""

    def __init__(self):
        self.settings = get_settings()
        self.db_path = os.path.join(self.settings.DATA_DIR, "audit_fabric.db")
        self.secret_key = self.settings.AUDIT_FABRIC_SECRET or "default_audit_secret_change_me"
        self.logger = structlog.get_logger(__name__)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize audit fabric databases."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                subject_id TEXT,
                subject_type TEXT,
                jurisdiction TEXT NOT NULL,
                trust_level TEXT NOT NULL,
                capabilities TEXT NOT NULL,  -- JSON array
                policy_version TEXT,
                constitution_snapshot TEXT,
                decision TEXT,
                metadata TEXT NOT NULL,  -- JSON object
                content_hash TEXT NOT NULL,
                previous_hash TEXT,
                signature TEXT NOT NULL,
                stream_type TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                batch_id TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_batches (
                batch_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                stream_type TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                merkle_root TEXT NOT NULL,
                event_count INTEGER NOT NULL,
                previous_batch_hash TEXT,
                batch_hash TEXT NOT NULL,
                consensus_signatures TEXT NOT NULL,  -- JSON array
                committed_at TEXT,
                ledger_reference TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stream_heads (
                stream_type TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                last_event_hash TEXT,
                last_batch_hash TEXT,
                sequence_number INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (stream_type, stream_id)
            )
        """)

        conn.commit()
        conn.close()
        self.logger.info("Immutable Audit Fabric database initialized", db_path=self.db_path)

    def _generate_content_hash(self, event_data: Dict[str, Any]) -> str:
        """Generate hash of event content."""
        # Sort keys for deterministic hashing
        content_str = json.dumps(event_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _generate_signature(self, content_hash: str, previous_hash: Optional[str] = None) -> str:
        """Generate HMAC signature for event."""
        message = f"{content_hash}:{previous_hash or ''}"
        return hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _get_stream_head(self, stream_type: str, stream_id: str) -> Tuple[Optional[str], int]:
        """Get the last event hash and sequence number for a stream."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT last_event_hash, sequence_number FROM stream_heads
            WHERE stream_type = ? AND stream_id = ?
        """, (stream_type, stream_id))

        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0], row[1]
        return None, 0

    def _update_stream_head(self, stream_type: str, stream_id: str, event_hash: str, sequence_number: int) -> None:
        """Update the stream head with new event hash."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO stream_heads (stream_type, stream_id, last_event_hash, sequence_number)
            VALUES (?, ?, ?, ?)
        """, (stream_type, stream_id, event_hash, sequence_number))
        conn.commit()
        conn.close()

    def record_event(self, event: AuditEvent, stream_type: str, stream_id: str) -> AuditEvent:
        """
        Record an audit event in the immutable fabric.

        Args:
            event: The audit event to record
            stream_type: Type of stream (citizen, tenant, global)
            stream_id: ID of the stream

        Returns:
            The recorded event with hashes and signature
        """
        # Get previous hash and sequence number
        previous_hash, sequence_number = self._get_stream_head(stream_type, stream_id)

        # Prepare event data for hashing
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "actor_id": event.actor_id,
            "actor_type": event.actor_type,
            "subject_id": event.subject_id,
            "subject_type": event.subject_type,
            "jurisdiction": event.jurisdiction,
            "trust_level": event.trust_level,
            "capabilities": event.capabilities,
            "policy_version": event.policy_version,
            "constitution_snapshot": event.constitution_snapshot,
            "decision": event.decision,
            "metadata": event.metadata,
        }

        # Generate content hash
        content_hash = self._generate_content_hash(event_data)

        # Generate signature
        signature = self._generate_signature(content_hash, previous_hash)

        # Update event with hashes and signature
        event.content_hash = content_hash
        event.previous_hash = previous_hash
        event.signature = signature

        # Persist event
        conn = sqlite3.connect(self.db_path)
        sequence_number += 1

        conn.execute("""
            INSERT INTO audit_events (
                event_id, event_type, timestamp, actor_id, actor_type,
                subject_id, subject_type, jurisdiction, trust_level,
                capabilities, policy_version, constitution_snapshot,
                decision, metadata, content_hash, previous_hash, signature,
                stream_type, stream_id, sequence_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id, event.event_type, event.timestamp,
            event.actor_id, event.actor_type, event.subject_id, event.subject_type,
            event.jurisdiction, event.trust_level, json.dumps(event.capabilities),
            event.policy_version, event.constitution_snapshot, event.decision,
            json.dumps(event.metadata), content_hash, previous_hash, signature,
            stream_type, stream_id, sequence_number,
            datetime.utcnow().isoformat() + "Z"
        ))

        conn.commit()
        conn.close()

        # Update stream head
        self._update_stream_head(stream_type, stream_id, content_hash, sequence_number)

        self.logger.info("Audit event recorded",
                        event_id=event.event_id,
                        event_type=event.event_type,
                        stream_type=stream_type,
                        stream_id=stream_id,
                        sequence_number=sequence_number)

        return event

    def create_merkle_tree(self, event_hashes: List[str]) -> Tuple[str, MerkleNode]:
        """
        Create Merkle tree from event hashes.

        Returns:
            Tuple of (merkle_root, merkle_tree)
        """
        if not event_hashes:
            return "", MerkleNode(hash_value="", event_ids=[])

        if len(event_hashes) == 1:
            return event_hashes[0], MerkleNode(hash_value=event_hashes[0], event_ids=[event_hashes[0]])

        # Build tree level by level
        current_level = [MerkleNode(hash_value=h, event_ids=[h]) for h in event_hashes]

        while len(current_level) > 1:
            next_level = []

            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else None

                if right:
                    combined_hash = hashlib.sha256(f"{left.hash_value}:{right.hash_value}".encode()).hexdigest()
                    event_ids = left.event_ids + right.event_ids
                else:
                    # Odd number of nodes - duplicate last node
                    combined_hash = hashlib.sha256(f"{left.hash_value}:{left.hash_value}".encode()).hexdigest()
                    event_ids = left.event_ids + left.event_ids

                next_level.append(MerkleNode(
                    left_hash=left.hash_value,
                    right_hash=right.hash_value if right else left.hash_value,
                    hash_value=combined_hash,
                    event_ids=event_ids
                ))

            current_level = next_level

        return current_level[0].hash_value, current_level[0]

    def create_audit_batch(self, stream_type: str, stream_id: str, event_count: int = 100) -> Optional[AuditBatch]:
        """
        Create an audit batch from recent events in a stream.

        Args:
            stream_type: Type of stream
            stream_id: Stream ID
            event_count: Number of events to batch

        Returns:
            AuditBatch if events were found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)

        # Get recent events not yet batched
        cursor = conn.execute("""
            SELECT content_hash FROM audit_events
            WHERE stream_type = ? AND stream_id = ? AND batch_id IS NULL
            ORDER BY sequence_number DESC
            LIMIT ?
        """, (stream_type, stream_id, event_count))

        rows = cursor.fetchall()
        event_hashes = [row[0] for row in rows]

        if not event_hashes:
            conn.close()
            return None

        # Create Merkle tree
        merkle_root, _ = self.create_merkle_tree(event_hashes)

        # Get previous batch hash
        cursor = conn.execute("""
            SELECT batch_hash FROM audit_batches
            WHERE stream_type = ? AND stream_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (stream_type, stream_id))

        previous_batch_row = cursor.fetchone()
        previous_batch_hash = previous_batch_row[0] if previous_batch_row else None

        # Create batch
        batch = AuditBatch(
            stream_type=stream_type,
            stream_id=stream_id,
            merkle_root=merkle_root,
            event_count=len(event_hashes),
            previous_batch_hash=previous_batch_hash
        )

        # Generate batch hash
        batch_data = {
            "batch_id": batch.batch_id,
            "timestamp": batch.timestamp,
            "stream_type": batch.stream_type,
            "stream_id": batch.stream_id,
            "merkle_root": batch.merkle_root,
            "event_count": batch.event_count,
            "previous_batch_hash": batch.previous_batch_hash
        }
        batch_content = json.dumps(batch_data, sort_keys=True)
        batch.batch_hash = hashlib.sha256(batch_content.encode()).hexdigest()

        # Persist batch
        conn.execute("""
            INSERT INTO audit_batches (
                batch_id, timestamp, stream_type, stream_id, merkle_root,
                event_count, previous_batch_hash, batch_hash, consensus_signatures
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch.batch_id, batch.timestamp, batch.stream_type, batch.stream_id,
            batch.merkle_root, batch.event_count, batch.previous_batch_hash,
            batch.batch_hash, json.dumps(batch.consensus_signatures)
        ))

        # Mark events as batched
        event_hash_placeholders = ','.join('?' * len(event_hashes))
        conn.execute(f"""
            UPDATE audit_events SET batch_id = ?
            WHERE stream_type = ? AND stream_id = ? AND content_hash IN ({event_hash_placeholders})
        """, [batch.batch_id, stream_type, stream_id] + event_hashes)

        conn.commit()
        conn.close()

        self.logger.info("Audit batch created",
                        batch_id=batch.batch_id,
                        stream_type=stream_type,
                        stream_id=stream_id,
                        event_count=batch.event_count)

        return batch

    def verify_event_chain(self, stream_type: str, stream_id: str, start_sequence: int = 1, end_sequence: Optional[int] = None) -> bool:
        """
        Verify the cryptographic chain of events in a stream.

        Args:
            stream_type: Type of stream
            stream_id: Stream ID
            start_sequence: Starting sequence number
            end_sequence: Ending sequence number (None for latest)

        Returns:
            True if chain is valid, False otherwise
        """
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT sequence_number, content_hash, previous_hash, signature
            FROM audit_events
            WHERE stream_type = ? AND stream_id = ?
            AND sequence_number >= ?
        """
        params = [stream_type, stream_id, start_sequence]

        if end_sequence:
            query += " AND sequence_number <= ?"
            params.append(end_sequence)

        query += " ORDER BY sequence_number ASC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return True  # Empty range is valid

        previous_hash = None
        for row in rows:
            sequence_number, content_hash, event_previous_hash, signature = row

            # Verify previous hash continuity
            if event_previous_hash != previous_hash:
                self.logger.error("Chain continuity broken",
                                sequence_number=sequence_number,
                                expected_previous=previous_hash,
                                actual_previous=event_previous_hash)
                return False

            # Verify signature
            expected_signature = self._generate_signature(content_hash, previous_hash)
            if not hmac.compare_digest(signature, expected_signature):
                self.logger.error("Signature verification failed",
                                sequence_number=sequence_number,
                                expected=expected_signature,
                                actual=signature)
                return False

            previous_hash = content_hash

        return True

    def get_verification_proof(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get verification proof for an event.

        Returns proof data that can be independently verified.
        """
        conn = sqlite3.connect(self.db_path)

        cursor = conn.execute("""
            SELECT e.*, b.batch_hash, b.consensus_signatures
            FROM audit_events e
            LEFT JOIN audit_batches b ON e.batch_id = b.batch_id
            WHERE e.event_id = ?
        """, (event_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Parse data
        event_data = dict(zip([desc[0] for desc in cursor.description], row))
        event_data['capabilities'] = json.loads(event_data['capabilities'])
        event_data['metadata'] = json.loads(event_data['metadata'])
        event_data['consensus_signatures'] = json.loads(event_data.get('consensus_signatures', '[]'))

        return {
            "event": event_data,
            "verification_data": {
                "content_hash": event_data['content_hash'],
                "previous_hash": event_data['previous_hash'],
                "signature": event_data['signature'],
                "batch_hash": event_data.get('batch_hash'),
                "consensus_signatures": event_data.get('consensus_signatures', [])
            },
            "stream_info": {
                "stream_type": event_data['stream_type'],
                "stream_id": event_data['stream_id'],
                "sequence_number": event_data['sequence_number']
            }
        }


# Global audit fabric instance
audit_fabric = ImmutableAuditFabric()
