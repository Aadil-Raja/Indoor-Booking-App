import sys
import os
from pathlib import Path

# Add Backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, auth, properties, courts, pricing, availability, media, public, bookings, owner

app = FastAPI(title="Management API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/auth")
app.include_router(properties.router, prefix="/api")
app.include_router(courts.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(availability.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(owner.router, prefix="/api")
