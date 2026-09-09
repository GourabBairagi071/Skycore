from fastapi import FastAPI

from app.core.database import Base, engine
from app.models.telemetry import Telemetry
from app.api.telemetry import router as telemetry_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SkyCore API",
    description="Physical-AI Powered Autonomous Flying-Satellite Platform",
    version="0.1.0",
)


# Register routers
app.include_router(telemetry_router)


@app.get("/")
def root():
    return {
        "project": "SkyCore",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "skycore-backend",
        "database": "connected",
    }