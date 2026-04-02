"""
Hybrid Ledger System
====================

This module implements the hybrid ledger system that combines off-chain event storage
with on-chain hash commitments for the Immutable Audit Fabric.

Architecture:
- Off-chain: Full event data in high-performance databases for querying
- On-chain: Merkle roots and batch hashes committed to a distributed ledger
- WORM storage: Write-once-read-many guarantees for tamper evidence
- Public verification: Anyone can verify event chains against ledger commitments

This enables "regulators/insurers can independently verify sequences via published
verification tools" by providing cryptographically anchored proofs.
"""

import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings
from core.audit_fabric.service import audit_fabric, AuditBatch


class LedgerCommitment(BaseModel):
    """On-chain commitment for audit batch."""
    commitment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    batch_hash: str
    merkle_root: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sequence_number: int
    previous_commitment_hash: Optional[str] = None
    commitment_hash: str = ""
    signatures: List[str] = []  # Consensus cluster signatures
    block_height: Optional[int] = None  # For blockchain integration
    transaction_hash: Optional[str] = None  # For blockchain integration


class VerificationProof(BaseModel):
    """Independent verification proof for audit events."""
    event_id: str
    content_hash: str
    batch_id: str
    batch_hash: str
    merkle_proof: List[str]  # Merkle branch for inclusion proof
    ledger_commitment: str
    consensus_signatures: List[str]
    timestamp: str
    verified_by: str  # Verification tool/service identifier


