from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    vehicle_id = Column(
        String(50),
        nullable=False,
        index=True,
    )

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    altitude = Column(Float, nullable=True)

    ground_speed = Column(Float, nullable=True)
    air_speed = Column(Float, nullable=True)

    battery_voltage = Column(Float, nullable=True)
    battery_current = Column(Float, nullable=True)
    battery_percentage = Column(Float, nullable=True)

    roll = Column(Float, nullable=True)
    pitch = Column(Float, nullable=True)
    yaw = Column(Float, nullable=True)

    flight_mode = Column(
        String(50),
        nullable=True,
    )