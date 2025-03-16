#!/bin/bash

# Check if backup file is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Example: $0 /home/user/db_backups/wedding_db_backup_20230101_120000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Database credentials from .env file
source .env

echo "WARNING: This will overwrite the current database ($DATABASE_NAME)."
echo "Are you sure you want to continue? (y/n)"
read -r confirm

if [ "$confirm" != "y" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Starting database restore from $BACKUP_FILE..."

# Restore the database
gunzip -c "$BACKUP_FILE" | PGPASSWORD=$DATABASE_PASSWORD psql -h localhost -U $DATABASE_USER $DATABASE_NAME

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo "Restore completed successfully!"
else
    echo "Restore failed!"
    exit 1
fi 