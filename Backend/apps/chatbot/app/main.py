import sys
import os
from pathlib import Path

# Add Backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="Chatbot API")

app.include_router(health.router)
