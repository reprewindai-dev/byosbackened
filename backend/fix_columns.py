"""Add missing columns to existing tables in local.db."""
import sqlite3

conn = sqlite3.connect("local.db")
cursor = conn.cursor()

# Get existing columns per table
def get_columns(table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]

# Fix subscriptions table
cols = get_columns("subscriptions")
if "monthly_credits_included" not in cols:
    print("Adding subscriptions.monthly_credits_included")
    cursor.execute("ALTER TABLE subscriptions ADD COLUMN monthly_credits_included VARCHAR DEFAULT '0'")

# Fix alerts table - check for resolved_by
cols = get_columns("alerts")
if "resolved_by" not in cols:
    print("Adding alerts.resolved_by")
    cursor.execute("ALTER TABLE alerts ADD COLUMN resolved_by VARCHAR")

# Fix users table - check for missing columns
cols = get_columns("users")
expected_user_cols = ["mfa_enabled", "mfa_secret", "failed_login_attempts", "account_locked_until", "last_login", "last_activity", "github_id", "github_username", "github_access_token"]
for col in expected_user_cols:
    if col not in cols:
        print(f"Adding users.{col}")
        default = "0" if col in ["mfa_enabled", "failed_login_attempts"] else "NULL"
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} VARCHAR DEFAULT {default}")

conn.commit()
conn.close()
print("Done — missing columns added")
