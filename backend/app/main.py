from fastapi import FastAPI
from fastapi import Depends, HTTPException
from sqlalchemy import text

from app.api.router import router
from app.core.config import settings
from app.database.session import engine


import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
        "message": "Civic Intelligence API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            database_name = connection.execute(text("SELECT current_database()")).scalar_one()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    if database_name != "civic_db_test":
        raise HTTPException(status_code=503, detail="Backend database safety check failed")
    return {"status": "ok", "database": database_name}
