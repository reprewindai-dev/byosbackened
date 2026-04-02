"""
Merkle Tree Implementation for Audit Batching
=============================================

Implementation of Merkle tree batching for audit events as specified in the
engineering brief. This provides tamper-evident batching with efficient
proofs of inclusion.

Algorithm:
1. Group events by time window and/or stream type
2. Take entry hashes as leaves
3. Build balanced Merkle tree
4. Anchor root to immutable ledger
"""

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings
from core.audit_fabric.canonical_event_model import EventStream


class MerkleNode(BaseModel):
    """Merkle tree node."""
    hash_value: str
    left_child: Optional[str] = None
    right_child: Optional[str] = None
    event_hashes: List[str] = []  # For leaf nodes
    level: int = 0
    position: int = 0  # Position in level


class MerkleTree:
    """Merkle tree implementation for audit batching."""

    def __init__(self, leaf_hashes: List[str]):
        self.leaf_hashes = leaf_hashes
        self.root: Optional[MerkleNode] = None
        self.nodes: Dict[str, MerkleNode] = {}
        self.levels: List[List[MerkleNode]] = []
        self._build_tree()

    def _build_tree(self) -> None:
        """Build the Merkle tree from leaf hashes."""
        if not self.leaf_hashes:
            return

        # Ensure even number of leaves (duplicate last if odd)
        leaves = self.leaf_hashes.copy()
        if len(leaves) % 2 != 0:
            leaves.append(leaves[-1])

        # Create leaf nodes
        current_level = []
        for i, leaf_hash in enumerate(leaves):
            node = MerkleNode(
                hash_value=leaf_hash,
                event_hashes=[leaf_hash] if i < len(self.leaf_hashes) else [],  # Only original leaves
                level=0,
                position=i
            )
            current_level.append(node)
            self.nodes[leaf_hash] = node

        self.levels.append(current_level)

        # Build upper levels
        level_num = 1
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]

                # Combine hashes
                combined_hash = hashlib.sha256(
                    f"{left.hash_value}:{right.hash_value}".encode()
                ).hexdigest()

                parent_node = MerkleNode(
                    hash_value=combined_hash,
                    left_child=left.hash_value,
                    right_child=right.hash_value,
                    event_hashes=left.event_hashes + right.event_hashes,
                    level=level_num,
                    position=i // 2
                )

                next_level.append(parent_node)
                self.nodes[combined_hash] = parent_node

            self.levels.append(next_level)
            current_level = next_level
            level_num += 1

        self.root = current_level[0] if current_level else None

    def get_root_hash(self) -> Optional[str]:
        """Get the Merkle root hash."""
        return self.root.hash_value if self.root else None

    def get_inclusion_proof(self, target_hash: str) -> Optional[List[str]]:
        """
        Generate Merkle inclusion proof for a leaf hash.

        Returns list of hashes forming the proof path.
        """
        if target_hash not in self.nodes:
            return None

        proof = []
        current_hash = target_hash

        # Traverse up the tree
        for level in range(len(self.levels) - 1):
            current_node = self.nodes[current_hash]
            current_level = self.levels[level]

            # Find sibling
            if current_node.position % 2 == 0:
                # Left child, get right sibling
                if current_node.position + 1 < len(current_level):
                    sibling = current_level[current_node.position + 1]
                    proof.append(sibling.hash_value)
                else:
                    # Duplicate last node case
                    proof.append(current_node.hash_value)
            else:
                # Right child, get left sibling
                sibling = current_level[current_node.position - 1]
                proof.append(sibling.hash_value)

            # Move to parent
            parent_hash = None
            for node in self.levels[level + 1]:
                if node.left_child == current_hash or node.right_child == current_hash:
                    parent_hash = node.hash_value
                    break

            if parent_hash:
                current_hash = parent_hash
            else:
                break

        return proof

    def verify_inclusion(self, target_hash: str, proof: List[str]) -> bool:
        """
        Verify that a hash is included in this Merkle tree.

        Args:
            target_hash: The hash to verify inclusion for
            proof: The inclusion proof

        Returns:
            True if inclusion is verified
        """
        if not self.root:
            return False

        current_hash = target_hash

        for sibling_hash in proof:
            # Determine order based on hash comparison (simplified)
            if current_hash < sibling_hash:
                current_hash = hashlib.sha256(f"{current_hash}:{sibling_hash}".encode()).hexdigest()
            else:
                current_hash = hashlib.sha256(f"{sibling_hash}:{current_hash}".encode()).hexdigest()

        return current_hash == self.root.hash_value


class AuditBatch(BaseModel):
    """Audit batch with Merkle root."""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stream_type: str
    stream_id: str
    start_sequence: int
    end_sequence: int
    event_count: int
    merkle_root: str
    batch_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    duration_seconds: float = 0.0
    compression_ratio: float = 1.0  # Events per byte efficiency


