"""
AI Citizenship Identity System
==============================

This module implements the AI citizenship identity system with cryptographic keys.
Each citizen has a long-term identity key for their citizenship, and short-lived
session keys bound to that identity and trust tier.

Architecture:
- Long-term identity keys: Permanent cryptographic identity for citizenship
- Session keys: Short-lived keys for specific operations/contexts
- Key hierarchy: Master identity key signs session keys
- Certificate integration: Keys bound to citizenship certificates
- Trust tier binding: Session keys include trust level and capabilities

This ensures "every decision and AI-to-AI message is signed by Seked (authorization)
and signed by the citizen (proof of origin)."
"""

import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from pydantic import BaseModel, Field
import structlog

from core.config import get_settings
from core.ai_citizenship.service import ai_citizenship_service
from core.mtls_infrastructure.service import mtls_infrastructure


class CitizenIdentityKey(BaseModel):
    """Long-term identity key for AI citizen."""
    citizen_id: str
    public_key_pem: str
    private_key_encrypted: str  # Encrypted with citizen-specific key
    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    algorithm: str = "RSA-2048"


class SessionKey(BaseModel):
    """Short-lived session key bound to citizen identity and trust tier."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    citizen_id: str
    trust_level: str
    capabilities: List[str]
    jurisdiction: str
    public_key_pem: str
    private_key_encrypted: str  # Encrypted with session-specific key
    issued_by_seked: str  # Seked signature of session parameters
    issued_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    expires_at: str
    signature: str  # Citizen's signature of session key
    context: Dict[str, str] = {}  # Use case, data class, etc.


class CitizenIdentitySystem:
    """AI citizenship identity management system."""

    def __init__(self):
        self.settings = get_settings()
        self.keys_path = os.path.join(self.settings.DATA_DIR, "citizen_keys")
        self.sessions_path = os.path.join(self.settings.DATA_DIR, "citizen_sessions")
        self.keys_db_path = os.path.join(self.keys_path, "identity_keys.db")
        self.sessions_db_path = os.path.join(self.sessions_path, "sessions.db")
        self.logger = structlog.get_logger(__name__)
        self._init_storage()

    def _init_storage(self) -> None:
        """Initialize key and session storage."""
        os.makedirs(self.keys_path, exist_ok=True)
        os.makedirs(self.sessions_path, exist_ok=True)

        # Initialize identity keys database
        if not os.path.exists(self.keys_db_path):
            self._init_keys_db()

        # Initialize sessions database
        if not os.path.exists(self.sessions_db_path):
            self._init_sessions_db()

        self.logger.info("Citizen identity storage initialized")

    def _init_keys_db(self) -> None:
        """Initialize identity keys database."""
        import sqlite3

        conn = sqlite3.connect(self.keys_db_path)
        conn.execute("""
            CREATE TABLE citizen_identity_keys (
                citizen_id TEXT PRIMARY KEY,
                public_key_pem TEXT NOT NULL,
                private_key_encrypted TEXT NOT NULL,
                key_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)
        conn.commit()
        conn.close()

    def _init_sessions_db(self) -> None:
        """Initialize sessions database."""
        import sqlite3

        conn = sqlite3.connect(self.sessions_db_path)
        conn.execute("""
            CREATE TABLE citizen_sessions (
                session_id TEXT PRIMARY KEY,
                citizen_id TEXT NOT NULL,
                trust_level TEXT NOT NULL,
                capabilities TEXT NOT NULL,  -- JSON array
                jurisdiction TEXT NOT NULL,
                public_key_pem TEXT NOT NULL,
                private_key_encrypted TEXT NOT NULL,
                issued_by_seked TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                signature TEXT NOT NULL,
                context TEXT NOT NULL,  -- JSON object
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                revocation_reason TEXT
            )
        """)

        # Create indexes for efficient lookups
        conn.execute("CREATE INDEX idx_sessions_citizen ON citizen_sessions(citizen_id)")
        conn.execute("CREATE INDEX idx_sessions_expires ON citizen_sessions(expires_at)")
        conn.commit()
        conn.close()

    def _generate_keypair(self) -> Tuple[rsa.RSAPrivateKey, str, str]:
        """Generate RSA keypair and return PEM strings."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        return private_key, public_key_pem, private_key_pem

    def _encrypt_private_key(self, private_key_pem: str, encryption_key: str) -> str:
        """Encrypt private key with provided key."""
        # Use HKDF to derive encryption key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"citizen_key_encryption",
            backend=default_backend()
        )
        key = hkdf.derive(encryption_key.encode())

        # Generate random IV
        iv = os.urandom(16)

        # Encrypt private key
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Pad the data to block size
        block_size = 16
        padding_length = block_size - (len(private_key_pem.encode()) % block_size)
        padded_data = private_key_pem.encode() + bytes([padding_length]) * padding_length

        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Return IV + encrypted data as base64
        import base64
        return base64.b64encode(iv + encrypted_data).decode()

    def _decrypt_private_key(self, encrypted_key_pem: str, decryption_key: str) -> str:
        """Decrypt private key with provided key."""
        import base64

        # Decode encrypted data
        encrypted_data = base64.b64decode(encrypted_key_pem)

        # Extract IV and encrypted key
        iv = encrypted_data[:16]
        encrypted_key = encrypted_data[16:]

        # Derive decryption key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"citizen_key_encryption",
            backend=default_backend()
        )
        key = hkdf.derive(decryption_key.encode())

        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        decrypted_padded = decryptor.update(encrypted_key) + decryptor.finalize()

        # Remove padding
        padding_length = decrypted_padded[-1]
        decrypted_data = decrypted_padded[:-padding_length]

        return decrypted_data.decode()

    def _sign_session_parameters(self, session_data: Dict, citizen_private_key: rsa.RSAPrivateKey) -> str:
        """Sign session parameters with citizen's private key."""
        # Create canonical representation
        canonical_data = json.dumps(session_data, sort_keys=True, separators=(',', ':'))

        # Sign with PSS padding
        signature = citizen_private_key.sign(
            canonical_data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        import base64
        return base64.b64encode(signature).decode()

    def _seked_sign_session(self, session_data: Dict) -> str:
        """Sign session with Seked's authority."""
        # In production, this would use Seked's governance cluster consensus
        # For now, use a simple HMAC with Seked secret
        canonical_data = json.dumps(session_data, sort_keys=True, separators=(',', ':'))

        import hmac
        from core.config import get_settings
        settings = get_settings()

        signature = hmac.new(
            settings.AI_CITIZENSHIP_SECRET.encode(),
            canonical_data.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def create_citizen_identity(self, citizen_id: str) -> CitizenIdentityKey:
        """
        Create long-term identity key for AI citizen.

        Args:
            citizen_id: Unique citizen identifier

        Returns:
            Citizen identity key
        """
        import sqlite3

        # Generate keypair
        private_key, public_key_pem, private_key_pem = self._generate_keypair()

        # Encrypt private key with citizen-specific key (derived from citizen_id + secret)
        encryption_key = f"{citizen_id}:{self.settings.AI_CITIZENSHIP_SECRET}"
        encrypted_private_key = self._encrypt_private_key(private_key_pem, encryption_key)

        # Create identity key object
        identity_key = CitizenIdentityKey(
            citizen_id=citizen_id,
            public_key_pem=public_key_pem,
            private_key_encrypted=encrypted_private_key
        )

        # Store in database
        conn = sqlite3.connect(self.keys_db_path)
        conn.execute("""
            INSERT INTO citizen_identity_keys (
                citizen_id, public_key_pem, private_key_encrypted,
                key_id, created_at, algorithm, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            identity_key.citizen_id, identity_key.public_key_pem,
            identity_key.private_key_encrypted, identity_key.key_id,
            identity_key.created_at, identity_key.algorithm, True
        ))
        conn.commit()
        conn.close()

        self.logger.info("Citizen identity key created",
                        citizen_id=citizen_id,
                        key_id=identity_key.key_id)

        return identity_key

    def get_citizen_identity(self, citizen_id: str) -> Optional[CitizenIdentityKey]:
        """Get citizen's identity key."""
        import sqlite3

        conn = sqlite3.connect(self.keys_db_path)
        cursor = conn.execute("""
            SELECT citizen_id, public_key_pem, private_key_encrypted,
                   key_id, created_at, algorithm
            FROM citizen_identity_keys
            WHERE citizen_id = ? AND active = TRUE
        """, (citizen_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return CitizenIdentityKey(
                citizen_id=row[0],
                public_key_pem=row[1],
                private_key_encrypted=row[2],
                key_id=row[3],
                created_at=row[4],
                algorithm=row[5]
            )
        return None

    def issue_session_key(self, citizen_id: str, trust_level: str,
                         capabilities: List[str], jurisdiction: str,
                         context: Dict[str, str] = None, validity_hours: int = 24) -> Optional[SessionKey]:
        """
        Issue a session key bound to citizen identity and trust tier.

        Args:
            citizen_id: Citizen identifier
            trust_level: Trust level for session
            capabilities: Capabilities granted in session
            jurisdiction: Legal jurisdiction
            context: Session context (use case, data class, etc.)
            validity_hours: Session validity in hours

        Returns:
            Session key if successful
        """
        import sqlite3

        # Verify citizen exists and has valid citizenship
        citizen = ai_citizenship_service.get_citizenship(citizen_id)
        if not citizen:
            self.logger.error("Citizen not found", citizen_id=citizen_id)
            return None

        # Verify trust level matches citizenship
        if citizen.trust_level != trust_level:
            self.logger.error("Trust level mismatch",
                            citizen_trust=citizen.trust_level,
                            requested_trust=trust_level)
            return None

        # Get citizen identity key
        identity_key = self.get_citizen_identity(citizen_id)
        if not identity_key:
            self.logger.error("Citizen identity key not found", citizen_id=citizen_id)
            return None

        # Generate session keypair
        session_private_key, session_public_key_pem, session_private_key_pem = self._generate_keypair()

        # Encrypt session private key
        session_encryption_key = f"{citizen_id}:{uuid.uuid4()}:{self.settings.AI_CITIZENSHIP_SECRET}"
        encrypted_session_private_key = self._encrypt_private_key(session_private_key_pem, session_encryption_key)

        # Calculate expiration
        expires_at = (datetime.utcnow() + timedelta(hours=validity_hours)).isoformat() + "Z"

        # Prepare session data for signing
        session_data = {
            "session_id": "",  # Will be set after creation
            "citizen_id": citizen_id,
            "trust_level": trust_level,
            "capabilities": sorted(capabilities),  # Sort for canonical representation
            "jurisdiction": jurisdiction,
            "issued_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at,
            "context": context or {}
        }

        # Get Seked authorization signature
        seked_signature = self._seked_sign_session(session_data)

        # Create session key object (without signature yet)
        session_key = SessionKey(
            citizen_id=citizen_id,
            trust_level=trust_level,
            capabilities=capabilities,
            jurisdiction=jurisdiction,
            public_key_pem=session_public_key_pem,
            private_key_encrypted=encrypted_session_private_key,
            issued_by_seked=seked_signature,
            expires_at=expires_at,
            context=context or {}
        )

        # Add session_id to data and sign with citizen's identity key
        session_data["session_id"] = session_key.session_id

        # Decrypt citizen's private key for signing
        citizen_private_key_pem = self._decrypt_private_key(
            identity_key.private_key_encrypted,
            f"{citizen_id}:{self.settings.AI_CITIZENSHIP_SECRET}"
        )

        citizen_private_key = serialization.load_pem_private_key(
            citizen_private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )

        citizen_signature = self._sign_session_parameters(session_data, citizen_private_key)
        session_key.signature = citizen_signature

        # Store session in database
        conn = sqlite3.connect(self.sessions_db_path)
        conn.execute("""
            INSERT INTO citizen_sessions (
                session_id, citizen_id, trust_level, capabilities, jurisdiction,
                public_key_pem, private_key_encrypted, issued_by_seked,
                issued_at, expires_at, signature, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_key.session_id, session_key.citizen_id, session_key.trust_level,
            json.dumps(session_key.capabilities), session_key.jurisdiction,
            session_key.public_key_pem, session_key.private_key_encrypted,
            session_key.issued_by_seked, session_key.issued_at,
            session_key.expires_at, session_key.signature,
            json.dumps(session_key.context)
        ))
        conn.commit()
        conn.close()

        self.logger.info("Session key issued",
                        session_id=session_key.session_id,
                        citizen_id=citizen_id,
                        trust_level=trust_level,
                        expires_at=expires_at)

        return session_key

    def get_session_key(self, session_id: str) -> Optional[SessionKey]:
        """Get session key by ID."""
        import sqlite3

        conn = sqlite3.connect(self.sessions_db_path)
        cursor = conn.execute("""
            SELECT session_id, citizen_id, trust_level, capabilities, jurisdiction,
                   public_key_pem, private_key_encrypted, issued_by_seked,
                   issued_at, expires_at, signature, context, revoked
            FROM citizen_sessions
            WHERE session_id = ? AND revoked = FALSE
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            # Check expiration
            expires_at = datetime.fromisoformat(row[9].replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                return None

            return SessionKey(
                session_id=row[0],
                citizen_id=row[1],
                trust_level=row[2],
                capabilities=json.loads(row[3]),
                jurisdiction=row[4],
                public_key_pem=row[5],
                private_key_encrypted=row[6],
                issued_by_seked=row[7],
                issued_at=row[8],
                expires_at=row[9],
                signature=row[10],
                context=json.loads(row[11]) if row[11] else {}
            )
        return None

    def revoke_session_key(self, session_id: str, reason: str = "administrative") -> bool:
        """Revoke a session key."""
        import sqlite3

        conn = sqlite3.connect(self.sessions_db_path)
        cursor = conn.execute("""
            UPDATE citizen_sessions
            SET revoked = TRUE, revocation_reason = ?
            WHERE session_id = ? AND revoked = FALSE
        """, (reason, session_id))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if updated:
            self.logger.info("Session key revoked", session_id=session_id, reason=reason)

        return updated

    def verify_session_signature(self, session: SessionKey) -> bool:
        """
        Verify that session key is properly signed by both Seked and citizen.

        Args:
            session: Session key to verify

        Returns:
            True if signatures are valid
        """
        try:
            # Verify Seked signature
            session_data = {
                "session_id": session.session_id,
                "citizen_id": session.citizen_id,
                "trust_level": session.trust_level,
                "capabilities": sorted(session.capabilities),
                "jurisdiction": session.jurisdiction,
                "issued_at": session.issued_at,
                "expires_at": session.expires_at,
                "context": session.context
            }

            expected_seked_signature = self._seked_sign_session(session_data)
            if not hmac.compare_digest(session.issued_by_seked, expected_seked_signature):
                return False

            # Verify citizen signature
            identity_key = self.get_citizen_identity(session.citizen_id)
            if not identity_key:
                return False

            # Load citizen's public key
            public_key = serialization.load_pem_public_key(
                identity_key.public_key_pem.encode(),
                backend=default_backend()
            )

            # Verify signature
            import base64
            signature_bytes = base64.b64decode(session.signature)

            canonical_data = json.dumps(session_data, sort_keys=True, separators=(',', ':'))

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
            self.logger.error("Session signature verification failed",
                            session_id=session.session_id,
                            error=str(e))
            return False

    def get_active_sessions(self, citizen_id: str) -> List[SessionKey]:
        """Get all active sessions for a citizen."""
        import sqlite3

        conn = sqlite3.connect(self.sessions_db_path)
        cursor = conn.execute("""
            SELECT session_id, citizen_id, trust_level, capabilities, jurisdiction,
                   public_key_pem, private_key_encrypted, issued_by_seked,
                   issued_at, expires_at, signature, context
            FROM citizen_sessions
            WHERE citizen_id = ? AND revoked = FALSE
            AND datetime(expires_at) > datetime('now')
            ORDER BY issued_at DESC
        """, (citizen_id,))

        sessions = []
        for row in cursor.fetchall():
            sessions.append(SessionKey(
                session_id=row[0],
                citizen_id=row[1],
                trust_level=row[2],
                capabilities=json.loads(row[3]),
                jurisdiction=row[4],
                public_key_pem=row[5],
                private_key_encrypted=row[6],
                issued_by_seked=row[7],
                issued_at=row[8],
                expires_at=row[9],
                signature=row[10],
                context=json.loads(row[11]) if row[11] else {}
            ))

        conn.close()
        return sessions

    def rotate_identity_key(self, citizen_id: str) -> Optional[CitizenIdentityKey]:
        """
        Rotate a citizen's identity key (creates new key, keeps old for verification).

        Args:
            citizen_id: Citizen identifier

        Returns:
            New identity key
        """
        import sqlite3

        # Deactivate old key
        conn = sqlite3.connect(self.keys_db_path)
        conn.execute("""
            UPDATE citizen_identity_keys
            SET active = FALSE
            WHERE citizen_id = ? AND active = TRUE
        """, (citizen_id,))
        conn.commit()
        conn.close()

        # Create new identity key
        new_key = self.create_citizen_identity(citizen_id)

        self.logger.info("Identity key rotated",
                        citizen_id=citizen_id,
                        old_key_id="rotated",
                        new_key_id=new_key.key_id)

        return new_key


# Global citizen identity system instance
citizen_identity_system = CitizenIdentitySystem()
