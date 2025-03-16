# Database Backup System

This directory contains scripts for automatically backing up and restoring the wedding website's PostgreSQL database.

## Setup

1. Make sure all scripts are executable:
   ```
   chmod +x backup_db.sh restore_db.sh setup_backup_cron.sh
   ```

2. Run the setup script to configure the automated backup:
   ```
   ./setup_backup_cron.sh
   ```

This will:
- Set up a daily backup at 2:00 AM
- Store backups in `/home/[username]/db_backups/`
- Log backup operations to `/home/[username]/db_backup.log`

## Manual Operations

### Creating a Manual Backup

To manually create a backup:
```
./backup_db.sh
```

### Restoring from a Backup

To restore the database from a backup:
```
./restore_db.sh /path/to/backup_file.sql.gz
```

For example:
```
./restore_db.sh /home/[username]/db_backups/wedding_db_backup_20230101_120000.sql.gz
```

## Backup Rotation

By default, the system keeps the 10 most recent backups. You can change this by editing the `MAX_BACKUPS` variable in `backup_db.sh`.

## Off-Server Backups

For additional security, consider enabling one of the off-server backup options in `backup_db.sh`:

1. SCP to another server
2. Upload to AWS S3
3. Email (for small databases only)

To enable, uncomment and configure the desired option in the backup script.

## Troubleshooting

If backups are not running:
1. Check the log file: `cat /home/[username]/db_backup.log`
2. Verify cron is running: `systemctl status cron`
3. Check your crontab: `crontab -l`

## Security Considerations

- Backup files contain all database data, so keep them secure
- Consider encrypting backups if they contain sensitive information
- Regularly test the restore process to ensure backups are valid 