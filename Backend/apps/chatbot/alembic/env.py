from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os
import sys

# Add chatbot app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Add Backend directory to path for shared models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# --- Load .env from chatbot app ---
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# --- Point alembic to use env var CHAT_DATABASE_URL ---
config = context.config
# Convert async URL to sync URL for Alembic
chat_db_url = os.getenv("CHAT_DATABASE_URL", "")
# Replace asyncpg with psycopg2 for Alembic migrations and fix SSL parameter
sync_db_url = chat_db_url.replace("postgresql+asyncpg://", "postgresql://")
# Replace ssl=require with sslmode=require for psycopg2
sync_db_url = sync_db_url.replace("ssl=require", "sslmode=require")
config.set_main_option("sqlalchemy.url", sync_db_url)

# ---- Import chatbot-specific models Base ----
from shared.models.base import Base
from app.models import Chat, Message

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
