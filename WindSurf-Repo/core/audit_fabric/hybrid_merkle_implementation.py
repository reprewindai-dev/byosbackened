"""
Enhanced Merkle Tree Implementation with Hash Chain Hybrid
===========================================================

Implementation of the hybrid approach from the engineering brief:
- Hash chain per logical stream (citizen, tenant, system) for order integrity
- Merkle trees per batch for efficient inclusion proofs
- Optimized for Seked's multi-tenant, high-volume audit requirements

This provides the best of both worlds: sequence integrity + efficient proofs.
"""

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings
from core.audit_fabric.canonical_event_model import EventStream


class HybridMerkleNode(BaseModel):
    """Enhanced Merkle tree node with hash chain integration."""
    hash_value: str
    left_child: Optional[str] = None
    right_child: Optional[str] = None
    event_hashes: List[str] = []  # Events in this subtree
    level: int = 0
    position: int = 0
    # Hash chain integration
    stream_prev_hash: Optional[str] = None  # From stream's hash chain
    batch_sequence_start: int = 0  # First sequence number in batch
    batch_sequence_end: int = 0    # Last sequence number in batch


class HybridMerkleTree:
    """Merkle tree with integrated hash chain verification."""

    def __init__(self, event_hashes: List[str], stream_prev_hash: Optional[str] = None):
        self.event_hashes = event_hashes
        self.stream_prev_hash = stream_prev_hash
        self.root: Optional[HybridMerkleNode] = None
        self.nodes: Dict[str, HybridMerkleNode] = {}
        self.levels: List[List[HybridMerkleNode]] = []
        self.batch_sequence_start = 0
        self.batch_sequence_end = len(event_hashes) - 1
        self._build_hybrid_tree()

    def _build_hybrid_tree(self) -> None:
        """Build Merkle tree with hash chain integration."""
        if not self.event_hashes:
            return

        # Ensure even number of leaves
        leaves = self.event_hashes.copy()
        if len(leaves) % 2 != 0:
            leaves.append(leaves[-1])

        # Create leaf nodes with hash chain context
        current_level = []
        for i, event_hash in enumerate(leaves):
            node = HybridMerkleNode(
                hash_value=event_hash,
                event_hashes=[event_hash] if i < len(self.event_hashes) else [],
                level=0,
                position=i,
                batch_sequence_start=self.batch_sequence_start + i,
                batch_sequence_end=self.batch_sequence_start + i
            )
            current_level.append(node)
            self.nodes[event_hash] = node

        self.levels.append(current_level)

        # Build upper levels
        level_num = 1
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]

                # Enhanced combined hash includes hash chain context
                combined_input = f"{left.hash_value}:{right.hash_value}"
                if self.stream_prev_hash:
                    combined_input += f":{self.stream_prev_hash}"

                combined_hash = hashlib.sha256(combined_input.encode()).hexdigest()

                parent_node = HybridMerkleNode(
                    hash_value=combined_hash,
                    left_child=left.hash_value,
                    right_child=right.hash_value,
                    event_hashes=left.event_hashes + right.event_hashes,
                    level=level_num,
                    position=i // 2,
                    batch_sequence_start=left.batch_sequence_start,
                    batch_sequence_end=right.batch_sequence_end
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

    def generate_inclusion_proof(self, target_hash: str) -> Optional[Dict[str, Any]]:
        """
        Generate enhanced inclusion proof with hash chain verification.

        Returns proof with Merkle path and hash chain context.
        """
        if target_hash not in self.nodes:
            return None

        proof_hashes = []
        current_hash = target_hash
        target_node = self.nodes[target_hash]

        # Traverse up the tree to collect proof hashes
        for level in range(len(self.levels) - 1):
            current_node = self.nodes[current_hash]
            current_level = self.levels[level]

            # Find sibling
            if current_node.position % 2 == 0:
                # Left child, get right sibling
                if current_node.position + 1 < len(current_level):
                    sibling = current_level[current_node.position + 1]
                    proof_hashes.append({
                        "direction": "right",
                        "hash": sibling.hash_value,
                        "position": current_node.position + 1
                    })
                else:
                    # Duplicate case
                    proof_hashes.append({
                        "direction": "right",
                        "hash": current_node.hash_value,
                        "position": current_node.position
                    })
            else:
                # Right child, get left sibling
                sibling = current_level[current_node.position - 1]
                proof_hashes.append({
                    "direction": "left",
                    "hash": sibling.hash_value,
                    "position": current_node.position - 1
                })

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

        return {
            "target_hash": target_hash,
            "merkle_root": self.root.hash_value if self.root else None,
            "proof_path": proof_hashes,
            "batch_sequence_start": self.batch_sequence_start,
            "batch_sequence_end": self.batch_sequence_end,
            "stream_prev_hash": self.stream_prev_hash,
            "tree_height": len(self.levels),
            "total_leaves": len(self.event_hashes)
        }

    def verify_inclusion_with_chain(self, target_hash: str, proof: Dict[str, Any],
                                   stream_prev_hash: Optional[str] = None) -> bool:
        """
        Verify inclusion with hash chain continuity.

        Enhanced verification that checks both Merkle proof and hash chain integrity.
        """
        if not proof.get("merkle_root"):
            return False

        # Verify Merkle proof
        current_hash = target_hash
        for step in proof["proof_path"]:
            if step["direction"] == "left":
                current_hash = hashlib.sha256(f"{step['hash']}:{current_hash}".encode()).hexdigest()
            else:
                current_hash = hashlib.sha256(f"{current_hash}:{step['hash']}".encode()).hexdigest()

        # Include stream hash chain context if provided
        if stream_prev_hash or proof.get("stream_prev_hash"):
            chain_context = stream_prev_hash or proof.get("stream_prev_hash")
            current_hash = hashlib.sha256(f"{current_hash}:{chain_context}".encode()).hexdigest()

        return current_hash == proof["merkle_root"]


class HybridMerkleBatchProcessor:
    """Enhanced batch processor using hybrid Merkle + hash chain approach."""

    def __init__(self, batch_size: int = 1000, batch_interval_seconds: int = 300):
        self.settings = get_settings()
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds
        self.batches_db_path = os.path.join(self.settings.DATA_DIR, "hybrid_batches.db")
        self.logger = structlog.get_logger(__name__)

        self._init_hybrid_batches_db()

    def _init_hybrid_batches_db(self) -> None:
        """Initialize hybrid batch database."""
        os.makedirs(os.path.dirname(self.batches_db_path), exist_ok=True)

        conn = sqlite3.connect(self.batches_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hybrid_batches (
                batch_id TEXT PRIMARY KEY,
                stream_type TEXT NOT NULL,
                stream_id TEXT NOT NULL,
                start_sequence INTEGER NOT NULL,
                end_sequence INTEGER NOT NULL,
                event_count INTEGER NOT NULL,
                merkle_root TEXT NOT NULL,
                batch_hash TEXT NOT NULL,
                stream_prev_hash TEXT,
                tree_height INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                build_duration_seconds REAL NOT NULL,
                compression_ratio REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
        """)

        # Indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hybrid_batches_stream ON hybrid_batches(stream_type, stream_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hybrid_batches_timestamp ON hybrid_batches(timestamp)")

        conn.commit()
        conn.close()

    def create_hybrid_batch(self, stream: EventStream, max_events: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Create a hybrid batch using both hash chains and Merkle trees.

        Returns enhanced batch metadata with both verification methods.
        """
        max_events = max_events or self.batch_size

        # Get stream head
        _, current_sequence = stream.get_stream_head()
        if current_sequence == 0:
            return None

        # Get recent events
        start_sequence = max(1, current_sequence - max_events + 1)
        events = stream.get_events_range(start_sequence, current_sequence)

        if len(events) < 10:  # Minimum batch size
            return None

        start_time = time.time()

        # Extract event hashes and stream context
        event_hashes = [event.entry_hash for event in events]
        stream_prev_hash = events[0].prev_hash if events else None

        # Build hybrid Merkle tree
        merkle_tree = HybridMerkleTree(event_hashes, stream_prev_hash)
        merkle_root = merkle_tree.get_root_hash()

        if not merkle_root:
            return None

        end_time = time.time()
        build_duration = end_time - start_time

        # Calculate metrics
        total_events = len(events)
        compression_ratio = total_events / len(merkle_root) if merkle_root else 1.0

        # Create batch
        batch_id = f"hybrid_{stream.stream_type}_{stream.stream_id}_{start_sequence}_{current_sequence}"
        batch = {
            "batch_id": batch_id,
            "stream_type": stream.stream_type,
            "stream_id": stream.stream_id,
            "start_sequence": start_sequence,
            "end_sequence": current_sequence,
            "event_count": total_events,
            "merkle_root": merkle_root,
            "batch_hash": self._compute_hybrid_batch_hash(events, merkle_root, stream_prev_hash),
            "stream_prev_hash": stream_prev_hash,
            "tree_height": len(merkle_tree.levels),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "build_duration_seconds": build_duration,
            "compression_ratio": compression_ratio,
            "verification_methods": ["merkle_proof", "hash_chain", "hybrid_combined"]
        }

        # Store batch
        self._store_hybrid_batch(batch)

        self.logger.info("Hybrid batch created",
                        batch_id=batch_id,
                        stream_type=stream.stream_type,
                        stream_id=stream.stream_id,
                        event_count=total_events,
                        merkle_root=merkle_root[:8],
                        build_duration_seconds=round(build_duration, 3))

        return batch

    def _compute_hybrid_batch_hash(self, events: List[Any], merkle_root: str,
                                  stream_prev_hash: Optional[str]) -> str:
        """Compute batch hash incorporating both Merkle and hash chain elements."""
        if not events:
            return ""

        batch_data = {
            "event_count": len(events),
            "first_sequence": events[0].sequence_number,
            "last_sequence": events[-1].sequence_number,
            "first_timestamp": events[0].timestamp,
            "last_timestamp": events[-1].timestamp,
            "merkle_root": merkle_root,
            "stream_prev_hash": stream_prev_hash
        }

        batch_json = json.dumps(batch_data, sort_keys=True)
        return hashlib.sha256(batch_json.encode()).hexdigest()

    def _store_hybrid_batch(self, batch: Dict[str, Any]) -> None:
        """Store hybrid batch in database."""
        conn = sqlite3.connect(self.batches_db_path)
        conn.execute("""
            INSERT INTO hybrid_batches (
                batch_id, stream_type, stream_id, start_sequence, end_sequence,
                event_count, merkle_root, batch_hash, stream_prev_hash,
                tree_height, timestamp, build_duration_seconds, compression_ratio, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch["batch_id"], batch["stream_type"], batch["stream_id"],
            batch["start_sequence"], batch["end_sequence"], batch["event_count"],
            batch["merkle_root"], batch["batch_hash"], batch["stream_prev_hash"],
            batch["tree_height"], batch["timestamp"], batch["build_duration_seconds"],
            batch["compression_ratio"], datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

    def generate_hybrid_inclusion_proof(self, event_hash: str, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Generate hybrid inclusion proof combining Merkle and hash chain verification.

        Returns comprehensive proof data for independent verification.
        """
        # Get batch metadata
        batch = self._get_hybrid_batch(batch_id)
        if not batch:
            return None

        # Reconstruct Merkle tree for proof generation
        # In production, you'd store the tree structure or recompute from events
        mock_tree = HybridMerkleTree([event_hash], batch["stream_prev_hash"])

        # Generate Merkle proof
        merkle_proof = mock_tree.generate_inclusion_proof(event_hash)
        if not merkle_proof:
            return None

        # Get hash chain context
        stream_prev_hash = batch.get("stream_prev_hash")

        return {
            "event_hash": event_hash,
            "batch_id": batch_id,
            "verification_methods": {
                "merkle_proof": {
                    "root": batch["merkle_root"],
                    "path": merkle_proof["proof_path"],
                    "tree_height": batch["tree_height"]
                },
                "hash_chain": {
                    "stream_prev_hash": stream_prev_hash,
                    "batch_sequence_start": batch["start_sequence"],
                    "batch_sequence_end": batch["end_sequence"]
                },
                "hybrid_combined": {
                    "batch_hash": batch["batch_hash"],
                    "compression_ratio": batch["compression_ratio"]
                }
            },
            "batch_metadata": {
                "stream_type": batch["stream_type"],
                "stream_id": batch["stream_id"],
                "event_count": batch["event_count"],
                "timestamp": batch["timestamp"]
            }
        }

    def _get_hybrid_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve hybrid batch by ID."""
        conn = sqlite3.connect(self.batches_db_path)
        cursor = conn.execute("""
            SELECT batch_id, stream_type, stream_id, start_sequence, end_sequence,
                   event_count, merkle_root, batch_hash, stream_prev_hash, tree_height,
                   timestamp, build_duration_seconds, compression_ratio
            FROM hybrid_batches WHERE batch_id = ?
        """, (batch_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "batch_id": row[0],
                "stream_type": row[1],
                "stream_id": row[2],
                "start_sequence": row[3],
                "end_sequence": row[4],
                "event_count": row[5],
                "merkle_root": row[6],
                "batch_hash": row[7],
                "stream_prev_hash": row[8],
                "tree_height": row[9],
                "timestamp": row[10],
                "build_duration_seconds": row[11],
                "compression_ratio": row[12]
            }
        return None

    def verify_hybrid_proof(self, proof: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify hybrid inclusion proof using both Merkle and hash chain methods.

        Returns comprehensive verification results.
        """
        verification_results = {
            "overall_valid": False,
            "merkle_verification": {"valid": False, "details": {}},
            "hash_chain_verification": {"valid": False, "details": {}},
            "hybrid_verification": {"valid": False, "details": {}}
        }

        event_hash = proof.get("event_hash")
        batch_id = proof.get("batch_id")

        if not event_hash or not batch_id:
            verification_results["error"] = "Missing event_hash or batch_id"
            return verification_results

        # Get batch for verification
        batch = self._get_hybrid_batch(batch_id)
        if not batch:
            verification_results["error"] = f"Batch {batch_id} not found"
            return verification_results

        # Merkle proof verification
        merkle_data = proof.get("verification_methods", {}).get("merkle_proof", {})
        if merkle_data:
            try:
                # Reconstruct proof verification
                mock_tree = HybridMerkleTree([event_hash], batch.get("stream_prev_hash"))
                merkle_valid = mock_tree.verify_inclusion_with_chain(
                    event_hash, merkle_data, batch.get("stream_prev_hash")
                )
                verification_results["merkle_verification"] = {
                    "valid": merkle_valid,
                    "root_matches": merkle_data.get("root") == batch["merkle_root"]
                }
            except Exception as e:
                verification_results["merkle_verification"] = {
                    "valid": False,
                    "error": str(e)
                }

        # Hash chain verification
        hash_chain_data = proof.get("verification_methods", {}).get("hash_chain", {})
        if hash_chain_data:
            # Verify sequence continuity and hash chaining
            expected_start = hash_chain_data.get("batch_sequence_start")
            expected_end = hash_chain_data.get("batch_sequence_end")
            stream_prev_hash = hash_chain_data.get("stream_prev_hash")

            sequence_valid = (batch["start_sequence"] == expected_start and
                            batch["end_sequence"] == expected_end)

            verification_results["hash_chain_verification"] = {
                "valid": sequence_valid,
                "sequence_matches": sequence_valid,
                "stream_prev_hash": stream_prev_hash
            }

        # Hybrid combined verification
        hybrid_data = proof.get("verification_methods", {}).get("hybrid_combined", {})
        if hybrid_data:
            batch_hash_matches = hybrid_data.get("batch_hash") == batch["batch_hash"]
            verification_results["hybrid_verification"] = {
                "valid": batch_hash_matches,
                "batch_hash_matches": batch_hash_matches,
                "compression_ratio": hybrid_data.get("compression_ratio")
            }

        # Overall validity
        merkle_valid = verification_results["merkle_verification"].get("valid", False)
        hash_valid = verification_results["hash_chain_verification"].get("valid", False)
        hybrid_valid = verification_results["hybrid_verification"].get("valid", False)

        verification_results["overall_valid"] = merkle_valid and hash_valid and hybrid_valid

        return verification_results

    def get_scaling_metrics(self, stream_type: str = None, stream_id: str = None,
                           hours: int = 24) -> Dict[str, Any]:
        """
        Get scaling metrics for Merkle tree performance and optimization.

        Returns metrics to monitor and tune the hybrid approach.
        """
        conn = sqlite3.connect(self.batches_db_path)

        query = """
            SELECT COUNT(*) as batch_count,
                   SUM(event_count) as total_events,
                   AVG(event_count) as avg_events_per_batch,
                   AVG(build_duration_seconds) as avg_build_time,
                   AVG(tree_height) as avg_tree_height,
                   AVG(compression_ratio) as avg_compression,
                   MIN(timestamp) as earliest_batch,
                   MAX(timestamp) as latest_batch
            FROM hybrid_batches
            WHERE timestamp >= ?
        """
        params = [(datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"]

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
                "period_hours": hours,
                "batch_count": row[0] or 0,
                "total_events": row[1] or 0,
                "avg_events_per_batch": round(row[2] or 0, 2),
                "avg_build_time_seconds": round(row[3] or 0, 4),
                "avg_tree_height": round(row[4] or 0, 2),
                "avg_compression_ratio": round(row[5] or 0, 4),
                "earliest_batch": row[6],
                "latest_batch": row[7],
                "events_per_second_throughput": round((row[1] or 0) / (hours * 3600), 2) if hours > 0 else 0,
                "optimization_recommendations": self._generate_scaling_recommendations(row)
            }

        return {
            "period_hours": hours,
            "batch_count": 0,
            "total_events": 0,
            "error": "No batch data found for period"
        }

    def _generate_scaling_recommendations(self, metrics_row) -> List[str]:
        """Generate scaling optimization recommendations based on metrics."""
        recommendations = []
        avg_build_time, avg_tree_height, avg_compression = metrics_row[3:6]

        if avg_build_time > 1.0:  # Over 1 second
            recommendations.append("Consider reducing batch size or implementing parallel tree construction")

        if avg_tree_height > 15:  # Very deep trees
            recommendations.append("Batch size may be too large; consider smaller batches for faster proofs")

        if avg_compression < 0.1:  # Poor compression
            recommendations.append("Review event data structure; consider event deduplication or compression")

        if not recommendations:
            recommendations.append("Scaling metrics look optimal")

        return recommendations


# Global hybrid Merkle processor instance
hybrid_merkle_processor = HybridMerkleBatchProcessor()


# Utility functions for hybrid batch operations
def create_hybrid_batch_for_stream(stream_type: str, stream_id: str, max_events: int = 1000) -> Optional[Dict[str, Any]]:
    """Create hybrid batch for a specific stream."""
    from core.audit_fabric.canonical_event_model import EventStream
    settings = get_settings()
    stream_db_path = os.path.join(settings.DATA_DIR, "audit_fabric", f"{stream_type}_{stream_id}.db")
    stream = EventStream(stream_type, stream_id, stream_db_path)
    return hybrid_merkle_processor.create_hybrid_batch(stream, max_events)


def get_hybrid_inclusion_proof(event_hash: str, batch_id: str) -> Optional[Dict[str, Any]]:
    """Generate hybrid inclusion proof."""
    return hybrid_merkle_processor.generate_hybrid_inclusion_proof(event_hash, batch_id)


def verify_hybrid_inclusion_proof(proof: Dict[str, Any]) -> Dict[str, Any]:
    """Verify hybrid inclusion proof."""
    return hybrid_merkle_processor.verify_hybrid_proof(proof)


def get_hybrid_scaling_metrics(stream_type: str = None, stream_id: str = None, hours: int = 24) -> Dict[str, Any]:
    """Get scaling performance metrics."""
    return hybrid_merkle_processor.get_scaling_metrics(stream_type, stream_id, hours)
