"""
AI Citizenship API Router
=========================

FastAPI router for AI Citizenship Service endpoints.

This router provides REST API endpoints for:
- Managing user credits and tokens
- Creating and retrieving AI citizenships
- Certificate validation and verification
- Governance integration with control plane
"""

import hmac
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# import structlog  # Temporarily commented out for startup

from core.ai_citizenship.service import (
    ai_citizenship_service,
    AICitizenshipRequest,
    AICitizenshipCertificate,
    UserCredits
)
from core.auth.dependencies import get_current_user_token
from core.control_plane.engine import control_plane_engine

router = APIRouter(prefix="/api/v1/ai-citizenship", tags=["AI Citizenship"])
security = HTTPBearer()
logger = None  # structlog.get_logger(__name__)  # Temporarily commented out for startup


@router.post("/users", response_model=UserCredits, summary="Create or update user with credits")
async def create_user(
    token: str,
    credits: int,
    current_user: str = Depends(get_current_user_token)
) -> UserCredits:
    """
    Create or update a user with credits.

    **Note:** This endpoint should be protected in production deployments.
    Currently allows any authenticated user to create tokens for testing.

    Args:
        token: The user token to create/update
        credits: Number of credits to assign

    Returns:
        UserCredits: The created/updated user information
    """
    try:
        user = ai_citizenship_service.add_user(token, credits)
        logger.info("User created via API", token=token, credits=credits, by_user=current_user)
        return user
    except Exception as e:
        logger.error("Failed to create user", error=str(e), token=token)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/users/{token}", response_model=UserCredits, summary="Get user credit balance")
async def get_user_credits(
    token: str,
    current_user: str = Depends(get_current_user_token)
) -> UserCredits:
    """
    Retrieve user credit balance.

    Args:
        token: The user token to query

    Returns:
        UserCredits: User credit information
    """
    user = ai_citizenship_service.get_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/citizenships", response_model=AICitizenshipCertificate, summary="Create AI citizenship")
async def create_citizenship(
    request: AICitizenshipRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AICitizenshipCertificate:
    """
    Create a new AI citizenship certificate.

    Requires valid user token with sufficient credits.
    Deducts 1 credit per citizenship creation.

    Args:
        request: Citizenship creation request with AI details

    Returns:
        AICitizenshipCertificate: The created citizenship certificate with signature
    """
    token = credentials.credentials

    try:
        # Validate user exists
        user = ai_citizenship_service.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unknown token"
            )

        # Create citizenship
        certificate = ai_citizenship_service.create_citizenship(request, token)

        # Log to control plane for governance
        await control_plane_engine.log_governance_event(
            event_type="ai_citizenship_created",
            details={
                "citizenship_id": certificate.citizenship_id,
                "model_type": certificate.model_type,
                "trust_level": certificate.trust_level,
                "owner_entity": certificate.owner_entity,
                "jurisdiction": certificate.jurisdiction
            },
            severity="info"
        )

        logger.info("Citizenship created via API",
                   citizenship_id=certificate.citizenship_id,
                   token=token,
                   model_type=request.model_type)

        return certificate

    except ValueError as e:
        if "Unknown token" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        elif "Insufficient credits" in str(e):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error("Failed to create citizenship", error=str(e), token=token)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create citizenship"
        )


@router.get("/citizenships/{citizenship_id}", response_model=AICitizenshipCertificate, summary="Get citizenship by ID")
async def get_citizenship(
    citizenship_id: str,
    current_user: str = Depends(get_current_user_token)
) -> AICitizenshipCertificate:
    """
    Retrieve an AI citizenship certificate by ID.

    Args:
        citizenship_id: The unique citizenship identifier

    Returns:
        AICitizenshipCertificate: The citizenship certificate
    """
    certificate = ai_citizenship_service.get_citizenship(citizenship_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizenship not found"
        )
    return certificate


@router.get("/citizenships", response_model=List[AICitizenshipCertificate], summary="List citizenships")
async def list_citizenships(
    owner_token: Optional[str] = None,
    limit: int = 50,
    current_user: str = Depends(get_current_user_token)
) -> List[AICitizenshipCertificate]:
    """
    List AI citizenships, optionally filtered by owner.

    Args:
        owner_token: Optional filter by owner token
        limit: Maximum number of results (default: 50)

    Returns:
        List[AICitizenshipCertificate]: List of citizenship certificates
    """
    try:
        citizenships = ai_citizenship_service.list_citizenships(owner_token, limit)
        return citizenships
    except Exception as e:
        logger.error("Failed to list citizenships", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list citizenships"
        )


@router.delete("/citizenships/{citizenship_id}", summary="Revoke citizenship")
async def revoke_citizenship(
    citizenship_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: str = Depends(get_current_user_token)
) -> dict:
    """
    Revoke an AI citizenship certificate.

    Only the owner can revoke their citizenship.

    Args:
        citizenship_id: The citizenship ID to revoke

    Returns:
        dict: Success confirmation
    """
    token = credentials.credentials

    try:
        success = ai_citizenship_service.revoke_citizenship(citizenship_id, token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Citizenship not found or not owned by this token"
            )

        # Log to control plane
        await control_plane_engine.log_governance_event(
            event_type="ai_citizenship_revoked",
            details={"citizenship_id": citizenship_id},
            severity="warning"
        )

        logger.info("Citizenship revoked via API", citizenship_id=citizenship_id, token=token)
        return {"message": "Citizenship revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to revoke citizenship", error=str(e), citizenship_id=citizenship_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke citizenship"
        )


@router.post("/citizenships/{citizenship_id}/verify", summary="Verify citizenship signature")
async def verify_citizenship(
    citizenship_id: str,
    current_user: str = Depends(get_current_user_token)
) -> dict:
    """
    Verify the cryptographic signature of a citizenship certificate.

    Args:
        citizenship_id: The citizenship ID to verify

    Returns:
        dict: Verification result
    """
    certificate = ai_citizenship_service.get_citizenship(citizenship_id)
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizenship not found"
        )

    # Reconstruct the payload and verify signature
    certificate_data = {
        "citizenshipId": certificate.citizenship_id,
        "modelType": certificate.model_type,
        "ownerEntity": certificate.owner_entity,
        "jurisdiction": certificate.jurisdiction,
        "capabilities": certificate.capabilities,
        "trustLevel": certificate.trust_level,
        "liabilityHolder": certificate.liability_holder,
        "issuedAt": certificate.issued_at,
    }

    expected_payload = json.dumps(certificate_data, sort_keys=True)
    expected_signature = ai_citizenship_service._generate_signature(expected_payload)

    is_valid = hmac.compare_digest(certificate.signature, expected_signature)

    return {
        "citizenship_id": citizenship_id,
        "signature_valid": is_valid,
        "verified_at": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/health", summary="AI Citizenship service health check")
async def health_check() -> dict:
    """
    Health check endpoint for the AI Citizenship service.

    Returns:
        dict: Service health status
    """
    return {
        "service": "AI Citizenship Service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
