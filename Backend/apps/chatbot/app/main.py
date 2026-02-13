from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="Chatbot API")

app.include_router(health.router)
