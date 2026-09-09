from fastapi import FastAPI

app = FastAPI(
    title="SkyCore API",
    description="Physical-AI Powered Autonomous Flying-Satellite Platform",
    version="0.1.0",
)


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
    }
