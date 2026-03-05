"""Reset alembic version table"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load chatbot .env
load_dotenv(Path(__file__).parent / ".env")

database_url = os.getenv("CHAT_DATABASE_URL")
if not database_url:
    print("❌ CHAT_DATABASE_URL not found")
    sys.exit(1)

# Convert asyncpg to psycopg2 for sync operations and fix SSL parameter
database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
database_url = database_url.replace("ssl=require", "sslmode=require")

engine = create_engine(database_url)

with engine.connect() as conn:
    # Drop existing tables
    conn.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS chats CASCADE"))
    # Drop alembic_version table
    conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
    conn.commit()
    print("✅ Cleared all tables and alembic_version")

print("\nNow run: alembic upgrade head")
