from db.session import SessionLocal
from sqlalchemy import text

def check_database():
    db = SessionLocal()
    try:
        # Check existing tables
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print('Existing tables:', tables)
        
        # Check if users table exists and has records
        if 'users' in tables:
            count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
            print(f'Users in database: {count}')
            
            # Check table schema
            schema = db.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in schema]
            print(f'User table columns: {columns}')
        
        # Test registration directly
        if 'users' in tables and 'workspaces' in tables:
            print('Database schema looks OK')
        else:
            print('Missing essential tables')
            
    except Exception as e:
        print(f'Database check failed: {e}')
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_database()
