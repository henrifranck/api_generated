import json
import os
import sys
import subprocess
from utils.move_migrations_versions import move_migration_files

DEFAULT_PATH = os.path.join("alembic", "versions")


def run_migrations(message: str):
    try:
        with open("config.json") as f:
            config_data = json.load(f)

        os.environ["PYTHONPATH"] = config_data["new_project_path"]
        sys.path.append(config_data["new_project_path"])

        local_directory = DEFAULT_PATH
        remote_directory = os.path.normpath(os.path.join(config_data["new_project_path"], DEFAULT_PATH))

        print(f"Remote directory: {remote_directory}")
        print("Moving migration files to local directory...")
        move_migration_files(remote_directory, local_directory)
        print("Finished moving migration files.")

        # ✅ Run Alembic in a fresh subprocess
        print("Creating migration...")
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", message], check=True)

        print("Applying migration...")
        subprocess.run(["alembic", "upgrade", "head"], check=True)

        print("Migrations completed successfully!")

        print("Moving migration files back to remote directory...")
        move_migration_files(local_directory, remote_directory)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
