import sqlite3
conn = sqlite3.connect("local.db")
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables ({len(tables)}):")
for t in sorted(tables):
    print(f"  {t}")
conn.close()
