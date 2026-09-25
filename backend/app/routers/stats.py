"""Lightweight account-level summary for the dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dns import DNSRecord, HostedZone
from app.services.auth import get_session

router = APIRouter()


@router.get("/summary")
def summary(db: Session = Depends(get_db), _s=Depends(get_session)):
    zones = db.query(func.count(HostedZone.id)).scalar() or 0
    records = db.query(func.count(DNSRecord.id)).scalar() or 0
    return {"hosted_zones": zones, "records": records}
