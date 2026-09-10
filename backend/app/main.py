from fastapi import FastAPI
from sqlalchemy import text

from app.api.telemetry import router as telemetry_router
from app.core.database import Base, SessionLocal, engine
from app.models.telemetry import Telemetry


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SkyCore API",
    description="Physical-AI Powered Autonomous Flying-Satellite Platform",
    version="0.1.0",
)


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
    database_status = "disconnected"

    db = SessionLocal()

    try:
        db.execute(text("SELECT 1"))
        database_status = "connected"

    except Exception:
        database_status = "disconnected"

    finally:
        db.close()

    return {
        "status": "ok" if database_status == "connected" else "degraded",
        "service": "skycore-backend",
        "database": database_status,
    }