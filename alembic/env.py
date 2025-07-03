import json
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Lire le fichier de configuration
with open("config.json") as f:
    config_data = json.load(f)

# Ajouter le chemin de new_project au PYTHONPATH
sys.path.append(config_data["new_project_path"])

# Importer les modèles de new_project
from app.db.base import Base  # Assurez-vous que c'est le bon chemin

# Configuration d'Alembic
config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def get_url():
    return f"mysql+pymysql://{config_data['user']}:{config_data['password']}@{config_data['host']}:" \
           f"{config_data['port']}/{config_data['db']}"


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    print("ito no ampesaina", get_url())
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
