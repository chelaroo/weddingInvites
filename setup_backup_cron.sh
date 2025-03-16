#!/bin/bash

# Make backup scripts executable
chmod +x backup_db.sh
chmod +x restore_db.sh

# Get the absolute path to the backup script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_db.sh"

# Create a temporary file for the new crontab
TEMP_CRON=$(mktemp)

# Export current crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "# New crontab" > "$TEMP_CRON"

# Check if the backup job is already in crontab
if grep -q "$BACKUP_SCRIPT" "$TEMP_CRON"; then
    echo "Backup job already exists in crontab."
else
    # Add the backup job to run daily at 2:00 AM
    echo "# Daily database backup at 2:00 AM" >> "$TEMP_CRON"
    echo "0 2 * * * $BACKUP_SCRIPT >> /home/$(whoami)/db_backup.log 2>&1" >> "$TEMP_CRON"
    
    # Install the new crontab
    crontab "$TEMP_CRON"
    echo "Backup job added to crontab. It will run daily at 2:00 AM."
fi

# Clean up
rm "$TEMP_CRON"

echo "Backup system setup complete!"
echo "- Backup script: $BACKUP_SCRIPT"
echo "- Backups will be stored in: /home/$(whoami)/db_backups/"
echo "- Log file: /home/$(whoami)/db_backup.log"
echo ""
echo "To manually run a backup, use: ./backup_db.sh"
echo "To restore from a backup, use: ./restore_db.sh <backup_file.sql.gz>" 