from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelemetryCreate(BaseModel):
    vehicle_id: str

    latitude: float | None = None
    longitude: float | None = None

    altitude: float | None = None

    ground_speed: float | None = None
    air_speed: float | None = None

    battery_voltage: float | None = None
    battery_current: float | None = None
    battery_percentage: float | None = None

    roll: float | None = None
    pitch: float | None = None
    yaw: float | None = None

    flight_mode: str | None = None


class TelemetryResponse(TelemetryCreate):
    id: int
    timestamp: datetime

    model_config = ConfigDict(
        from_attributes=True
    )