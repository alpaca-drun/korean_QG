#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/run_schema_migration_20260225.sh
#   bash scripts/run_schema_migration_20260225.sh --fix-admin-email
#
# Optional env vars:
#   CONTAINER_NAME (default: KG_db)
#   DB_USER (default: root)
#   DB_PASSWORD (default: niceday123!)
#   DB_NAME (default: KG_db)
#   MIGRATION_SQL (default: db/migrations/20260225_optimize_schema.sql)
#   BACKUP_DIR (default: docker/mariadb/backups)

CONTAINER_NAME="${CONTAINER_NAME:-KG_db}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-niceday123!}"
DB_NAME="${DB_NAME:-KG_db}"
MIGRATION_SQL="${MIGRATION_SQL:-db/migrations/20260225_optimize_schema.sql}"
BACKUP_DIR="${BACKUP_DIR:-docker/mariadb/backups}"
FIX_ADMIN_EMAIL=0

for arg in "$@"; do
  case "$arg" in
    --fix-admin-email)
      FIX_ADMIN_EMAIL=1
      ;;
    *)
      echo "[ERROR] Unknown argument: $arg"
      echo "Usage: bash scripts/run_schema_migration_20260225.sh [--fix-admin-email]"
      exit 1
      ;;
  esac
done

echo "[INFO] Start schema migration: 20260225_optimize_schema"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker command not found"
  exit 1
fi

if [[ ! -f "$MIGRATION_SQL" ]]; then
  echo "[ERROR] Migration SQL not found: $MIGRATION_SQL"
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "[ERROR] Container not running: $CONTAINER_NAME"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/backup_before_20260225_${TS}.sql"

echo "[INFO] Create backup: $BACKUP_FILE"
docker exec "$CONTAINER_NAME" sh -c \
  "mysqldump -u\"$DB_USER\" -p\"$DB_PASSWORD\" \"$DB_NAME\"" > "$BACKUP_FILE"

echo "[INFO] Run migration SQL: $MIGRATION_SQL"
set +e
docker exec -i "$CONTAINER_NAME" mariadb \
  -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$MIGRATION_SQL"
MIGRATION_EXIT_CODE=$?
set -e

if [[ "$MIGRATION_EXIT_CODE" -ne 0 ]]; then
  echo "[WARN] Migration returned non-zero exit code: $MIGRATION_EXIT_CODE"
  echo "[WARN] Common cause: duplicate users.email for UQ_users_email"
fi

if [[ "$FIX_ADMIN_EMAIL" -eq 1 ]]; then
  echo "[INFO] Apply admin email fix and re-try UQ_users_email"
  docker exec "$CONTAINER_NAME" mariadb -u"$DB_USER" -p"$DB_PASSWORD" -D "$DB_NAME" -e \
    "UPDATE users SET email = NULL WHERE login_id = 'admin';"

  # Add UNIQUE only if it does not exist.
  docker exec "$CONTAINER_NAME" mariadb -u"$DB_USER" -p"$DB_PASSWORD" -D "$DB_NAME" -e \
    "SET @has_uq_users_email = (
       SELECT COUNT(*) FROM information_schema.STATISTICS
       WHERE TABLE_SCHEMA = DATABASE()
         AND TABLE_NAME = 'users'
         AND INDEX_NAME = 'UQ_users_email'
     );
     SET @sql = IF(
       @has_uq_users_email = 0,
       'ALTER TABLE users ADD CONSTRAINT UQ_users_email UNIQUE (email)',
       'SELECT \"skip: UQ_users_email exists\" AS info'
     );
     PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;"
fi

echo "[INFO] Verify key changes"
docker exec "$CONTAINER_NAME" mariadb -u"$DB_USER" -p"$DB_PASSWORD" -D "$DB_NAME" -e \
  "SELECT COLUMN_NAME
   FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME='passage_custom'
     AND COLUMN_NAME IN ('is_use','is_used');

   SELECT CONSTRAINT_NAME
   FROM information_schema.TABLE_CONSTRAINTS
   WHERE CONSTRAINT_SCHEMA = DATABASE()
     AND TABLE_NAME='users'
     AND CONSTRAINT_TYPE='UNIQUE'
   ORDER BY CONSTRAINT_NAME;

   SELECT CONSTRAINT_NAME
   FROM information_schema.TABLE_CONSTRAINTS
   WHERE CONSTRAINT_SCHEMA = DATABASE()
     AND CONSTRAINT_NAME IN ('FK_passages_TO_passage_custom','FK_user_preferences_TO_project_source_config')
   ORDER BY CONSTRAINT_NAME;"

echo "[INFO] Done"
echo "[INFO] Backup file: $BACKUP_FILE"
