from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="Management API")

app.include_router(health.router)
