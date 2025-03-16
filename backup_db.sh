#!/bin/bash

# Database credentials from .env file
source .env

# Backup directory
BACKUP_DIR="/home/$(whoami)/db_backups"
mkdir -p $BACKUP_DIR

# Timestamp for the backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/wedding_db_backup_$TIMESTAMP.sql.gz"

# Number of backups to keep (adjust as needed)
MAX_BACKUPS=10

echo "Starting database backup..."

# Create the backup and compress it
PGPASSWORD=$DATABASE_PASSWORD pg_dump -h localhost -U $DATABASE_USER $DATABASE_NAME | gzip > $BACKUP_FILE

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    # Remove old backups if we have more than MAX_BACKUPS
    NUM_BACKUPS=$(ls -1 $BACKUP_DIR/wedding_db_backup_*.sql.gz 2>/dev/null | wc -l)
    if [ $NUM_BACKUPS -gt $MAX_BACKUPS ]; then
        echo "Removing old backups. Keeping most recent $MAX_BACKUPS backups."
        ls -1t $BACKUP_DIR/wedding_db_backup_*.sql.gz | tail -n +$((MAX_BACKUPS+1)) | xargs rm -f
    fi
else
    echo "Backup failed!"
    exit 1
fi

# Optional: Copy to external location
# Uncomment and configure one of these options if you want off-server backups

# Option 1: SCP to another server
# scp $BACKUP_FILE backup_user@backup-server:/path/to/backup/directory/

# Option 2: Upload to S3 (requires AWS CLI)
# aws s3 cp $BACKUP_FILE s3://your-bucket-name/database-backups/

# Option 3: Send via email (for small databases only)
echo "Wedding database backup" | mail -a $BACKUP_FILE -s "Database Backup $TIMESTAMP" chelaruc197@gmail.com

echo "Backup process completed." 