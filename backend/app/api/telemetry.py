from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse


router = APIRouter(
    prefix="/api/telemetry",
    tags=["Telemetry"],
)


@router.post(
    "",
    response_model=TelemetryResponse,
)
def create_telemetry(
    data: TelemetryCreate,
    db: Session = Depends(get_db),
):
    telemetry = Telemetry(
        **data.model_dump()
    )

    db.add(telemetry)
    db.commit()
    db.refresh(telemetry)

    return telemetry


@router.get(
    "",
    response_model=list[TelemetryResponse],
)
def get_telemetry(
    db: Session = Depends(get_db),
):
    telemetry_records = (
        db.query(Telemetry)
        .order_by(Telemetry.timestamp.desc())
        .limit(100)
        .all()
    )

    return telemetry_records


@router.get(
    "/latest/{vehicle_id}",
    response_model=TelemetryResponse | None,
)
def get_latest_telemetry(
    vehicle_id: str,
    db: Session = Depends(get_db),
):
    telemetry = (
        db.query(Telemetry)
        .filter(Telemetry.vehicle_id == vehicle_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )

    return telemetry