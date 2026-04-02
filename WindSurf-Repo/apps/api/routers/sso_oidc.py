"""OIDC SSO endpoints (authorization code flow).

This is a baseline implementation intended for Okta/AzureAD/Google.
"""

from __future__ import annotations

import secrets
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from core.config import get_settings
from core.security import create_access_token

# from core.sso.oidc_state import sign_state, verify_state
from db.session import get_db

# from db.session import tenant_enforcement_disabled
# from db.models import Organization, OrganizationSSOProvider, SSOProviderType, User, UserIdentity

settings = get_settings()

router = APIRouter(prefix="/sso/oidc", tags=["sso"])


async def _discovery(issuer: str) -> dict[str, Any]:
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def _jwks(jwks_uri: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(jwks_uri)
        r.raise_for_status()
        return r.json()


def _find_key(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return k
    return None


@router.get("/{org_slug}/{provider_name}/start")
async def oidc_start(
    org_slug: str,
    provider_name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    with tenant_enforcement_disabled():
        org = (
            db.query(Organization)
            .filter(Organization.slug == org_slug, Organization.is_active == True)
            .first()
        )
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        provider = (
            db.query(OrganizationSSOProvider)
            .filter(
                OrganizationSSOProvider.organization_id == org.id,
                OrganizationSSOProvider.name == provider_name,
                OrganizationSSOProvider.provider_type == SSOProviderType.OIDC,
                OrganizationSSOProvider.is_active == True,
            )
            .first()
        )
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not configured")

    if not provider.oidc_issuer_url or not provider.oidc_client_id:
        raise HTTPException(status_code=400, detail="OIDC provider missing issuer/client_id")

    # nonce = secrets.token_urlsafe(16)
    # state = sign_state({"org_id": org.id, "provider_id": provider.id, "nonce": nonce})

    disc = await _discovery(provider.oidc_issuer_url)
    auth_endpoint = disc.get("authorization_endpoint")
    if not auth_endpoint:
        raise HTTPException(status_code=400, detail="OIDC discovery missing authorization_endpoint")

    redirect_uri = str(
        request.url_for("oidc_callback", org_slug=org_slug, provider_name=provider_name)
    )

    params = {
        "client_id": provider.oidc_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        # "state": state,
        # "nonce": nonce,
    }
    return RedirectResponse(url=str(httpx.URL(auth_endpoint, params=params)))


@router.get("/{org_slug}/{provider_name}/callback", name="oidc_callback")
async def oidc_callback(
    org_slug: str,
    provider_name: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # TODO: implement OIDC state handling
    raise HTTPException(status_code=501, detail="OIDC not implemented")

    with tenant_enforcement_disabled():
        org = (
            db.query(Organization)
            .filter(Organization.slug == org_slug, Organization.is_active == True)
            .first()
        )
        if not org or org.id != st.get("org_id"):
            raise HTTPException(status_code=400, detail="Invalid org")

        provider = (
            db.query(OrganizationSSOProvider)
            .filter(
                OrganizationSSOProvider.id == st.get("provider_id"),
                OrganizationSSOProvider.organization_id == org.id,
                OrganizationSSOProvider.name == provider_name,
                OrganizationSSOProvider.provider_type == SSOProviderType.OIDC,
                OrganizationSSOProvider.is_active == True,
            )
            .first()
        )
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not configured")

    if not provider.oidc_client_secret:
        raise HTTPException(status_code=400, detail="OIDC provider missing client_secret")

    disc = await _discovery(provider.oidc_issuer_url)
    token_endpoint = disc.get("token_endpoint")
    jwks_uri = disc.get("jwks_uri")
    if not token_endpoint or not jwks_uri:
        raise HTTPException(status_code=400, detail="OIDC discovery missing endpoints")

    redirect_uri = str(
        request.url_for("oidc_callback", org_slug=org_slug, provider_name=provider_name)
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider.oidc_client_id,
                "client_secret": provider.oidc_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail="Token exchange failed")
        token_json = token_resp.json()

    id_token = token_json.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="Missing id_token")

    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    jwks = await _jwks(jwks_uri)
    key = _find_key(jwks, kid) if kid else None
    if not key:
        raise HTTPException(status_code=400, detail="Unable to find JWKS key")

    claims = jwt.decode(
        id_token,
        key,
        algorithms=[header.get("alg") or "RS256"],
        audience=provider.oidc_client_id,
        issuer=provider.oidc_issuer_url,
        options={"verify_at_hash": False},
    )

    subject = claims.get("sub")
    email = claims.get("email")
    if not subject:
        raise HTTPException(status_code=400, detail="Missing subject")

    with tenant_enforcement_disabled():
        ident = (
            db.query(UserIdentity)
            .filter(
                UserIdentity.sso_provider_id == provider.id,
                UserIdentity.provider_subject == subject,
                UserIdentity.is_active == True,
            )
            .first()
        )

        user: User | None = None
        if ident:
            user = db.query(User).filter(User.id == ident.user_id, User.is_active == True).first()
        elif email:
            user = db.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not provisioned")

        if not ident:
            ident = UserIdentity(
                organization_id=org.id,
                user_id=user.id,
                sso_provider_id=provider.id,
                provider_subject=subject,
                email=email,
                is_active=True,
            )
            db.add(ident)
            db.commit()

    access_token = create_access_token(
        data={
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "workspace_id": user.workspace_id,
            "organization_id": user.organization_id,
            "is_superuser": user.is_superuser,
        }
    )

    # For now, redirect back to root with token in fragment (frontend can capture).
    return RedirectResponse(url=f"/static/index.html#access_token={access_token}")
