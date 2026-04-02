"""
Canonical Event Model with Hash Chaining
=========================================

Implementation of the canonical event structure and hash chaining as specified
in the engineering brief. This provides tamper-evident logs with efficient
proofs of inclusion.

Event Structure:
- Canonical JSON format for deterministic hashing
- Hash chaining for tamper detection
- Merkle tree integration for batch proofs
"""

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
import structlog

from core.config import get_settings


class CanonicalAuditEvent(BaseModel):
    """Canonical audit event structure with hash chaining."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_type: str  # citizen, tenant, system
    stream_id: str  # citizen-123, tenant-456, system
    event_type: str  # CITIZENSHIP_GRANTED, POLICY_DECISION, AI_MESSAGE, etc.
    payload: Dict[str, Any]  # Arbitrary structured data
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    prev_hash: Optional[str] = None
    entry_hash: Optional[str] = None
    sequence_number: Optional[int] = None
    compliance_tags: Dict[str, List[str]] = {}  # ISO 42001 and NIST AI RMF mappings

    @validator('stream_type')
    def validate_stream_type(cls, v):
        valid_types = ['citizen', 'tenant', 'system', 'global']
        if v not in valid_types:
            raise ValueError(f'Stream type must be one of: {valid_types}')
        return v

    @validator('event_type')
    def validate_event_type(cls, v):
        # Allow flexible event types but ensure they're uppercase with underscores
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Event type must contain only alphanumeric characters, underscores, and hyphens')
        return v.upper()

    def to_canonical_json(self) -> str:
        """Convert event to canonical JSON string for hashing."""
        # Create deterministic representation
        canonical_data = {
            "event_id": self.event_id,
            "stream_type": self.stream_type,
            "stream_id": self.stream_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "compliance_tags": self.compliance_tags
        }

        # Sort keys recursively and use consistent separators
        return json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))

    def compute_entry_hash(self) -> str:
        """Compute the entry hash for this event."""
        canonical_json = self.to_canonical_json()

        # Use SHA-256 for strong collision resistance
        hash_obj = hashlib.sha256()
        hash_obj.update(canonical_json.encode('utf-8'))

        if self.prev_hash:
            hash_obj.update(self.prev_hash.encode('utf-8'))

        return hash_obj.hexdigest()

    def with_hash_chain(self, prev_hash: Optional[str] = None, sequence_number: Optional[int] = None) -> 'CanonicalAuditEvent':
        """Return a new event with computed hash chain."""
        event_copy = self.copy()
        event_copy.prev_hash = prev_hash
        event_copy.sequence_number = sequence_number
        event_copy.entry_hash = event_copy.compute_entry_hash()
        return event_copy


class EventStream:
    """Manages an append-only event stream with hash chaining."""

    def __init__(self, stream_type: str, stream_id: str, db_path: str):
        self.stream_type = stream_type
        self.stream_id = stream_id
        self.db_path = db_path
        self.logger = structlog.get_logger(__name__).bind(
            stream_type=stream_type,
            stream_id=stream_id
        )
        self._init_stream()

    def _init_stream(self) -> None:
        """Initialize the stream database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                stream_type TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,  -- JSON
                timestamp TEXT NOT NULL,
                prev_hash TEXT,
                entry_hash TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                compliance_tags TEXT NOT NULL,  -- JSON
                canonical_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(sequence_number, stream_type, stream_id)
            )
        """)

        # Create indexes for efficient queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_sequence ON events(sequence_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")

        # Initialize stream head if not exists
        cursor = conn.execute("""
            SELECT last_hash, sequence_number FROM stream_heads
            WHERE stream_type = ? AND stream_id = ?
        """, (self.stream_type, self.stream_id))

        if not cursor.fetchone():
            conn.execute("""
                INSERT INTO stream_heads (stream_type, stream_id, last_hash, sequence_number)
                VALUES (?, ?, ?, ?)
            """, (self.stream_type, self.stream_id, None, 0))

        conn.commit()
        conn.close()

    def get_stream_head(self) -> Tuple[Optional[str], int]:
        """Get the current stream head (last hash and sequence number)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT last_hash, sequence_number FROM stream_heads
            WHERE stream_type = ? AND stream_id = ?
        """, (self.stream_type, self.stream_id))

        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0], row[1]
        return None, 0

    def append_event(self, event: CanonicalAuditEvent) -> CanonicalAuditEvent:
        """
        Append an event to the stream with hash chaining.

        Args:
            event: The event to append

        Returns:
            The event with computed hash chain
        """
        if event.stream_type != self.stream_type or event.stream_id != self.stream_id:
            raise ValueError("Event stream type/id does not match stream")

        conn = sqlite3.connect(self.db_path)

        # Get current head
        prev_hash, sequence_number = self.get_stream_head()
        next_sequence = sequence_number + 1

        # Compute hash chain for event
        chained_event = event.with_hash_chain(prev_hash, next_sequence)

        # Store event
        conn.execute("""
            INSERT INTO events (
                event_id, stream_type, stream_id, event_type, payload,
                timestamp, prev_hash, entry_hash, sequence_number,
                compliance_tags, canonical_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chained_event.event_id,
            chained_event.stream_type,
            chained_event.stream_id,
            chained_event.event_type,
            json.dumps(chained_event.payload),
            chained_event.timestamp,
            chained_event.prev_hash,
            chained_event.entry_hash,
            chained_event.sequence_number,
            json.dumps(chained_event.compliance_tags),
            chained_event.to_canonical_json(),
            datetime.utcnow().isoformat() + "Z"
        ))

        # Update stream head
        conn.execute("""
            UPDATE stream_heads
            SET last_hash = ?, sequence_number = ?
            WHERE stream_type = ? AND stream_id = ?
        """, (chained_event.entry_hash, next_sequence, self.stream_type, self.stream_id))

        conn.commit()
        conn.close()

        self.logger.info("Event appended to stream",
                        event_id=chained_event.event_id,
                        event_type=chained_event.event_type,
                        sequence_number=next_sequence,
                        entry_hash=chained_event.entry_hash)

        return chained_event

    def get_event(self, event_id: str) -> Optional[CanonicalAuditEvent]:
        """Retrieve an event by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT event_id, stream_type, stream_id, event_type, payload,
                   timestamp, prev_hash, entry_hash, sequence_number, compliance_tags
            FROM events WHERE event_id = ?
        """, (event_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return CanonicalAuditEvent(
                event_id=row[0],
                stream_type=row[1],
                stream_id=row[2],
                event_type=row[3],
                payload=json.loads(row[4]),
                timestamp=row[5],
                prev_hash=row[6],
                entry_hash=row[7],
                sequence_number=row[8],
                compliance_tags=json.loads(row[9]) if row[9] else {}
            )
        return None

    def get_events_range(self, start_sequence: int, end_sequence: Optional[int] = None,
                        limit: int = 1000) -> List[CanonicalAuditEvent]:
        """Get events in a sequence range."""
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT event_id, stream_type, stream_id, event_type, payload,
                   timestamp, prev_hash, entry_hash, sequence_number, compliance_tags
            FROM events
            WHERE stream_type = ? AND stream_id = ? AND sequence_number >= ?
        """
        params = [self.stream_type, self.stream_id, start_sequence]

        if end_sequence:
            query += " AND sequence_number <= ?"
            params.append(end_sequence)

        query += " ORDER BY sequence_number ASC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append(CanonicalAuditEvent(
                event_id=row[0],
                stream_type=row[1],
                stream_id=row[2],
                event_type=row[3],
                payload=json.loads(row[4]),
                timestamp=row[5],
                prev_hash=row[6],
                entry_hash=row[7],
                sequence_number=row[8],
                compliance_tags=json.loads(row[9]) if row[9] else {}
            ))

        return events

    def verify_chain_integrity(self, start_sequence: int = 1,
                              end_sequence: Optional[int] = None) -> Tuple[bool, Optional[int]]:
        """
        Verify the hash chain integrity of the stream.

        Returns:
            Tuple of (is_valid, first_invalid_sequence)
        """
        events = self.get_events_range(start_sequence, end_sequence, limit=10000)

        if not events:
            return True, None

        expected_prev_hash = None

        for i, event in enumerate(events):
            # Verify hash computation
            computed_hash = event.compute_entry_hash()
            if computed_hash != event.entry_hash:
                self.logger.error("Hash verification failed",
                                event_id=event.event_id,
                                sequence_number=event.sequence_number,
                                expected=computed_hash,
                                actual=event.entry_hash)
                return False, event.sequence_number

            # Verify chain continuity
            if event.prev_hash != expected_prev_hash:
                self.logger.error("Chain continuity broken",
                                event_id=event.event_id,
                                sequence_number=event.sequence_number,
                                expected_prev=expected_prev_hash,
                                actual_prev=event.prev_hash)
                return False, event.sequence_number

            expected_prev_hash = event.entry_hash

        return True, None

    def get_merkle_leaves(self, start_sequence: int, end_sequence: int) -> List[str]:
        """Get entry hashes for Merkle tree construction."""
        events = self.get_events_range(start_sequence, end_sequence, limit=10000)
        return [event.entry_hash for event in events]


class CanonicalEventFactory:
    """Factory for creating canonical audit events with compliance tagging."""

    def __init__(self):
        from core.compliance.standards_mapping import standards_compliance
        self.standards_compliance = standards_compliance

    def create_event(self, stream_type: str, stream_id: str, event_type: str,
                    payload: Dict[str, Any], **kwargs) -> CanonicalAuditEvent:
        """Create a canonical event with automatic compliance tagging."""
        event = CanonicalAuditEvent(
            stream_type=stream_type,
            stream_id=stream_id,
            event_type=event_type,
            payload=payload,
            **kwargs
        )

        # Auto-tag with compliance mappings
        compliance_mapping = self.standards_compliance.get_compliance_mapping(event_type)
        if compliance_mapping:
            event.compliance_tags = {
                "iso_42001": [clause.value for clause in compliance_mapping.iso_42001_clauses],
                "nist_ai_rmf": [cat.value for cat in compliance_mapping.nist_ai_rmf_categories],
                "regulatory_frameworks": list(compliance_mapping.regulatory_mappings.keys())
            }

        return event


# Global event factory instance
canonical_event_factory = CanonicalEventFactory()


# Utility functions for common event types
def create_citizenship_event(stream_id: str, citizen_id: str, action: str,
                           payload: Dict[str, Any]) -> CanonicalAuditEvent:
    """Create a citizenship-related audit event."""
    return canonical_event_factory.create_event(
        stream_type="citizen",
        stream_id=stream_id,
        event_type=f"CITIZENSHIP_{action.upper()}",
        payload={
            "citizen_id": citizen_id,
            "action": action,
            **payload
        }
    )


def create_policy_event(stream_id: str, policy_id: str, decision: str,
                       payload: Dict[str, Any]) -> CanonicalAuditEvent:
    """Create a policy evaluation event."""
    return canonical_event_factory.create_event(
        stream_type="system",
        stream_id=stream_id,
        event_type="POLICY_DECISION",
        payload={
            "policy_id": policy_id,
            "decision": decision,
            **payload
        }
    )


def create_communication_event(stream_id: str, sender_id: str, recipient_id: str,
                             message_type: str, payload: Dict[str, Any]) -> CanonicalAuditEvent:
    """Create an AI-to-AI communication event."""
    return canonical_event_factory.create_event(
        stream_type="citizen",
        stream_id=stream_id,
        event_type="AI_COMMUNICATION",
        payload={
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": message_type,
            **payload
        }
    )
