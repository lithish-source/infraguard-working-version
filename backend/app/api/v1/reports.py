"""Report routes: create, list, fetch, verify, manage."""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import (
    MessageResponse,
    ReportCreate,
    ReportListItem,
    ReportListResponse,
    ReportOut,
    VerificationCreate,
)
from app.services import report_service
from app.ai_runtime import get_ai_analyzer

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(
    title: str = Form(...),
    description: str = Form(...),
    category_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: Optional[str] = Form(None),
    district_id: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    try:
        cat_id = int(category_id)
    except (ValueError, TypeError):
        cat_id = 1

    dist_id = None
    if district_id and str(district_id).strip():
        try:
            dist_id = int(district_id)
        except (ValueError, TypeError):
            dist_id = None

    payload = ReportCreate(
        title=title, description=description, category_id=cat_id,
        latitude=latitude, longitude=longitude, address=address or None, district_id=dist_id,
    )
    return await report_service.create_report(
        db, user, payload, images, get_ai_analyzer(),
        background_tasks=background_tasks,
    )


@router.get("", response_model=ReportListResponse)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    district_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    order_by: str = Query("created_at_desc"),
    db: Session = Depends(get_db),
):
    items, total = report_service.list_reports(
        db, page=page, page_size=page_size,
        status_filter=status, severity_filter=severity,
        category_id=category_id, district_id=district_id,
        search=search, order_by=order_by,
    )
    return ReportListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/map", response_model=dict)
def map_data(
    district_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """GeoJSON FeatureCollection for the map view."""
    from app.services.map_service import reports_geojson
    return reports_geojson(
        db, district_id=district_id, category_id=category_id,
        severity=severity, status=status,
    )


@router.get("/heatmap")
def heatmap_data(
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from app.services.map_service import heatmap_points
    return {"points": heatmap_points(db, severity=severity)}


@router.get("/me", response_model=List[ReportOut])
@router.get("/me/my-reports", response_model=List[ReportOut])
def my_reports(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return report_service.my_reports(db, user.id)


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    return report_service.get_report(db, report_id)


@router.post("/{report_id}/verifications", response_model=ReportOut)
async def add_verification(
    report_id: int,
    severity_vote: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    is_confirmed: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payload = VerificationCreate(
        severity_vote=severity_vote, comment=comment, is_confirmed=is_confirmed,
    )
    return report_service.add_verification(db, report_id, user, payload, image)
