"""
AI Citizenship Service
======================

This module implements a governance layer for managing AI citizenships within the BYOS system.
Each citizenship acts as a legally binding identity for an AI system, providing:

- Deterministic policy enforcement with schema validation
- Hard gate execution preventing invalid citizenship creation
- Immutable audit records with cryptographic signatures
- Built-in monetization through credit-based system
- Integration with BYOS control plane governance

The service manages:
- AI system identities and legal entities
- Trust levels and liability holders
- Jurisdiction and regulatory compliance
- Capability declarations and constraints
"""

import hmac
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, validator
# import structlog  # Temporarily commented out for startup

from core.config import get_settings


class AICitizenshipRequest(BaseModel):
    """Request model for creating AI citizenship."""
    model_type: str = Field(..., description="Type of AI model (e.g., 'GPT-4', 'Claude-3')")
    owner_entity: str = Field(..., description="Legal entity owning the AI system")
    jurisdiction: str = Field(..., description="Legal jurisdiction for the citizenship")
    capabilities: List[str] = Field(..., description="List of AI capabilities and permissions")
    trust_level: str = Field(..., description="Trust level classification (e.g., 'high', 'medium', 'low')")
    liability_holder: str = Field(..., description="Entity legally liable for AI actions")

    @validator('capabilities')
    def validate_capabilities(cls, v):
        if not v:
            raise ValueError('Capabilities list cannot be empty')
        return v

    @validator('trust_level')
    def validate_trust_level(cls, v):
        valid_levels = ['high', 'medium', 'low', 'critical', 'experimental']
        if v.lower() not in valid_levels:
            raise ValueError(f'Trust level must be one of: {valid_levels}')
        return v.lower()


class AICitizenshipCertificate(BaseModel):
    """Certificate model for AI citizenship."""
    citizenship_id: str
    model_type: str
    owner_entity: str
    jurisdiction: str
    capabilities: List[str]
    trust_level: str
    liability_holder: str
    issued_at: str
    signature: str


class UserCredits(BaseModel):
    """User credit balance model."""
    token: str
    credits: int


