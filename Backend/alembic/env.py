from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os

# --- Load .env from management app ---
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "apps", "management", ".env"))

# --- Point alembic to use env var DATABASE_URL ---
config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))

# ---- Import shared models Base ----
from shared.models.property import Base

# Set target metadata for migrations
target_metadata = Base.metadata

# --- standard alembic boilerplate ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
