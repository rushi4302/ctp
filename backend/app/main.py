from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.router import router
from app.core.config import settings
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✅ Database Connected Successfully!")
    except Exception as e:
        print("❌ Database Connection Failed!")
        print(e)

    yield


import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists and mount static files
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Backend is running!",
        "database": "Connected",
    }