"""Workspace-scoped secrets (BYOK) utilities."""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.security.encryption import encrypt_field, decrypt_field
from db.models.workspace_secret import WorkspaceSecret


class WorkspaceSecretsService:
    """Read/write encrypted secrets for a workspace."""

    def set_secret(
        self,
        db: Session,
        workspace_id: str,
        provider: str,
        secret_name: str,
        value: str,
        is_active: bool = True,
    ) -> WorkspaceSecret:
        encrypted_value = encrypt_field(value)
        secret = (
            db.query(WorkspaceSecret)
            .filter(
                WorkspaceSecret.workspace_id == workspace_id,
                WorkspaceSecret.provider == provider,
                WorkspaceSecret.secret_name == secret_name,
            )
            .first()
        )

        if not secret:
            secret = WorkspaceSecret(
                workspace_id=workspace_id,
                provider=provider,
                secret_name=secret_name,
                encrypted_value=encrypted_value,
                is_active=is_active,
            )
            db.add(secret)
        else:
            secret.encrypted_value = encrypted_value
            secret.is_active = is_active

        db.commit()
        db.refresh(secret)
        return secret

    def get_secret(
        self,
        db: Session,
        workspace_id: str,
        provider: str,
        secret_name: str,
    ) -> str | None:
        secret = (
            db.query(WorkspaceSecret)
            .filter(
                WorkspaceSecret.workspace_id == workspace_id,
                WorkspaceSecret.provider == provider,
                WorkspaceSecret.secret_name == secret_name,
                WorkspaceSecret.is_active == True,
            )
            .first()
        )
        if not secret:
            return None
        return decrypt_field(secret.encrypted_value)

    def delete_secret(
        self,
        db: Session,
        workspace_id: str,
        provider: str,
        secret_name: str,
    ) -> bool:
        secret = (
            db.query(WorkspaceSecret)
            .filter(
                WorkspaceSecret.workspace_id == workspace_id,
                WorkspaceSecret.provider == provider,
                WorkspaceSecret.secret_name == secret_name,
            )
            .first()
        )
        if not secret:
            return False
        db.delete(secret)
        db.commit()
        return True


_workspace_secrets_service = WorkspaceSecretsService()


def get_workspace_secrets_service() -> WorkspaceSecretsService:
    return _workspace_secrets_service
