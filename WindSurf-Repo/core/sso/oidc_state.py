"""OIDC state management for secure authentication flows."""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from core.config import settings


class OIDCStateError(Exception):
    """OIDC state management error."""
    pass


def _serialize_state(state_data: Dict) -> str:
    """Serialize state data to base64-encoded JSON."""
    json_str = json.dumps(state_data, separators=(',', ':'), sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode()).decode().rstrip('=')


def _deserialize_state(state_str: str) -> Dict:
    """Deserialize base64-encoded JSON state data."""
    # Add padding if needed
    padding = '=' * (-len(state_str) % 4)
    try:
        json_str = base64.urlsafe_b64decode(state_str + padding).decode()
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        raise OIDCStateError(f"Invalid state format: {e}")


def _sign_state(state_data: str) -> str:
    """Create HMAC signature for state data."""
    secret = settings.secret_key.encode()
    return hmac.new(secret, state_data.encode(), hashlib.sha256).hexdigest()


def sign_state(state_data: Dict) -> str:
    """Create a signed OIDC state token.
    
    Args:
        state_data: Dictionary containing state information
        
    Returns:
        Signed state token (state.signature)
    """
    # Add timestamp to prevent replay attacks
    state_data['ts'] = datetime.utcnow().isoformat()
    state_data['rnd'] = secrets.token_hex(16)  # Random nonce
    
    serialized = _serialize_state(state_data)
    signature = _sign_state(serialized)
    
    return f"{serialized}.{signature}"


def verify_state(state_token: str, max_age_minutes: int = 15) -> Dict:
    """Verify and decode a signed OIDC state token.
    
    Args:
        state_token: Signed state token (state.signature)
        max_age_minutes: Maximum age of state token in minutes
        
    Returns:
        Decoded state data
        
    Raises:
        OIDCStateError: If state is invalid or expired
    """
    try:
        serialized, signature = state_token.rsplit('.', 1)
    except ValueError:
        raise OIDCStateError("Invalid state format")
    
    # Verify signature
    expected_signature = _sign_state(serialized)
    if not hmac.compare_digest(signature, expected_signature):
        raise OIDCStateError("Invalid state signature")
    
    # Decode state data
    state_data = _deserialize_state(serialized)
    
    # Check timestamp
    try:
        timestamp = datetime.fromisoformat(state_data['ts'])
        if datetime.utcnow() - timestamp > timedelta(minutes=max_age_minutes):
            raise OIDCStateError("State token expired")
    except (KeyError, ValueError):
        raise OIDCStateError("Invalid or missing timestamp")
    
    # Remove internal fields
    state_data.pop('ts', None)
    state_data.pop('rnd', None)
    
    return state_data


def create_auth_state(
    redirect_uri: str,
    workspace_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Create an authentication state token.
    
    Args:
        redirect_uri: URI to redirect to after authentication
        workspace_id: Optional workspace ID for context
        provider_id: Optional SSO provider ID
        **kwargs: Additional state data
        
    Returns:
        Signed state token
    """
    state_data = {
        'redirect_uri': redirect_uri,
        'workspace_id': workspace_id,
        'provider_id': provider_id,
        **kwargs
    }
    
    return sign_state(state_data)


def create_link_state(
    user_id: str,
    workspace_id: str,
    provider_id: str,
    **kwargs,
) -> str:
    """Create a state token for account linking.
    
    Args:
        user_id: User ID to link
        workspace_id: Workspace ID context
        provider_id: SSO provider ID
        **kwargs: Additional state data
        
    Returns:
        Signed state token
    """
    state_data = {
        'action': 'link',
        'user_id': user_id,
        'workspace_id': workspace_id,
        'provider_id': provider_id,
        **kwargs
    }
    
    return sign_state(state_data)


def create_invite_state(
    invite_token: str,
    workspace_id: str,
    **kwargs,
) -> str:
    """Create a state token for invitation acceptance.
    
    Args:
        invite_token: Invitation token
        workspace_id: Workspace ID
        **kwargs: Additional state data
        
    Returns:
        Signed state token
    """
    state_data = {
        'action': 'invite',
        'invite_token': invite_token,
        'workspace_id': workspace_id,
        **kwargs
    }
    
    return sign_state(state_data)


def parse_state_action(state_data: Dict) -> str:
    """Parse the action from state data.
    
    Args:
        state_data: Decoded state data
        
    Returns:
        Action string (e.g., 'auth', 'link', 'invite')
    """
    return state_data.get('action', 'auth')


def is_valid_state_format(state_token: str) -> bool:
    """Check if state token has valid format.
    
    Args:
        state_token: State token to validate
        
    Returns:
        True if format appears valid
    """
    try:
        serialized, signature = state_token.rsplit('.', 1)
        # Basic format check
        return len(serialized) > 0 and len(signature) == 64  # SHA256 hex length
    except ValueError:
        return False
