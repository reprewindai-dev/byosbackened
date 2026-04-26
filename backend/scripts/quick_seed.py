"""Quick seed script for dev API key - works around bcrypt issues."""
import sys
import os
import hashlib
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_URL'] = 'sqlite:///./local.db'
os.environ['SECRET_KEY'] = 'local-dev-secret-key'
os.environ['ENCRYPTION_KEY'] = 'local-dev-encryption-key'

from db.session import SessionLocal
from db.models.workspace import Workspace
from db.models.user import User, UserRole, UserStatus
from db.models.api_key import APIKey
from sqlalchemy import text

print('Creating dev workspace, user, and API key...')

db = SessionLocal()
try:
    # Workspace
    workspace = db.query(Workspace).filter(Workspace.slug == 'dev-local').first()
    if not workspace:
        workspace = Workspace(name='dev-local', slug='dev-local', is_active=True)
        db.add(workspace)
        db.flush()
        print(f'✅ Workspace: {workspace.id}')
    else:
        print(f'Workspace exists: {workspace.id}')
    
    # User - skip password hashing by using raw SQL
    user = db.query(User).filter(User.email == 'dev@byos.local').first()
    if not user:
        # Use a pre-computed bcrypt hash for 'devpass123'
        precomputed_hash = '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'
        db.execute(text('''
            INSERT INTO users (id, email, hashed_password, full_name, role, status, is_active, is_superuser, workspace_id, mfa_enabled, failed_login_attempts, created_at, updated_at)
            VALUES (lower(hex(randomblob(16))), :email, :hash, 'Dev User', 'OWNER', 'ACTIVE', 1, 1, :workspace_id, 0, 0, datetime('now'), datetime('now'))
        '''), {
            'email': 'dev@byos.local',
            'hash': precomputed_hash,
            'workspace_id': workspace.id
        })
        db.commit()
        print('✅ User created')
    else:
        print(f'User exists: {user.id}')
    
    # API Key - get user_id first
    user = db.query(User).filter(User.email == 'dev@byos.local').first()
    api_key = db.query(APIKey).filter(APIKey.name == 'dev-local-key').first()
    if not api_key:
        raw_key = f'byos_{secrets.token_urlsafe(32)}'
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]  # First 8 chars as prefix
        api_key = APIKey(
            name='dev-local-key',
            key_hash=key_hash,
            key_prefix=key_prefix,
            workspace_id=workspace.id,
            user_id=user.id,
            is_active=True,
        )
        db.add(api_key)
        db.commit()
        print('✅ API Key created')
        print('')
        print('='*60)
        print('🔑 COPY THIS KEY FOR STRESS TEST:')
        print('='*60)
        print(f'   {raw_key}')
        print('='*60)
    else:
        print('API Key already exists')
        # Get existing key hash and show a new one
        raw_key = f'byos_{secrets.token_urlsafe(32)}'
        print('')
        print('='*60)
        print('🔑 GENERATE NEW KEY - REPLACE IN DB:')
        print('='*60)
        print(f'   {raw_key}')
        print('='*60)
        print('(Note: You need to update the key_hash in the database)')
        
finally:
    db.close()