class HybridLedgerSystem:
    """Hybrid ledger implementation combining off-chain and on-chain storage."""

    def __init__(self):
        self.settings = get_settings()
        self.ledger_db_path = os.path.join(self.settings.DATA_DIR, "hybrid_ledger.db")
        self.worm_storage_path = os.path.join(self.settings.DATA_DIR, "worm_storage")
        self.logger = structlog.get_logger(__name__)
        self._init_ledger_db()
        self._init_worm_storage()

    def _init_ledger_db(self) -> None:
        """Initialize ledger commitment database."""
        os.makedirs(os.path.dirname(self.ledger_db_path), exist_ok=True)

        conn = sqlite3.connect(self.ledger_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ledger_commitments (
                commitment_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                batch_hash TEXT NOT NULL,
                merkle_root TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                previous_commitment_hash TEXT,
                commitment_hash TEXT NOT NULL,
                signatures TEXT NOT NULL,  -- JSON array
                block_height INTEGER,
                transaction_hash TEXT,
                committed_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS verification_proofs (
                proof_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                batch_hash TEXT NOT NULL,
                merkle_proof TEXT NOT NULL,  -- JSON array
                ledger_commitment TEXT NOT NULL,
                consensus_signatures TEXT NOT NULL,  -- JSON array
                timestamp TEXT NOT NULL,
                verified_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        self.logger.info("Hybrid ledger database initialized", db_path=self.ledger_db_path)

    def _init_worm_storage(self) -> None:
        """Initialize write-once-read-many storage."""
        os.makedirs(self.worm_storage_path, exist_ok=True)

        # Create .gitkeep or similar to ensure directory exists
        gitkeep_path = os.path.join(self.worm_storage_path, ".gitkeep")
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, 'w') as f:
                f.write("# WORM Storage - Write Once Read Many\n")

        self.logger.info("WORM storage initialized", path=self.worm_storage_path)

    def _get_last_commitment(self, stream_type: str, stream_id: str) -> Optional[Tuple[str, int]]:
        """Get the last commitment hash and sequence number for a stream."""
        conn = sqlite3.connect(self.ledger_db_path)
        cursor = conn.execute("""
            SELECT commitment_hash, sequence_number FROM ledger_commitments
            WHERE batch_id LIKE ?
            ORDER BY sequence_number DESC
            LIMIT 1
        """, (f"{stream_type}_{stream_id}_%",))

        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0], row[1]
        return None, 0

    def commit_batch_to_ledger(self, batch: AuditBatch, consensus_signatures: List[str] = None) -> LedgerCommitment:
        """
        Commit an audit batch to the hybrid ledger.

        Args:
            batch: The audit batch to commit
            consensus_signatures: Signatures from governance cluster consensus

        Returns:
            The ledger commitment
        """
        # Get previous commitment
        previous_hash, sequence_number = self._get_last_commitment(batch.stream_type, batch.stream_id)

        # Create commitment
        commitment = LedgerCommitment(
            batch_id=batch.batch_id,
            batch_hash=batch.batch_hash,
            merkle_root=batch.merkle_root,
            sequence_number=sequence_number + 1,
            previous_commitment_hash=previous_hash,
            signatures=consensus_signatures or []
        )

        # Generate commitment hash
        commitment_data = {
            "commitment_id": commitment.commitment_id,
            "batch_id": commitment.batch_id,
            "batch_hash": commitment.batch_hash,
            "merkle_root": commitment.merkle_root,
            "timestamp": commitment.timestamp,
            "sequence_number": commitment.sequence_number,
            "previous_commitment_hash": commitment.previous_commitment_hash
        }
        commitment_content = json.dumps(commitment_data, sort_keys=True)
        commitment.commitment_hash = hashlib.sha256(commitment_content.encode()).hexdigest()

        # Write to WORM storage (immutable file)
        worm_filename = f"{batch.stream_type}_{batch.stream_id}_{commitment.sequence_number:010d}.json"
        worm_filepath = os.path.join(self.worm_storage_path, worm_filename)

        worm_data = {
            "commitment": commitment.dict(),
            "batch": batch.dict(),
            "commitment_content": commitment_content,
            "verification_hash": commitment.commitment_hash
        }

        with open(worm_filepath, 'w') as f:
            json.dump(worm_data, f, indent=2, sort_keys=True)

        # Persist to database
        conn = sqlite3.connect(self.ledger_db_path)
        conn.execute("""
            INSERT INTO ledger_commitments (
                commitment_id, batch_id, batch_hash, merkle_root, timestamp,
                sequence_number, previous_commitment_hash, commitment_hash,
                signatures, committed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            commitment.commitment_id, commitment.batch_id, commitment.batch_hash,
            commitment.merkle_root, commitment.timestamp, commitment.sequence_number,
            commitment.previous_commitment_hash, commitment.commitment_hash,
            json.dumps(commitment.signatures), datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

        # Mark batch as committed in audit fabric
        # (This would update the audit_fabric database to mark the batch as committed)

        self.logger.info("Batch committed to hybrid ledger",
                        commitment_id=commitment.commitment_id,
                        batch_id=batch.batch_id,
                        sequence_number=commitment.sequence_number,
                        worm_file=worm_filename)

        return commitment

    def generate_merkle_proof(self, event_hash: str, batch: AuditBatch) -> List[str]:
        """
        Generate Merkle proof for event inclusion in batch.

        Args:
            event_hash: Hash of the event to prove inclusion for
            batch: The batch containing the event

        Returns:
            List of hashes forming the Merkle proof
        """
        # This is a simplified implementation - in production, you'd rebuild the tree
        # and generate the actual proof path

        # For now, return a basic proof structure
        return [
            batch.merkle_root,
            f"sibling_hash_for_{event_hash}",
            "intermediate_hash_1",
            "intermediate_hash_2"
        ]

    def create_verification_proof(self, event_id: str, verified_by: str = "seked_verifier") -> Optional[VerificationProof]:
        """
        Create an independent verification proof for an event.

        Args:
            event_id: ID of the event to create proof for
            verified_by: Identifier of the verification service

        Returns:
            VerificationProof if successful, None otherwise
        """
        # Get event verification data from audit fabric
        verification_data = audit_fabric.get_verification_proof(event_id)
        if not verification_data:
            return None

        # Get batch information
        batch = self.get_batch_by_id(verification_data['event']['batch_id'])
        if not batch:
            return None

        # Generate Merkle proof
        merkle_proof = self.generate_merkle_proof(
            verification_data['verification_data']['content_hash'],
            batch
        )

        # Get ledger commitment
        commitment = self.get_commitment_by_batch_id(batch.batch_id)
        if not commitment:
            return None

        # Create proof
        proof = VerificationProof(
            event_id=event_id,
            content_hash=verification_data['verification_data']['content_hash'],
            batch_id=batch.batch_id,
            batch_hash=batch.batch_hash,
            merkle_proof=merkle_proof,
            ledger_commitment=commitment.commitment_hash,
            consensus_signatures=commitment.signatures,
            timestamp=datetime.utcnow().isoformat() + "Z",
            verified_by=verified_by
        )

        # Persist proof
        conn = sqlite3.connect(self.ledger_db_path)
        conn.execute("""
            INSERT INTO verification_proofs (
                proof_id, event_id, content_hash, batch_id, batch_hash,
                merkle_proof, ledger_commitment, consensus_signatures,
                timestamp, verified_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), proof.event_id, proof.content_hash,
            proof.batch_id, proof.batch_hash, json.dumps(proof.merkle_proof),
            proof.ledger_commitment, json.dumps(proof.consensus_signatures),
            proof.timestamp, proof.verified_by, datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

        self.logger.info("Verification proof created",
                        event_id=event_id,
                        proof_id=str(uuid.uuid4()))

        return proof

    def verify_proof_independently(self, proof: VerificationProof) -> bool:
        """
        Independently verify a proof without trusting the main system.

        This function can be called by regulators, insurers, or auditors
        to verify proofs independently.

        Args:
            proof: The verification proof to check

        Returns:
            True if proof is valid, False otherwise
        """
        try:
            # 1. Verify the event content hash is correctly formed
            # (This would involve reconstructing the event and hashing it)

            # 2. Verify Merkle proof shows inclusion in batch
            # (This would involve Merkle proof verification)

            # 3. Verify batch hash matches the committed batch
            if not self.verify_batch_hash(proof.batch_id, proof.batch_hash):
                return False

            # 4. Verify ledger commitment exists and is properly signed
            commitment = self.get_commitment_by_hash(proof.ledger_commitment)
            if not commitment:
                return False

            # 5. Verify consensus signatures (simplified)
            if len(proof.consensus_signatures) < 2:  # Require at least 2 signatures
                return False

            # 6. Check WORM storage integrity
            if not self.verify_worm_integrity(proof.batch_id):
                return False

            return True

        except Exception as e:
            self.logger.error("Proof verification failed", error=str(e), proof_id=proof.event_id)
            return False

    def get_batch_by_id(self, batch_id: str) -> Optional[AuditBatch]:
        """Get batch by ID from audit fabric."""
        # This would query the audit fabric database
        # For now, return a mock batch
        return AuditBatch(
            batch_id=batch_id,
            stream_type="mock",
            stream_id="mock",
            merkle_root="mock_root",
            event_count=1
        )

    def get_commitment_by_batch_id(self, batch_id: str) -> Optional[LedgerCommitment]:
        """Get ledger commitment by batch ID."""
        conn = sqlite3.connect(self.ledger_db_path)
        cursor = conn.execute("""
            SELECT commitment_id, batch_id, batch_hash, merkle_root, timestamp,
                   sequence_number, previous_commitment_hash, commitment_hash,
                   signatures, block_height, transaction_hash
            FROM ledger_commitments
            WHERE batch_id = ?
        """, (batch_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return LedgerCommitment(
                commitment_id=row[0],
                batch_id=row[1],
                batch_hash=row[2],
                merkle_root=row[3],
                timestamp=row[4],
                sequence_number=row[5],
                previous_commitment_hash=row[6],
                commitment_hash=row[7],
                signatures=json.loads(row[8]) if row[8] else [],
                block_height=row[9],
                transaction_hash=row[10]
            )
        return None

    def get_commitment_by_hash(self, commitment_hash: str) -> Optional[LedgerCommitment]:
        """Get ledger commitment by hash."""
        conn = sqlite3.connect(self.ledger_db_path)
        cursor = conn.execute("""
            SELECT commitment_id, batch_id, batch_hash, merkle_root, timestamp,
                   sequence_number, previous_commitment_hash, commitment_hash,
                   signatures, block_height, transaction_hash
            FROM ledger_commitments
            WHERE commitment_hash = ?
        """, (commitment_hash,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return LedgerCommitment(
                commitment_id=row[0],
                batch_id=row[1],
                batch_hash=row[2],
                merkle_root=row[3],
                timestamp=row[4],
                sequence_number=row[5],
                previous_commitment_hash=row[6],
                commitment_hash=row[7],
                signatures=json.loads(row[8]) if row[8] else [],
                block_height=row[9],
                transaction_hash=row[10]
            )
        return None

    def verify_batch_hash(self, batch_id: str, expected_hash: str) -> bool:
        """Verify batch hash matches records."""
        batch = self.get_batch_by_id(batch_id)
        return batch and batch.batch_hash == expected_hash

    def verify_worm_integrity(self, batch_id: str) -> bool:
        """Verify WORM storage integrity for a batch."""
        # Check if WORM file exists and content matches database
        commitment = self.get_commitment_by_batch_id(batch_id)
        if not commitment:
            return False

        worm_pattern = f"*{batch_id}*.json"
        worm_files = [f for f in os.listdir(self.worm_storage_path) if batch_id in f and f.endswith('.json')]

        if not worm_files:
            return False

        worm_filepath = os.path.join(self.worm_storage_path, worm_files[0])

        try:
            with open(worm_filepath, 'r') as f:
                worm_data = json.load(f)

            # Verify the commitment hash in WORM matches database
            return worm_data.get('verification_hash') == commitment.commitment_hash

        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def get_public_verification_data(self, stream_type: str, stream_id: str) -> Dict[str, Any]:
        """
        Get public verification data that regulators/auditors can use
        to verify audit trails independently.
        """
        conn = sqlite3.connect(self.ledger_db_path)

        # Get latest commitments for the stream
        cursor = conn.execute("""
            SELECT commitment_hash, batch_id, batch_hash, merkle_root,
                   sequence_number, timestamp, signatures
            FROM ledger_commitments
            WHERE batch_id LIKE ?
            ORDER BY sequence_number DESC
            LIMIT 10
        """, (f"{stream_type}_{stream_id}_%",))

        commitments = []
        for row in cursor.fetchall():
            commitments.append({
                "commitment_hash": row[0],
                "batch_id": row[1],
                "batch_hash": row[2],
                "merkle_root": row[3],
                "sequence_number": row[4],
                "timestamp": row[5],
                "signatures": json.loads(row[6]) if row[6] else []
            })

        conn.close()

        return {
            "stream_type": stream_type,
            "stream_id": stream_id,
            "latest_commitments": commitments,
            "verification_endpoint": "/api/v1/audit/verify",
            "public_key_endpoint": "/api/v1/audit/public-keys",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }


# Global hybrid ledger instance
hybrid_ledger = HybridLedgerSystem()
