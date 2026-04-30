"""Create missing DB tables (token_wallets, token_transactions) using SQLAlchemy metadata."""
from db.session import engine, Base
import db.models  # import all models so Base.metadata is populated

# Only create tables that don't exist yet
Base.metadata.create_all(bind=engine)
print("Done — all model tables ensured in local.db")
