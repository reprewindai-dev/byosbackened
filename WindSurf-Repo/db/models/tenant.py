"""Tenant model for multi-tenant architecture."""

from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from db.base_class import Base


class Tenant(Base):
    """Tenant model for multi-tenant isolation."""
    
    __tablename__ = "tenants"
    
    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    execution_limit = Column(Integer, default=1000)
    daily_execution_count = Column(Integer, default=0)
    last_execution_date = Column(Date, default=date.today)
    
    # Relationships
    executions = relationship("Execution", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("TenantSetting", back_populates="tenant", cascade="all, delete-orphan")


class Execution(Base):
    """Execution tracking for tenant requests."""
    
    __tablename__ = "executions"
    
    execution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    tokens_generated = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="executions")


class TenantSetting(Base):
    """Tenant-specific settings."""
    
    __tablename__ = "tenant_settings"
    
    setting_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="settings")