class MerkleBatchProcessor:
    """Processes audit events into Merkle tree batches."""

    def __init__(self, batch_size: int = 1000, batch_interval_seconds: int = 300):
        self.settings = get_settings()
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds
        self.batches_db_path = os.path.join(self.settings.DATA_DIR, "audit_batches.db")
        self.logger = structlog.get_logger(__name__)
        self._init_batches_db()

    def _init_batches_db(self) -> None:
        """Initialize batches database."""
        os.makedirs(os.path.dirname(self.batches_db_path), exist_ok=True)

        conn = sqlite3.connect(self.batches_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_batches (
                batch_id TEXT PRIMARY KEY,
                stream_type TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                start_sequence INTEGER NOT NULL,
                end_sequence INTEGER NOT NULL,
                event_count INTEGER NOT NULL,
                merkle_root TEXT NOT NULL,
                batch_hash TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                compression_ratio REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_stream ON audit_batches(stream_type, stream_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_timestamp ON audit_batches(timestamp)")

        conn.commit()
        conn.close()

    def create_batch(self, stream: EventStream, max_events: Optional[int] = None) -> Optional[AuditBatch]:
        """
        Create a Merkle batch from pending events in a stream.

        Args:
            stream: The event stream to batch
            max_events: Maximum events to include (default: batch_size)

        Returns:
            AuditBatch if events were batched, None otherwise
        """
        max_events = max_events or self.batch_size

        # Get stream head to determine range
        _, current_sequence = stream.get_stream_head()
        if current_sequence == 0:
            return None

        # Get recent events for batching
        start_sequence = max(1, current_sequence - max_events + 1)
        events = stream.get_events_range(start_sequence, current_sequence)

        if len(events) < 10:  # Minimum batch size
            return None

        # Start timing
        start_time = time.time()

        # Extract leaf hashes
        leaf_hashes = [event.entry_hash for event in events]

        # Build Merkle tree
        merkle_tree = MerkleTree(leaf_hashes)
        merkle_root = merkle_tree.get_root_hash()

        if not merkle_root:
            return None

        # Calculate batch metrics
        end_time = time.time()
        duration = end_time - start_time

        # Estimate compression ratio (events per hash efficiency)
        total_events = len(events)
        compression_ratio = total_events / len(merkle_root) if merkle_root else 1.0

        # Create batch
        batch = AuditBatch(
            stream_type=stream.stream_type,
            stream_id=stream.stream_id,
            start_sequence=start_sequence,
            end_sequence=current_sequence,
            event_count=total_events,
            merkle_root=merkle_root,
            batch_hash=self._compute_batch_hash(events, merkle_root),
            duration_seconds=duration,
            compression_ratio=compression_ratio
        )

        # Store batch
        self._store_batch(batch)

        self.logger.info("Merkle batch created",
                        batch_id=batch.batch_id,
                        stream_type=batch.stream_type,
                        stream_id=batch.stream_id,
                        event_count=batch.event_count,
                        merkle_root=batch.merkle_root,
                        duration_seconds=batch.duration_seconds)

        return batch

    def _compute_batch_hash(self, events: List[Any], merkle_root: str) -> str:
        """Compute batch hash including event metadata."""
        # Include event count, timestamp range, and Merkle root
        if not events:
            return ""

        first_event = events[0]
        last_event = events[-1]

        batch_data = {
            "event_count": len(events),
            "first_sequence": first_event.sequence_number,
            "last_sequence": last_event.sequence_number,
            "first_timestamp": first_event.timestamp,
            "last_timestamp": last_event.timestamp,
            "merkle_root": merkle_root
        }

        batch_json = json.dumps(batch_data, sort_keys=True)
        return hashlib.sha256(batch_json.encode()).hexdigest()

    def _store_batch(self, batch: AuditBatch) -> None:
        """Store batch in database."""
        conn = sqlite3.connect(self.batches_db_path)
        conn.execute("""
            INSERT INTO audit_batches (
                batch_id, stream_type, stream_id, start_sequence, end_sequence,
                event_count, merkle_root, batch_hash, timestamp,
                duration_seconds, compression_ratio, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch.batch_id, batch.stream_type, batch.stream_id,
            batch.start_sequence, batch.end_sequence, batch.event_count,
            batch.merkle_root, batch.batch_hash, batch.timestamp,
            batch.duration_seconds, batch.compression_ratio,
            datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

    def get_batch(self, batch_id: str) -> Optional[AuditBatch]:
        """Retrieve a batch by ID."""
        conn = sqlite3.connect(self.batches_db_path)
        cursor = conn.execute("""
            SELECT batch_id, stream_type, stream_id, start_sequence, end_sequence,
                   event_count, merkle_root, batch_hash, timestamp,
                   duration_seconds, compression_ratio
            FROM audit_batches WHERE batch_id = ?
        """, (batch_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return AuditBatch(
                batch_id=row[0],
                stream_type=row[1],
                stream_id=row[2],
                start_sequence=row[3],
                end_sequence=row[4],
                event_count=row[5],
                merkle_root=row[6],
                batch_hash=row[7],
                timestamp=row[8],
                duration_seconds=row[9],
                compression_ratio=row[10]
            )
        return None

    def generate_inclusion_proof(self, event_hash: str, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate inclusion proof for an event in a batch.

        Returns proof data that can be independently verified.
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return None

        # Get events for this batch
        stream = EventStream(batch.stream_type, batch.stream_id,
                           os.path.join(self.settings.DATA_DIR, "audit_fabric",
                                      f"{batch.stream_type}_{batch.stream_id}.db"))

        events = stream.get_events_range(batch.start_sequence, batch.end_sequence)
        leaf_hashes = [event.entry_hash for event in events]

        # Find the event
        event_index = None
        for i, event in enumerate(events):
            if event.entry_hash == event_hash:
                event_index = i
                break

        if event_index is None:
            return None

        # Build Merkle tree and get proof
        merkle_tree = MerkleTree(leaf_hashes)
        proof_hashes = merkle_tree.get_inclusion_proof(event_hash)

        if proof_hashes is None:
            return None

        return {
            "event_hash": event_hash,
            "batch_id": batch_id,
            "batch_hash": batch.batch_hash,
            "merkle_root": batch.merkle_root,
            "event_index": event_index,
            "proof_hashes": proof_hashes,
            "total_leaves": len(leaf_hashes)
        }

    def verify_inclusion_proof(self, proof: Dict[str, Any]) -> bool:
        """
        Verify an inclusion proof independently.

        Args:
            proof: The proof data returned by generate_inclusion_proof

        Returns:
            True if proof is valid
        """
        event_hash = proof["event_hash"]
        batch_hash = proof["batch_hash"]
        merkle_root = proof["merkle_root"]
        proof_hashes = proof["proof_hashes"]

        # Reconstruct Merkle tree path
        current_hash = event_hash
        for sibling_hash in proof_hashes:
            # Order hashes deterministically
            hashes = sorted([current_hash, sibling_hash])
            current_hash = hashlib.sha256(f"{hashes[0]}:{hashes[1]}".encode()).hexdigest()

        # Verify against root
        return current_hash == merkle_root

    def get_batch_statistics(self, stream_type: str = None, stream_id: str = None,
                           days: int = 30) -> Dict[str, Any]:
        """Get batching statistics for monitoring."""
        conn = sqlite3.connect(self.batches_db_path)

        query = """
            SELECT COUNT(*) as batch_count,
                   SUM(event_count) as total_events,
                   AVG(event_count) as avg_events_per_batch,
                   AVG(duration_seconds) as avg_batch_time,
                   AVG(compression_ratio) as avg_compression,
                   MIN(timestamp) as earliest_batch,
                   MAX(timestamp) as latest_batch
            FROM audit_batches
            WHERE timestamp >= ?
        """
        params = [(datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"]

        if stream_type:
            query += " AND stream_type = ?"
            params.append(stream_type)

        if stream_id:
            query += " AND stream_id = ?"
            params.append(stream_id)

        cursor = conn.execute(query, params)
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "batch_count": row[0] or 0,
                "total_events": row[1] or 0,
                "avg_events_per_batch": row[2] or 0.0,
                "avg_batch_time_seconds": row[3] or 0.0,
                "avg_compression_ratio": row[4] or 1.0,
                "earliest_batch": row[5],
                "latest_batch": row[6],
                "period_days": days
            }

        return {
            "batch_count": 0,
            "total_events": 0,
            "avg_events_per_batch": 0.0,
            "avg_batch_time_seconds": 0.0,
            "avg_compression_ratio": 1.0,
            "period_days": days
        }


# Global Merkle batch processor instance
merkle_batch_processor = MerkleBatchProcessor()


# Utility functions for batch processing
def batch_pending_events(stream_type: str = "global", stream_id: str = "system",
                        max_events: int = 1000) -> Optional[AuditBatch]:
    """Batch pending events for a stream."""
    settings = get_settings()
    stream_db_path = os.path.join(settings.DATA_DIR, "audit_fabric",
                                f"{stream_type}_{stream_id}.db")
    stream = EventStream(stream_type, stream_id, stream_db_path)
    return merkle_batch_processor.create_batch(stream, max_events)


def get_batch_inclusion_proof(event_hash: str, batch_id: str) -> Optional[Dict[str, Any]]:
    """Get inclusion proof for an event in a batch."""
    return merkle_batch_processor.generate_inclusion_proof(event_hash, batch_id)


def verify_batch_inclusion_proof(proof: Dict[str, Any]) -> bool:
    """Verify a batch inclusion proof."""
    return merkle_batch_processor.verify_inclusion_proof(proof)
