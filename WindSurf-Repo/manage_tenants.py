#!/usr/bin/env python3
"""
Tenant Management Utility for Multi-Tenant BYOS Backend
Creates tenants, manages API keys, and handles tenant operations
"""

import asyncio
import hashlib
import hmac
import json
import uuid
from typing import Dict, Any, List, Optional
import argparse
import sys

from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models.tenant import Tenant, TenantSetting
from core.config import get_settings
from core.security import get_password_hash

settings = get_settings()


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hmac.new(
        settings.secret_key.encode('utf-8'),
        api_key.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"byos_{uuid.uuid4().hex}_{int(time.time())}"


class TenantManager:
    """Manage tenants in the multi-tenant backend."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def create_tenant(
        self,
        name: str,
        api_key: Optional[str] = None,
        execution_limit: int = 1000
    ) -> Dict[str, Any]:
        """Create a new tenant."""
        
        # Generate API key if not provided
        if not api_key:
            api_key = generate_api_key()
        
        # Hash the API key
        api_key_hash = hash_api_key(api_key)
        
        # Check if tenant already exists
        existing = self.db.query(Tenant).filter(Tenant.name == name).first()
        if existing:
            raise ValueError(f"Tenant '{name}' already exists")
        
        # Create tenant
        tenant = Tenant(
            name=name,
            api_key_hash=api_key_hash,
            execution_limit=execution_limit,
            is_active=True
        )
        
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        
        # Create default settings
        default_settings = {
            "model": "llama3.1",
            "temperature": "0.7",
            "max_tokens": "4096",
            "enable_cache": "true",
            "rate_limit_rpm": "60"
        }
        
        for key, value in default_settings.items():
            setting = TenantSetting(
                tenant_id=tenant.tenant_id,
                setting_key=key,
                setting_value=value
            )
            self.db.add(setting)
        
        self.db.commit()
        
        return {
            "tenant_id": str(tenant.tenant_id),
            "name": tenant.name,
            "api_key": api_key,  # Return plain key for user
            "api_key_hash": api_key_hash,
            "execution_limit": tenant.execution_limit,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat()
        }
    
    def list_tenants(self) -> List[Dict[str, Any]]:
        """List all tenants."""
        tenants = self.db.query(Tenant).all()
        return [
            {
                "tenant_id": str(t.tenant_id),
                "name": t.name,
                "execution_limit": t.execution_limit,
                "daily_execution_count": t.daily_execution_count,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat()
            }
            for t in tenants
        ]
    
    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant by ID."""
        tenant = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            return None
        
        return {
            "tenant_id": str(tenant.tenant_id),
            "name": tenant.name,
            "execution_limit": tenant.execution_limit,
            "daily_execution_count": tenant.daily_execution_count,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat()
        }
    
    def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        execution_limit: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update tenant details."""
        tenant = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            return None
        
        if name:
            tenant.name = name
        if execution_limit is not None:
            tenant.execution_limit = execution_limit
        if is_active is not None:
            tenant.is_active = is_active
        
        self.db.commit()
        self.db.refresh(tenant)
        
        return {
            "tenant_id": str(tenant.tenant_id),
            "name": tenant.name,
            "execution_limit": tenant.execution_limit,
            "daily_execution_count": tenant.daily_execution_count,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat()
        }
    
    def regenerate_api_key(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Regenerate API key for tenant."""
        tenant = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            return None
        
        # Generate new API key
        new_api_key = generate_api_key()
        new_hash = hash_api_key(new_api_key)
        
        # Update tenant
        tenant.api_key_hash = new_hash
        self.db.commit()
        
        return {
            "tenant_id": str(tenant.tenant_id),
            "name": tenant.name,
            "new_api_key": new_api_key,
            "api_key_hash": new_hash
        }
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant."""
        tenant = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            return False
        
        self.db.delete(tenant)
        self.db.commit()
        return True
    
    def get_tenant_settings(self, tenant_id: str) -> Dict[str, str]:
        """Get tenant settings."""
        settings = self.db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id
        ).all()
        
        return {s.setting_key: s.setting_value for s in settings}
    
    def update_tenant_setting(self, tenant_id: str, key: str, value: str) -> bool:
        """Update tenant setting."""
        setting = self.db.query(TenantSetting).filter(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.setting_key == key
        ).first()
        
        if setting:
            setting.setting_value = value
        else:
            setting = TenantSetting(
                tenant_id=tenant_id,
                setting_key=key,
                setting_value=value
            )
            self.db.add(setting)
        
        self.db.commit()
        return True
    
    def reset_daily_counts(self) -> int:
        """Reset daily execution counts for all tenants."""
        from datetime import date
        
        updated = self.db.query(Tenant).filter(
            Tenant.last_execution_date < date.today()
        ).update({
            "daily_execution_count": 0,
            "last_execution_date": date.today()
        })
        
        self.db.commit()
        return updated
    
    def get_usage_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get usage statistics for a tenant."""
        from db.models.tenant import Execution
        from datetime import datetime, timedelta
        
        tenant = self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            return {}
        
        # Get executions from last 30 days
        since = datetime.utcnow() - timedelta(days=30)
        executions = self.db.query(Execution).filter(
            Execution.tenant_id == tenant_id,
            Execution.created_at >= since
        ).all()
        
        total_executions = len(executions)
        avg_execution_time = sum(e.execution_time_ms for e in executions) / total_executions if executions else 0
        total_tokens = sum(e.tokens_generated for e in executions)
        
        return {
            "tenant_id": str(tenant_id),
            "name": tenant.name,
            "daily_execution_count": tenant.daily_execution_count,
            "execution_limit": tenant.execution_limit,
            "usage_percentage": (tenant.daily_execution_count / tenant.execution_limit * 100) if tenant.execution_limit > 0 else 0,
            "monthly_stats": {
                "total_executions": total_executions,
                "avg_execution_time_ms": round(avg_execution_time, 2),
                "total_tokens_generated": total_tokens
            }
        }


def main():
    """CLI interface for tenant management."""
    parser = argparse.ArgumentParser(description="Manage tenants in multi-tenant BYOS backend")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create tenant
    create_parser = subparsers.add_parser("create", help="Create a new tenant")
    create_parser.add_argument("name", help="Tenant name")
    create_parser.add_argument("--api-key", help="API key (auto-generated if not provided)")
    create_parser.add_argument("--limit", type=int, default=1000, help="Execution limit per day")
    
    # List tenants
    subparsers.add_parser("list", help="List all tenants")
    
    # Get tenant
    get_parser = subparsers.add_parser("get", help="Get tenant details")
    get_parser.add_argument("tenant_id", help="Tenant UUID")
    
    # Update tenant
    update_parser = subparsers.add_parser("update", help="Update tenant")
    update_parser.add_argument("tenant_id", help="Tenant UUID")
    update_parser.add_argument("--name", help="New name")
    update_parser.add_argument("--limit", type=int, help="New execution limit")
    update_parser.add_argument("--active", type=bool, help="Active status")
    
    # Regenerate API key
    keygen_parser = subparsers.add_parser("regenerate-key", help="Regenerate API key")
    keygen_parser.add_argument("tenant_id", help="Tenant UUID")
    
    # Delete tenant
    delete_parser = subparsers.add_parser("delete", help="Delete tenant")
    delete_parser.add_argument("tenant_id", help="Tenant UUID")
    
    # Settings
    settings_parser = subparsers.add_parser("settings", help="Get tenant settings")
    settings_parser.add_argument("tenant_id", help="Tenant UUID")
    
    set_parser = subparsers.add_parser("set-setting", help="Set tenant setting")
    set_parser.add_argument("tenant_id", help="Tenant UUID")
    set_parser.add_argument("key", help="Setting key")
    set_parser.add_argument("value", help="Setting value")
    
    # Stats
    stats_parser = subparsers.add_parser("stats", help="Get usage statistics")
    stats_parser.add_argument("tenant_id", help="Tenant UUID")
    
    # Reset daily counts
    subparsers.add_parser("reset-daily", help="Reset daily execution counts")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = TenantManager()
    
    try:
        if args.command == "create":
            result = manager.create_tenant(args.name, args.api_key, args.limit)
            print(f"✅ Tenant created successfully!")
            print(f"   ID: {result['tenant_id']}")
            print(f"   Name: {result['name']}")
            print(f"   API Key: {result['api_key']}")
            print(f"   Execution Limit: {result['execution_limit']}")
            print("   ⚠️  Save the API key securely - it won't be shown again!")
        
        elif args.command == "list":
            tenants = manager.list_tenants()
            print(f"📋 Found {len(tenants)} tenants:")
            for tenant in tenants:
                print(f"   {tenant['name']} ({tenant['tenant_id'][:8]}...)")
                print(f"     Limit: {tenant['execution_limit']}/day")
                print(f"     Used: {tenant['daily_execution_count']} today")
                print(f"     Active: {tenant['is_active']}")
        
        elif args.command == "get":
            tenant = manager.get_tenant(args.tenant_id)
            if tenant:
                print(f"📄 Tenant Details:")
                print(f"   ID: {tenant['tenant_id']}")
                print(f"   Name: {tenant['name']}")
                print(f"   Execution Limit: {tenant['execution_limit']}/day")
                print(f"   Used Today: {tenant['daily_execution_count']}")
                print(f"   Active: {tenant['is_active']}")
                print(f"   Created: {tenant['created_at']}")
            else:
                print("❌ Tenant not found")
        
        elif args.command == "update":
            tenant = manager.update_tenant(args.tenant_id, args.name, args.limit, args.active)
            if tenant:
                print(f"✅ Tenant updated successfully!")
                print(f"   Name: {tenant['name']}")
                print(f"   Limit: {tenant['execution_limit']}/day")
                print(f"   Active: {tenant['is_active']}")
            else:
                print("❌ Tenant not found")
        
        elif args.command == "regenerate-key":
            result = manager.regenerate_api_key(args.tenant_id)
            if result:
                print(f"✅ API key regenerated for {result['name']}")
                print(f"   New API Key: {result['new_api_key']}")
                print("   ⚠️  Save the new API key securely!")
            else:
                print("❌ Tenant not found")
        
        elif args.command == "delete":
            if manager.delete_tenant(args.tenant_id):
                print("✅ Tenant deleted successfully")
            else:
                print("❌ Tenant not found")
        
        elif args.command == "settings":
            settings = manager.get_tenant_settings(args.tenant_id)
            if settings:
                print(f"⚙️  Tenant Settings:")
                for key, value in settings.items():
                    print(f"   {key}: {value}")
            else:
                print("❌ Tenant not found or no settings")
        
        elif args.command == "set-setting":
            if manager.update_tenant_setting(args.tenant_id, args.key, args.value):
                print(f"✅ Setting updated: {args.key} = {args.value}")
            else:
                print("❌ Tenant not found")
        
        elif args.command == "stats":
            stats = manager.get_usage_stats(args.tenant_id)
            if stats:
                print(f"📊 Usage Statistics for {stats['name']}:")
                print(f"   Daily Usage: {stats['daily_execution_count']}/{stats['execution_limit']}")
                print(f"   Usage Percentage: {stats['usage_percentage']:.1f}%")
                print(f"   Monthly Executions: {stats['monthly_stats']['total_executions']}")
                print(f"   Avg Execution Time: {stats['monthly_stats']['avg_execution_time_ms']}ms")
                print(f"   Total Tokens: {stats['monthly_stats']['total_tokens_generated']}")
            else:
                print("❌ Tenant not found")
        
        elif args.command == "reset-daily":
            count = manager.reset_daily_counts()
            print(f"✅ Reset daily counts for {count} tenants")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import time
    main()
