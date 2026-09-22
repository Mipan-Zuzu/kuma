#!/bin/bash

set -e

echo "======================================"
echo " Uptime Kuma + Cloudflare R2"
echo " Auto Restore + Auto Backup"
echo "======================================"

DB_DIR="/app/db"
DB_FILE="$DB_DIR/kuma.db"

mkdir -p "$DB_DIR"

# =========================================================
# 1. AUTO RESTORE
# =========================================================

if [ ! -f "$DB_FILE" ]; then
    echo "[RESTORE] kuma.db tidak ditemukan."
    echo "[RESTORE] Mencari backup terbaru di R2..."

    python3 /restore.py

    if [ -f "$DB_FILE" ]; then
        echo "[RESTORE] Database berhasil dipulihkan."
    else
        echo "[RESTORE] Tidak ada backup. Kuma akan membuat database baru."
    fi
else
    echo "[RESTORE] kuma.db ditemukan. Tidak perlu restore."
fi


# =========================================================
# 2. START UPTIME KUMA DENGAN ENTRYPOINT ASLINYA
# =========================================================

echo "[KUMA] Starting Uptime Kuma..."

/usr/bin/dumb-init -- node server/server.js &
KUMA_PID=$!


# =========================================================
# 3. BACKUP SETELAH KUMA START
# =========================================================

sleep 30

echo "[BACKUP] Running initial backup..."

python3 /backup.py || \
    echo "[BACKUP] Initial backup failed."


# =========================================================
# 4. BACKUP SETIAP 6 JAM
# =========================================================

(
    while true; do
        sleep 21600

        echo "[BACKUP] Running scheduled backup..."

        python3 /backup.py || \
            echo "[BACKUP] Scheduled backup failed."
    done
) &

BACKUP_PID=$!


# =========================================================
# 5. TUNGGU KUMA
# =========================================================

wait "$KUMA_PID"

kill "$BACKUP_PID" 2>/dev/null || true