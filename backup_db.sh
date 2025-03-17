#!/bin/bash

# Database credentials from .env file
source .env

# Backup directory
BACKUP_DIR="/home/$(whoami)/db_backups"
mkdir -p $BACKUP_DIR

# Timestamp for the backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/wedding_db_backup_$TIMESTAMP.sql.gz"
CSV_FILE="$BACKUP_DIR/guests_$TIMESTAMP.csv"

# Number of backups to keep (adjust as needed)
MAX_BACKUPS=10

echo "Starting database backup..."

# Create the full backup and compress it
PGPASSWORD=$DATABASE_PASSWORD pg_dump -h localhost -U $DATABASE_USER $DATABASE_NAME | gzip > $BACKUP_FILE

# Export guests table to CSV
echo "Exporting guests table to CSV..."
PGPASSWORD=$DATABASE_PASSWORD psql -h localhost -U $DATABASE_USER $DATABASE_NAME -c "\COPY (SELECT * FROM guests ORDER BY created_at DESC) TO '$CSV_FILE' WITH CSV HEADER"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup and CSV export completed successfully"
    echo "- Full backup: $BACKUP_FILE"
    echo "- CSV export: $CSV_FILE"
    
    # Remove old backups if we have more than MAX_BACKUPS
    NUM_BACKUPS=$(ls -1 $BACKUP_DIR/wedding_db_backup_*.sql.gz 2>/dev/null | wc -l)
    if [ $NUM_BACKUPS -gt $MAX_BACKUPS ]; then
        echo "Removing old backups. Keeping most recent $MAX_BACKUPS backups."
        ls -1t $BACKUP_DIR/wedding_db_backup_*.sql.gz | tail -n +$((MAX_BACKUPS+1)) | xargs rm -f
    fi
    
    # Remove old CSVs if we have more than MAX_BACKUPS
    NUM_CSVS=$(ls -1 $BACKUP_DIR/guests_*.csv 2>/dev/null | wc -l)
    if [ $NUM_CSVS -gt $MAX_BACKUPS ]; then
        echo "Removing old CSV exports. Keeping most recent $MAX_BACKUPS exports."
        ls -1t $BACKUP_DIR/guests_*.csv | tail -n +$((MAX_BACKUPS+1)) | xargs rm -f
    fi
else
    echo "Backup failed!"
    exit 1
fi

# Send CSV via email
echo "Sending CSV export via email..."
echo "Wedding website guests list as of $(date)" | mail -a $CSV_FILE -s "Wedding Guests List $TIMESTAMP" chelaruc197@gmail.com

# Optional: Send full backup via email (uncomment if needed)
# echo "Wedding database backup" | mail -a $BACKUP_FILE -s "Database Backup $TIMESTAMP" chelaruc197@gmail.com

echo "Backup process completed." 