import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import boto3


# =========================================================
# CONFIG
# =========================================================

DB_PATH = "/app/data/kuma.db"


# =========================================================
# ENVIRONMENT
# =========================================================

def get_env(name):
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}"
        )

    return value


R2_ENDPOINT = get_env("R2_ENDPOINT")
R2_ACCESS_KEY_ID = get_env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = get_env("R2_SECRET_ACCESS_KEY")
R2_BUCKET = get_env("R2_BUCKET")


# =========================================================
# R2 CLIENT
# =========================================================

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


# =========================================================
# SQLITE BACKUP
# =========================================================

def create_database_backup(destination):

    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            f"Database not found: {DB_PATH}"
        )

    print(
        f"[BACKUP] Source database: {DB_PATH}"
    )

    source = sqlite3.connect(
        DB_PATH
    )

    try:

        target = sqlite3.connect(
            destination
        )

        try:

            source.backup(
                target
            )

        finally:

            target.close()

    finally:

        source.close()


# =========================================================
# MAIN
# =========================================================

def main():

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    print(
        f"[BACKUP] Starting backup: {timestamp}"
    )

    with tempfile.TemporaryDirectory() as temp:

        database_backup = os.path.join(
            temp,
            "kuma.db"
        )

        print(
            "[BACKUP] Creating SQLite snapshot..."
        )

        create_database_backup(
            database_backup
        )

        key = (
            f"backups/"
            f"kuma-{timestamp}.db"
        )

        print(
            f"[BACKUP] Uploading to R2: {key}"
        )

        s3.upload_file(
            database_backup,
            R2_BUCKET,
            key
        )

        print(
            f"[BACKUP] SUCCESS: "
            f"s3://{R2_BUCKET}/{key}"
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()