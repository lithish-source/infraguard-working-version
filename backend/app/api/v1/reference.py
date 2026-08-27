"""Reference data: infrastructure types, districts."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import District, InfrastructureType
from app.schemas import MessageResponse

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/infrastructure-types")
def list_infrastructure_types(db: Session = Depends(get_db)):
    rows = db.execute(select(InfrastructureType).order_by(InfrastructureType.name)).scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "code": r.code,
            "description": r.description,
            "default_priority_weight": r.default_priority_weight,
            "icon": r.icon,
        }
        for r in rows
    ]


@router.get("/districts")
def list_districts(db: Session = Depends(get_db)):
    rows = db.execute(select(District).order_by(District.name)).scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "code": r.code,
            "state": r.state, "population": r.population,
            "area_sq_km": r.area_sq_km,
        }
        for r in rows
    ]
