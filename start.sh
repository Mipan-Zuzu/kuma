#!/bin/bash

set -e


echo "======================================"
echo " Uptime Kuma + Cloudflare R2"
echo " Auto Restore + Auto Backup"
echo "======================================"


# =========================================================
# CONFIG
# =========================================================

DATA_DIR="/app/data"
DB_FILE="$DATA_DIR/kuma.db"
DB_CONFIG="$DATA_DIR/db-config.json"


mkdir -p "$DATA_DIR"


# =========================================================
# 1. AUTO RESTORE
# =========================================================

if [ ! -f "$DB_FILE" ]; then

    echo "[RESTORE] Active kuma.db tidak ditemukan."

    echo "[RESTORE] Mencari backup terbaru di R2..."

    python3 /restore.py || true


    if [ -f "$DB_FILE" ]; then

        echo "[RESTORE] Database berhasil dipulihkan."

    else

        echo "[RESTORE] Tidak ada database backup."

        echo "[RESTORE] Kuma akan membuat database baru."

    fi

else

    echo "[RESTORE] Active kuma.db ditemukan."

    echo "[RESTORE] Tidak perlu restore."

fi


# =========================================================
# 2. FORCE SQLITE CONFIG
# =========================================================

if [ ! -f "$DB_CONFIG" ]; then

    echo "[KUMA] Creating SQLite database config..."

    printf '%s\n' '{"type":"sqlite"}' > "$DB_CONFIG"

fi


# =========================================================
# 3. SHOW DATABASE INFO
# =========================================================

echo "======================================"
echo " Database:"
echo " $DB_FILE"
echo ""
echo " Config:"
echo " $DB_CONFIG"
echo "======================================"


if [ -f "$DB_FILE" ]; then

    echo "[KUMA] Database file found:"
    ls -lh "$DB_FILE"

else

    echo "[KUMA] Database belum ada."
    echo "[KUMA] Kuma akan membuat database baru."

fi


# =========================================================
# 4. START UPTIME KUMA
# =========================================================

echo "[KUMA] Starting Uptime Kuma..."


/usr/bin/dumb-init -- node server/server.js &

KUMA_PID=$!


# =========================================================
# 5. WAIT FOR KUMA
# =========================================================

echo "[KUMA] Waiting 30 seconds..."

sleep 30


# =========================================================
# 6. INITIAL BACKUP
# =========================================================

echo "[BACKUP] Running initial backup..."


python3 /backup.py || \
    echo "[BACKUP] Initial backup failed."


# =========================================================
# 7. BACKUP EVERY 6 HOURS
# =========================================================

(
    while true; do

        sleep 21600

        echo "======================================"
        echo "[BACKUP] Running scheduled backup..."
        echo "======================================"

        python3 /backup.py || \
            echo "[BACKUP] Scheduled backup failed."

    done
) &


BACKUP_PID=$!


# =========================================================
# 8. WAIT FOR KUMA
# =========================================================

wait "$KUMA_PID"


# =========================================================
# 9. CLEANUP
# =========================================================

kill "$BACKUP_PID" 2>/dev/null || true