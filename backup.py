import os
import sqlite3
import tempfile
import tarfile
from datetime import datetime, timezone

import boto3


DATA_DIR = "/app/data"


def get_env(name):
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")

    return value


R2_ENDPOINT = get_env("R2_ENDPOINT")
R2_ACCESS_KEY_ID = get_env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = get_env("R2_SECRET_ACCESS_KEY")
R2_BUCKET = get_env("R2_BUCKET")


s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
)


def create_database_backup(destination):
    source_path = os.path.join(DATA_DIR, "kuma.db")

    if not os.path.exists(source_path):
        raise RuntimeError("kuma.db not found")

    source = sqlite3.connect(source_path)

    try:
        target = sqlite3.connect(destination)

        try:
            source.backup(target)
        finally:
            target.close()

    finally:
        source.close()


def create_archive(archive_path, database_backup):
    files = [
        "db-config.json",
        "docker-tls",
        "screenshots",
        "upload",
    ]

    with tarfile.open(archive_path, "w:gz") as tar:

        # Consistent SQLite backup
        tar.add(
            database_backup,
            arcname="kuma.db"
        )

        # Additional Kuma data
        for name in files:

            path = os.path.join(DATA_DIR, name)

            if os.path.exists(path):
                tar.add(
                    path,
                    arcname=name
                )


def upload_backup(archive_path, timestamp):
    key = f"backups/kuma-{timestamp}.tar.gz"

    s3.upload_file(
        archive_path,
        R2_BUCKET,
        key,
    )

    return key


def main():

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    print(f"[BACKUP] Starting backup: {timestamp}")

    with tempfile.TemporaryDirectory() as temp:

        database_backup = os.path.join(
            temp,
            "kuma.db"
        )

        archive_path = os.path.join(
            temp,
            f"kuma-{timestamp}.tar.gz"
        )

        print("[BACKUP] Creating SQLite snapshot...")

        create_database_backup(
            database_backup
        )

        print("[BACKUP] Creating archive...")

        create_archive(
            archive_path,
            database_backup
        )

        print("[BACKUP] Uploading to Cloudflare R2...")

        key = upload_backup(
            archive_path,
            timestamp
        )

        print(
            f"[BACKUP] SUCCESS: s3://{R2_BUCKET}/{key}"
        )


if __name__ == "__main__":
    main()