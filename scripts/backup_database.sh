#!/bin/bash
# TaxDown Database Backup Script
# Backs up the Railway PostgreSQL database
#
# Usage: ./scripts/backup_database.sh
#
# Prerequisites:
#   - pg_dump installed (comes with PostgreSQL)
#   - DATABASE_URL_PUBLIC environment variable set
#   - AWS CLI configured (optional, for S3 uploads)

set -e  # Exit on error

# Configuration
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="taxdown_backup_${DATE}.sql"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    if ! command -v pg_dump &> /dev/null; then
        error "pg_dump is not installed. Please install PostgreSQL client tools."
    fi

    if [ -z "$DATABASE_URL_PUBLIC" ] && [ -z "$DATABASE_URL" ]; then
        error "DATABASE_URL_PUBLIC or DATABASE_URL environment variable is not set."
    fi
}

# Create backup directory if it doesn't exist
setup_directories() {
    log "Setting up backup directory..."
    mkdir -p "$BACKUP_DIR"
}

# Perform the backup
perform_backup() {
    log "Starting database backup..."

    # Use public URL for external access, fallback to DATABASE_URL
    DB_URL="${DATABASE_URL_PUBLIC:-$DATABASE_URL}"

    pg_dump "$DB_URL" \
        --verbose \
        --format=plain \
        --no-owner \
        --no-privileges \
        > "$BACKUP_DIR/$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log "Backup created: $BACKUP_DIR/$BACKUP_FILE"
    else
        error "Backup failed!"
    fi
}

# Compress the backup
compress_backup() {
    log "Compressing backup..."
    gzip "$BACKUP_DIR/$BACKUP_FILE"

    COMPRESSED_FILE="${BACKUP_FILE}.gz"
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$COMPRESSED_FILE" | cut -f1)
    log "Compressed backup: $BACKUP_DIR/$COMPRESSED_FILE ($BACKUP_SIZE)"
}

# Upload to S3 (optional)
upload_to_s3() {
    if command -v aws &> /dev/null && [ -n "$S3_BACKUP_BUCKET" ]; then
        log "Uploading to S3..."
        aws s3 cp "$BACKUP_DIR/${BACKUP_FILE}.gz" "s3://$S3_BACKUP_BUCKET/"

        if [ $? -eq 0 ]; then
            log "Uploaded to S3: s3://$S3_BACKUP_BUCKET/${BACKUP_FILE}.gz"
        else
            warn "S3 upload failed, but local backup is intact."
        fi
    else
        log "S3 upload skipped (AWS CLI not configured or S3_BACKUP_BUCKET not set)"
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."

    COUNT=$(find "$BACKUP_DIR" -name "taxdown_backup_*.gz" -mtime +$RETENTION_DAYS | wc -l)

    if [ "$COUNT" -gt 0 ]; then
        find "$BACKUP_DIR" -name "taxdown_backup_*.gz" -mtime +$RETENTION_DAYS -delete
        log "Removed $COUNT old backup(s)"
    else
        log "No old backups to remove"
    fi
}

# List existing backups
list_backups() {
    log "Existing backups:"
    ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null || echo "  No backups found"
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "  TaxDown Database Backup"
    echo "=========================================="
    echo ""

    check_prerequisites
    setup_directories
    perform_backup
    compress_backup
    upload_to_s3
    cleanup_old_backups

    echo ""
    echo "=========================================="
    log "Backup completed successfully!"
    echo "=========================================="
    echo ""

    list_backups
}

# Run main function
main "$@"
