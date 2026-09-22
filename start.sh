#!/bin/bash

set -e

echo "======================================"
echo " Uptime Kuma + Cloudflare R2 Backup"
echo "======================================"

# Pastikan data directory tersedia
mkdir -p /app/data

# Jalankan backup pertama setelah Kuma siap
echo "[INFO] Starting Uptime Kuma..."

node server/server.js &
KUMA_PID=$!

echo "[INFO] Waiting for Uptime Kuma to start..."

for i in {1..60}; do
    if curl -fsS http://127.0.0.1:3001 > /dev/null 2>&1; then
        echo "[INFO] Uptime Kuma is ready."
        break
    fi

    sleep 2
done

# Backup pertama
echo "[INFO] Running initial R2 backup..."
python3 /backup.py || echo "[WARN] Initial backup failed."

# Backup setiap 6 jam
(
    while true; do
        sleep 21600

        echo "[INFO] Running scheduled R2 backup..."
        python3 /backup.py || echo "[WARN] Scheduled backup failed."
    done
) &

BACKUP_PID=$!

# Jika Kuma mati, container ikut mati
wait $KUMA_PID

# Bersihkan proses backup
kill $BACKUP_PID 2>/dev/null || true