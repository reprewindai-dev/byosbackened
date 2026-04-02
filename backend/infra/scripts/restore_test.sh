#!/bin/bash
# Restore test script - tests backup restoration
# Run weekly to verify backups are working

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-byos_postgres}"
TEST_DB="byos_ai_test_restore"

# Find latest backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR/backup_*.tar.gz" | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup found in $BACKUP_DIR"
    exit 1
fi

echo "Testing restore from: $LATEST_BACKUP"

# Extract backup
TEMP_DIR=$(mktemp -d)
tar -xzf "$LATEST_BACKUP" -C "$TEMP_DIR"

# Find SQL dump
SQL_DUMP=$(find "$TEMP_DIR" -name "postgres_*.sql.gz" | head -1)

if [ -z "$SQL_DUMP" ]; then
    echo "ERROR: SQL dump not found in backup"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Create test database
echo "Creating test database..."
docker exec "$POSTGRES_CONTAINER" psql -U postgres -c "DROP DATABASE IF EXISTS $TEST_DB;"
docker exec "$POSTGRES_CONTAINER" psql -U postgres -c "CREATE DATABASE $TEST_DB;"

# Restore SQL dump
echo "Restoring SQL dump..."
gunzip -c "$SQL_DUMP" | docker exec -i "$POSTGRES_CONTAINER" psql -U postgres "$TEST_DB"

# Verify restore
echo "Verifying restore..."
TABLE_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U postgres -d "$TEST_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "SUCCESS: Restore test passed. Found $TABLE_COUNT tables."
    # Cleanup test database
    docker exec "$POSTGRES_CONTAINER" psql -U postgres -c "DROP DATABASE $TEST_DB;"
    rm -rf "$TEMP_DIR"
    exit 0
else
    echo "ERROR: Restore test failed. No tables found."
    rm -rf "$TEMP_DIR"
    exit 1
fi
