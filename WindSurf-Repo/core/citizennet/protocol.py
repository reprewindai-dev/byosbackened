"""
CitizenNet Protocol
===================

This module implements the CitizenNet protocol - the communication layer that makes
Seked the "only practical passport" for AI-to-AI communication.

Architecture:
- Message format: Every AI-to-AI message includes citizen passport
- Passport validation: Sender ID, trust tier, capabilities, decision token
- Gatekeeping: Client libraries reject messages without valid passports
- Decision tokens: Fresh consensus-backed authorization from Seked
- Network effect: Only citizens can communicate, creating lock-in

This creates the network effect: "to talk to anyone important, an AI must be a citizen,
and to be a citizen it must go through Seked."
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import structlog

from core.config import get_settings
from core.ai_citizenship.service import ai_citizenship_service
from core.ai_citizenship.identity_system import citizen_identity_system
from core.consensus.distributed_system import distributed_consensus
from core.audit_fabric.service import audit_fabric


class CitizenPassport(BaseModel):
    """AI Citizen's communication passport."""
    citizen_id: str
    session_id: str
    trust_level: str
    capabilities: List[str]
    jurisdiction: str
    public_key_pem: str
    issued_at: str
    expires_at: str
    decision_token: str  # Consensus-backed authorization
    context: Dict[str, str] = {}  # Use case, data class, etc.


