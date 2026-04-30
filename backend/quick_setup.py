#!/usr/bin/env python3
"""Quick database setup for testing - creates essential tables directly."""
from db.session import engine, SessionLocal
from db.models import Base, User, Workspace, Subscription, TokenWallet, TokenTransaction
from sqlalchemy import text

def create_tables():
    """Create essential tables for testing."""
    print("Creating database tables...")
    
    # Create all tables from models
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")
    
    # Verify tables exist
    db = SessionLocal()
    try:
        # Check user table
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print(f"📋 Tables created: {', '.join(tables)}")
        
        # Check if essential tables exist
        essential = ['users', 'workspaces', 'subscriptions', 'token_wallets', 'token_transactions']
        missing = [t for t in essential if t not in tables]
        if missing:
            print(f"⚠️  Missing tables: {missing}")
        else:
            print("✅ All essential tables present")
            
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
