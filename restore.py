import os
import sqlite3
import tempfile
import shutil

import boto3


# =========================================================
# CONFIG
# =========================================================

DB_DIR = "/app/data"
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
# FIND LATEST BACKUP
# =========================================================

def find_latest_backup():

    print(
        "[RESTORE] Listing R2 backups..."
    )

    response = s3.list_objects_v2(
        Bucket=R2_BUCKET,
        Prefix="backups/"
    )

    objects = response.get(
        "Contents",
        []
    )

    backups = [
        obj
        for obj in objects
        if obj["Key"].endswith(".db")
    ]

    if not backups:
        return None

    latest = max(
        backups,
        key=lambda obj: obj["LastModified"]
    )

    return latest


# =========================================================
# VALIDATE DATABASE
# =========================================================

def validate_database(path):

    print(
        "[RESTORE] Checking SQLite database..."
    )

    connection = sqlite3.connect(
        path
    )

    try:

        result = connection.execute(
            "PRAGMA integrity_check;"
        ).fetchone()

        if not result or result[0] != "ok":

            raise RuntimeError(
                f"SQLite integrity check failed: {result}"
            )

    finally:

        connection.close()

    print(
        "[RESTORE] SQLite database is valid."
    )


# =========================================================
# RESTORE
# =========================================================

def restore():

    latest = find_latest_backup()

    if latest is None:

        print(
            "[RESTORE] No backup found in R2."
        )

        return False

    key = latest["Key"]

    print(
        f"[RESTORE] Latest backup: {key}"
    )

    os.makedirs(
        DB_DIR,
        exist_ok=True
    )

    with tempfile.TemporaryDirectory() as temp:

        temporary_db = os.path.join(
            temp,
            "kuma.db"
        )

        print(
            "[RESTORE] Downloading backup..."
        )

        s3.download_file(
            R2_BUCKET,
            key,
            temporary_db
        )

        print(
            "[RESTORE] Download completed."
        )

        validate_database(
            temporary_db
        )

        # Backup database lama jika ada
        if os.path.exists(DB_PATH):

            old_db = DB_PATH + ".old"

            print(
                f"[RESTORE] Existing database "
                f"moved to: {old_db}"
            )

            shutil.move(
                DB_PATH,
                old_db
            )

        shutil.move(
            temporary_db,
            DB_PATH
        )

    print(
        f"[RESTORE] SUCCESS: {DB_PATH}"
    )

    return True


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:

        restore()

    except Exception as error:

        print(
            f"[RESTORE] ERROR: {error}"
        )

        raise