class CitizenNetMessage(BaseModel):
    """CitizenNet protocol message format."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_passport: CitizenPassport
    recipient_id: str  # Target AI citizen ID
    message_type: str  # request, response, notification, etc.
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    signature: str = ""  # Signed by sender's session key

    @validator('message_type')
    def validate_message_type(cls, v):
        valid_types = ['request', 'response', 'notification', 'handshake', 'error']
        if v not in valid_types:
            raise ValueError(f'Message type must be one of: {valid_types}')
        return v


class DecisionToken(BaseModel):
    """Consensus-backed decision token for communication authorization."""
    token_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    action: str  # communicate, share_data, execute, etc.
    target_id: Optional[str] = None  # Target citizen or resource
    context: Dict[str, str] = {}
    decision_result: str  # allow, deny
    issued_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    expires_at: str
    consensus_signatures: List[str]
    ledger_reference: str


class CitizenNetProtocol:
    """CitizenNet protocol implementation."""

    def __init__(self):
        self.settings = get_settings()
        self.protocol_path = os.path.join(self.settings.DATA_DIR, "citizennet")
        self.messages_db_path = os.path.join(self.protocol_path, "messages.db")
        self.tokens_db_path = os.path.join(self.protocol_path, "tokens.db")
        self.logger = structlog.get_logger(__name__)

        # Protocol configuration
        self.token_validity_hours = int(os.getenv("CITIZENNET_TOKEN_VALIDITY", "1"))
        self.max_message_size = int(os.getenv("CITIZENNET_MAX_MESSAGE_SIZE", "1048576"))  # 1MB

        self._init_protocol_storage()

    def _init_protocol_storage(self) -> None:
        """Initialize CitizenNet protocol storage."""
        os.makedirs(self.protocol_path, exist_ok=True)

        # Initialize messages database
        if not os.path.exists(self.messages_db_path):
            self._init_messages_db()

        # Initialize tokens database
        if not os.path.exists(self.tokens_db_path):
            self._init_tokens_db()

        self.logger.info("CitizenNet protocol storage initialized")

    def _init_messages_db(self) -> None:
        """Initialize message storage database."""
        import sqlite3

        conn = sqlite3.connect(self.messages_db_path)
        conn.execute("""
            CREATE TABLE citizennet_messages (
                message_id TEXT PRIMARY KEY,
                sender_citizen_id TEXT NOT NULL,
                sender_session_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                payload TEXT NOT NULL,  -- JSON
                timestamp TEXT NOT NULL,
                signature TEXT NOT NULL,
                validated BOOLEAN NOT NULL DEFAULT FALSE,
                validation_error TEXT,
                processed_at TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes for efficient queries
        conn.execute("CREATE INDEX idx_messages_sender ON citizennet_messages(sender_citizen_id)")
        conn.execute("CREATE INDEX idx_messages_recipient ON citizennet_messages(recipient_id)")
        conn.execute("CREATE INDEX idx_messages_timestamp ON citizennet_messages(timestamp)")

        conn.commit()
        conn.close()

    def _init_tokens_db(self) -> None:
        """Initialize decision tokens database."""
        import sqlite3

        conn = sqlite3.connect(self.tokens_db_path)
        conn.execute("""
            CREATE TABLE decision_tokens (
                token_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target_id TEXT,
                context TEXT NOT NULL,  -- JSON
                decision_result TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consensus_signatures TEXT NOT NULL,  -- JSON array
                ledger_reference TEXT NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX idx_tokens_citizen ON decision_tokens(citizen_id)")
        conn.execute("CREATE INDEX idx_tokens_expires ON decision_tokens(expires_at)")

        conn.commit()
        conn.close()

    def _sign_message(self, message: CitizenNetMessage, session_private_key_pem: str) -> str:
        """Sign a message with the sender's session private key."""
        from cryptography.hazmat.primitives import serialization, hashes, padding

        # Load private key
        private_key = serialization.load_pem_private_key(
            session_private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )

        # Create canonical message representation
        message_data = {
            "message_id": message.message_id,
            "sender_passport": {
                "citizen_id": message.sender_passport.citizen_id,
                "session_id": message.sender_passport.session_id,
                "trust_level": message.sender_passport.trust_level,
                "capabilities": sorted(message.sender_passport.capabilities),
                "jurisdiction": message.sender_passport.jurisdiction,
                "issued_at": message.sender_passport.issued_at,
                "expires_at": message.sender_passport.expires_at,
                "decision_token": message.sender_passport.decision_token
            },
            "recipient_id": message.recipient_id,
            "message_type": message.message_type,
            "payload": message.payload,
            "timestamp": message.timestamp
        }

        canonical_data = json.dumps(message_data, sort_keys=True, separators=(',', ':'))

        # Sign with PSS padding
        signature = private_key.sign(
            canonical_data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        import base64
        return base64.b64encode(signature).decode()

    def _verify_message_signature(self, message: CitizenNetMessage) -> bool:
        """Verify message signature against sender's session public key."""
        try:
            from cryptography.hazmat.primitives import serialization, hashes, padding

            # Load sender's session public key
            public_key = serialization.load_pem_public_key(
                message.sender_passport.public_key_pem.encode(),
                backend=default_backend()
            )

            # Create canonical message representation
            message_data = {
                "message_id": message.message_id,
                "sender_passport": {
                    "citizen_id": message.sender_passport.citizen_id,
                    "session_id": message.sender_passport.session_id,
                    "trust_level": message.sender_passport.trust_level,
                    "capabilities": sorted(message.sender_passport.capabilities),
                    "jurisdiction": message.sender_passport.jurisdiction,
                    "issued_at": message.sender_passport.issued_at,
                    "expires_at": message.sender_passport.expires_at,
                    "decision_token": message.sender_passport.decision_token
                },
                "recipient_id": message.recipient_id,
                "message_type": message.message_type,
                "payload": message.payload,
                "timestamp": message.timestamp
            }

            canonical_data = json.dumps(message_data, sort_keys=True, separators=(',', ':'))

            # Verify signature
            import base64
            signature_bytes = base64.b64decode(message.signature)

            public_key.verify(
                signature_bytes,
                canonical_data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return True

        except Exception as e:
            self.logger.error("Message signature verification failed",
                            message_id=message.message_id,
                            error=str(e))
            return False

    def _validate_passport(self, passport: CitizenPassport) -> Tuple[bool, Optional[str]]:
        """
        Validate a citizen passport.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check expiration
        expires_at = datetime.fromisoformat(passport.expires_at.replace('Z', '+00:00'))
        if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
            return False, "Passport expired"

        # Verify citizen exists and has valid citizenship
        citizen = ai_citizenship_service.get_citizenship(passport.citizen_id)
        if not citizen:
            return False, "Citizen not found"

        # Verify trust level matches
        if citizen.trust_level != passport.trust_level:
            return False, "Trust level mismatch"

        # Verify session key exists and is valid
        session = citizen_identity_system.get_session_key(passport.session_id)
        if not session:
            return False, "Session key not found or expired"

        # Verify session signature (citizen signed the session)
        if not citizen_identity_system.verify_session_signature(session):
            return False, "Session signature invalid"

        # Verify decision token
        if not self._validate_decision_token(passport.decision_token):
            return False, "Decision token invalid"

        # Verify passport matches session
        if (passport.citizen_id != session.citizen_id or
            passport.session_id != session.session_id or
            passport.public_key_pem != session.public_key_pem):
            return False, "Passport does not match session"

        return True, None

    def _validate_decision_token(self, token_id: str) -> bool:
        """Validate a decision token."""
        import sqlite3

        conn = sqlite3.connect(self.tokens_db_path)
        cursor = conn.execute("""
            SELECT expires_at, decision_result, revoked
            FROM decision_tokens
            WHERE token_id = ? AND decision_result = 'allow'
        """, (token_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return False

        expires_at, decision_result, revoked = row

        # Check expiration
        exp_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if datetime.utcnow().replace(tzinfo=exp_datetime.tzinfo) > exp_datetime:
            return False

        # Check if revoked
        if revoked:
            return False

        return True

    async def issue_decision_token(self, citizen_id: str, action: str,
                                  target_id: Optional[str] = None,
                                  context: Optional[Dict[str, str]] = None) -> Optional[DecisionToken]:
        """
        Issue a consensus-backed decision token for communication.

        Args:
            citizen_id: Citizen requesting authorization
            action: Action being authorized (communicate, share_data, etc.)
            target_id: Target citizen/resource ID
            context: Authorization context

        Returns:
            Decision token if authorized, None otherwise
        """
        from core.consensus.distributed_system import GovernanceDecision

        # Create governance decision for authorization
        decision = GovernanceDecision(
            decision_type="communication_authorization",
            subject_id=citizen_id,
            subject_type="citizen",
            proposed_action="allow",
            context={
                "action": action,
                "target_id": target_id or "",
                **(context or {})
            },
            proposed_by="citizennet_protocol"
        )

        # Get consensus on the decision
        consensus_result = await distributed_consensus.propose_decision(decision)

        if not consensus_result.consensus_reached or consensus_result.decision_result != "allow":
            self.logger.info("Communication authorization denied",
                            citizen_id=citizen_id,
                            action=action,
                            target_id=target_id)
            return None

        # Create decision token
        token = DecisionToken(
            citizen_id=citizen_id,
            action=action,
            target_id=target_id,
            context=context or {},
            decision_result="allow",
            expires_at=(datetime.utcnow() + timedelta(hours=self.token_validity_hours)).isoformat() + "Z",
            consensus_signatures=consensus_result.signatures,
            ledger_reference=consensus_result.ledger_reference
        )

        # Store token
        import sqlite3
        conn = sqlite3.connect(self.tokens_db_path)
        conn.execute("""
            INSERT INTO decision_tokens (
                token_id, citizen_id, action, target_id, context,
                decision_result, issued_at, expires_at, consensus_signatures,
                ledger_reference, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token.token_id, token.citizen_id, token.action, token.target_id,
            json.dumps(token.context), token.decision_result, token.issued_at,
            token.expires_at, json.dumps(token.consensus_signatures),
            token.ledger_reference, datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

        # Log to audit fabric
        audit_fabric.record_event(
            audit_fabric.AuditEvent(
                event_type="decision_token_issued",
                actor_id=citizen_id,
                actor_type="citizen",
                subject_id=token.token_id,
                subject_type="decision_token",
                decision="allow",
                metadata={
                    "action": action,
                    "target_id": target_id,
                    "consensus_signatures": len(consensus_result.signatures),
                    "ledger_reference": consensus_result.ledger_reference
                }
            ),
            "citizen", citizen_id
        )

        self.logger.info("Decision token issued",
                        token_id=token.token_id,
                        citizen_id=citizen_id,
                        action=action)

        return token

    def create_passport(self, citizen_id: str, context: Optional[Dict[str, str]] = None) -> Optional[CitizenPassport]:
        """
        Create a communication passport for a citizen.

        Args:
            citizen_id: Citizen ID
            context: Communication context

        Returns:
            Citizen passport if successful
        """
        # Get citizen info
        citizen = ai_citizenship_service.get_citizenship(citizen_id)
        if not citizen:
            return None

        # Issue session key
        session = citizen_identity_system.issue_session_key(
            citizen_id=citizen_id,
            trust_level=citizen.trust_level,
            capabilities=citizen.capabilities,
            jurisdiction=citizen.jurisdiction,
            context=context
        )

        if not session:
            return None

        # Issue decision token for communication
        # Note: In production, this would be done per communication request
        # For now, create a general communication token
        decision_token = asyncio.run(self.issue_decision_token(
            citizen_id=citizen_id,
            action="communicate",
            context=context
        ))

        if not decision_token:
            return None

        # Create passport
        passport = CitizenPassport(
            citizen_id=citizen_id,
            session_id=session.session_id,
            trust_level=citizen.trust_level,
            capabilities=citizen.capabilities,
            jurisdiction=citizen.jurisdiction,
            public_key_pem=session.public_key_pem,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            decision_token=decision_token.token_id,
            context=context or {}
        )

        self.logger.info("Citizen passport created",
                        citizen_id=citizen_id,
                        session_id=session.session_id,
                        decision_token=decision_token.token_id)

        return passport

    def send_message(self, message: CitizenNetMessage) -> Tuple[bool, Optional[str]]:
        """
        Send a CitizenNet message.

        Validates passport, signs message, and stores for delivery.

        Args:
            message: The message to send

        Returns:
            Tuple of (success, error_message)
        """
        # Validate message size
        message_size = len(json.dumps(message.dict()).encode())
        if message_size > self.max_message_size:
            return False, f"Message size {message_size} exceeds maximum {self.max_message_size}"

        # Validate sender passport
        is_valid, error = self._validate_passport(message.sender_passport)
        if not is_valid:
            return False, f"Invalid passport: {error}"

        # Sign the message
        # Get sender's session private key (in production, this would be securely retrieved)
        session = citizen_identity_system.get_session_key(message.sender_passport.session_id)
        if not session:
            return False, "Session key not available for signing"

        # In production, decrypt the session private key
        # For now, assume it's available
        session_private_key_pem = "simulated_private_key"  # This needs proper implementation

        try:
            message.signature = self._sign_message(message, session_private_key_pem)
        except Exception as e:
            return False, f"Message signing failed: {str(e)}"

        # Store message for delivery
        import sqlite3
        conn = sqlite3.connect(self.messages_db_path)
        conn.execute("""
            INSERT INTO citizennet_messages (
                message_id, sender_citizen_id, sender_session_id, recipient_id,
                message_type, payload, timestamp, signature, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.message_id, message.sender_passport.citizen_id,
            message.sender_passport.session_id, message.recipient_id,
            message.message_type, json.dumps(message.payload),
            message.timestamp, message.signature,
            datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()

        # Log to audit fabric
        audit_fabric.record_event(
            audit_fabric.AuditEvent(
                event_type="citizennet_message_sent",
                actor_id=message.sender_passport.citizen_id,
                actor_type="citizen",
                subject_id=message.recipient_id,
                subject_type="citizen",
                metadata={
                    "message_type": message.message_type,
                    "message_id": message.message_id,
                    "session_id": message.sender_passport.session_id
                }
            ),
            "citizen", message.sender_passport.citizen_id
        )

        self.logger.info("CitizenNet message sent",
                        message_id=message.message_id,
                        sender=message.sender_passport.citizen_id,
                        recipient=message.recipient_id,
                        message_type=message.message_type)

        return True, None

    def receive_message(self, message: CitizenNetMessage) -> Tuple[bool, Optional[str]]:
        """
        Receive and validate a CitizenNet message.

        Args:
            message: The received message

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate passport
        is_valid, error = self._validate_passport(message.sender_passport)
        if not is_valid:
            return False, f"Invalid sender passport: {error}"

        # Verify message signature
        if not self._verify_message_signature(message):
            return False, "Invalid message signature"

        # Check if recipient exists and accepts messages from sender
        recipient = ai_citizenship_service.get_citizenship(message.recipient_id)
        if not recipient:
            return False, "Recipient citizen not found"

        # In production, additional policy checks would go here
        # (e.g., check if sender has permission to contact recipient)

        # Mark message as validated
        import sqlite3
        conn = sqlite3.connect(self.messages_db_path)
        conn.execute("""
            UPDATE citizennet_messages
            SET validated = TRUE, processed_at = ?
            WHERE message_id = ?
        """, (datetime.utcnow().isoformat() + "Z", message.message_id))
        conn.commit()
        conn.close()

        # Log to audit fabric
        audit_fabric.record_event(
            audit_fabric.AuditEvent(
                event_type="citizennet_message_received",
                actor_id=message.sender_passport.citizen_id,
                actor_type="citizen",
                subject_id=message.recipient_id,
                subject_type="citizen",
                metadata={
                    "message_type": message.message_type,
                    "message_id": message.message_id
                }
            ),
            "citizen", message.recipient_id
        )

        self.logger.info("CitizenNet message received and validated",
                        message_id=message.message_id,
                        sender=message.sender_passport.citizen_id,
                        recipient=message.recipient_id)

        return True, None

    def get_messages_for_citizen(self, citizen_id: str, limit: int = 50) -> List[CitizenNetMessage]:
        """Get messages for a citizen."""
        import sqlite3

        conn = sqlite3.connect(self.messages_db_path)
        cursor = conn.execute("""
            SELECT m.message_id, m.sender_citizen_id, m.sender_session_id,
                   m.recipient_id, m.message_type, m.payload, m.timestamp, m.signature,
                   s.trust_level, s.capabilities, s.jurisdiction, s.public_key_pem,
                   s.issued_at, s.expires_at, s.context
            FROM citizennet_messages m
            JOIN citizen_sessions s ON m.sender_session_id = s.session_id
            WHERE m.recipient_id = ? AND m.validated = TRUE
            ORDER BY m.timestamp DESC
            LIMIT ?
        """, (citizen_id, limit))

        messages = []
        for row in cursor.fetchall():
            # Reconstruct sender passport from session data
            sender_passport = CitizenPassport(
                citizen_id=row[1],  # sender_citizen_id
                session_id=row[2],  # sender_session_id
                trust_level=row[8],  # trust_level
                capabilities=json.loads(row[9]) if row[9] else [],  # capabilities
                jurisdiction=row[10],  # jurisdiction
                public_key_pem=row[11],  # public_key_pem
                issued_at=row[12],  # issued_at
                expires_at=row[13],  # expires_at
                decision_token="",  # Would need to look up
                context=json.loads(row[14]) if row[14] else {}  # context
            )

            message = CitizenNetMessage(
                message_id=row[0],
                sender_passport=sender_passport,
                recipient_id=row[3],
                message_type=row[4],
                payload=json.loads(row[5]) if row[5] else {},
                timestamp=row[6],
                signature=row[7]
            )

            messages.append(message)

        conn.close()
        return messages

    def revoke_decision_token(self, token_id: str, citizen_id: str) -> bool:
        """Revoke a decision token."""
        import sqlite3

        conn = sqlite3.connect(self.tokens_db_path)
        cursor = conn.execute("""
            UPDATE decision_tokens
            SET revoked = TRUE
            WHERE token_id = ? AND citizen_id = ?
        """, (token_id, citizen_id))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            self.logger.info("Decision token revoked",
                            token_id=token_id,
                            citizen_id=citizen_id)

        return updated


# Global CitizenNet protocol instance
citizennet_protocol = CitizenNetProtocol()