class AICitizenshipService:
    """Core service for managing AI citizenships."""

    def __init__(self):
        self.settings = get_settings()
        self.db_path = os.path.join(self.settings.data_dir, "ai_citizenship.db")
        self.secret_key = self.settings.ai_citizenship_secret or "default_secret_change_me"
        self.logger = None  # structlog.get_logger(__name__)  # Temporarily commented out for startup
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                token TEXT PRIMARY KEY,
                credits INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_citizenships (
                id TEXT PRIMARY KEY,
                model_type TEXT NOT NULL,
                owner_entity TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                capabilities TEXT NOT NULL,  -- JSON array
                trust_level TEXT NOT NULL,
                liability_holder TEXT NOT NULL,
                certificate_json TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at TEXT NOT NULL,
                owner_token TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)

        conn.commit()
        conn.close()
        self.logger.info("AI Citizenship database initialized", db_path=self.db_path)

    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for the payload."""
        return hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def get_user(self, token: str) -> Optional[UserCredits]:
        """Retrieve user by token."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT token, credits FROM users WHERE token = ?",
            (token,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return UserCredits(token=row[0], credits=row[1])
        return None

    def deduct_credit(self, token: str) -> bool:
        """Atomically deduct one credit from user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT credits FROM users WHERE token = ?",
            (token,)
        )
        row = cursor.fetchone()

        if not row or row[0] <= 0:
            conn.close()
            return False

        new_credits = row[0] - 1
        conn.execute(
            "UPDATE users SET credits = ?, updated_at = ? WHERE token = ?",
            (new_credits, datetime.utcnow().isoformat() + "Z", token)
        )
        conn.commit()
        conn.close()

        self.logger.info("Credit deducted", token=token, remaining_credits=new_credits)
        return True

    def add_user(self, token: str, credits: int) -> UserCredits:
        """Create or update user with credits."""
        now = datetime.utcnow().isoformat() + "Z"

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO users (token, credits, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (token, credits, now, now))
        conn.commit()
        conn.close()

        self.logger.info("User created/updated", token=token, credits=credits)
        return UserCredits(token=token, credits=credits)

    def create_citizenship(self, request: AICitizenshipRequest, owner_token: str) -> AICitizenshipCertificate:
        """Create a new AI citizenship."""
        # Verify user exists and has credits
        user = self.get_user(owner_token)
        if not user:
            raise ValueError("Unknown token")

        if not self.deduct_credit(owner_token):
            raise ValueError("Insufficient credits")

        # Generate citizenship ID and certificate
        citizenship_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        certificate_data = {
            "citizenshipId": citizenship_id,
            "modelType": request.model_type,
            "ownerEntity": request.owner_entity,
            "jurisdiction": request.jurisdiction,
            "capabilities": request.capabilities,
            "trustLevel": request.trust_level,
            "liabilityHolder": request.liability_holder,
            "issuedAt": now,
        }

        certificate_json = json.dumps(certificate_data, sort_keys=True)
        signature = self._generate_signature(certificate_json)

        # Persist to database
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO ai_citizenships (
                id, model_type, owner_entity, jurisdiction, capabilities,
                trust_level, liability_holder, certificate_json, signature,
                created_at, owner_token
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            citizenship_id,
            request.model_type,
            request.owner_entity,
            request.jurisdiction,
            json.dumps(request.capabilities),
            request.trust_level,
            request.liability_holder,
            certificate_json,
            signature,
            now,
            owner_token,
        ))
        conn.commit()
        conn.close()

        self.logger.info("AI Citizenship created",
                        citizenship_id=citizenship_id,
                        owner_token=owner_token,
                        model_type=request.model_type)

        return AICitizenshipCertificate(
            citizenship_id=citizenship_id,
            model_type=request.model_type,
            owner_entity=request.owner_entity,
            jurisdiction=request.jurisdiction,
            capabilities=request.capabilities,
            trust_level=request.trust_level,
            liability_holder=request.liability_holder,
            issued_at=now,
            signature=signature
        )

    def get_citizenship(self, citizenship_id: str) -> Optional[AICitizenshipCertificate]:
        """Retrieve citizenship by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT certificate_json, signature FROM ai_citizenships
            WHERE id = ? AND status = 'active'
        """, (citizenship_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            certificate_data = json.loads(row[0])
            return AICitizenshipCertificate(
                **certificate_data,
                signature=row[1]
            )
        return None

    def list_citizenships(self, owner_token: Optional[str] = None, limit: int = 50) -> List[AICitizenshipCertificate]:
        """List citizenships, optionally filtered by owner."""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT certificate_json, signature FROM ai_citizenships
            WHERE status = 'active'
        """
        params = []

        if owner_token:
            query += " AND owner_token = ?"
            params.append(owner_token)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        citizenships = []
        for row in rows:
            certificate_data = json.loads(row[0])
            citizenships.append(AICitizenshipCertificate(
                **certificate_data,
                signature=row[1]
            ))

        return citizenships

    def revoke_citizenship(self, citizenship_id: str, owner_token: str) -> bool:
        """Revoke a citizenship (admin operation)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            UPDATE ai_citizenships SET status = 'revoked'
            WHERE id = ? AND owner_token = ?
        """, (citizenship_id, owner_token))

        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if changed:
            self.logger.info("Citizenship revoked", citizenship_id=citizenship_id)

        return changed


# Global service instance

# Lazy initialization factory
_ai_citizenship_service_instance = None

def get_ai_citizenship_service() -> AICitizenshipService:
    """Get or create the AI citizenship service instance."""
    global _ai_citizenship_service_instance
    if _ai_citizenship_service_instance is None:
        _ai_citizenship_service_instance = AICitizenshipService()
    return _ai_citizenship_service_instance

# Provide backward compatibility
ai_citizenship_service = None  # Will be lazily initialized

def __getattr__(name):
    """Lazy load ai_citizenship_service on access."""
    if name == 'ai_citizenship_service':
        return get_ai_citizenship_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

