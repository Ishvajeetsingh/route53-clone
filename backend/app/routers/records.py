from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette import status

from app.database import get_db
from app.models.dns import DNSRecord, HostedZone
from app.schemas.dns import (
    RECORD_TYPES,
    DNSRecordCreate,
    DNSRecordOut,
    DNSRecordUpdate,
    PaginatedRecords,
    validate_record_name,
)
from app.services.auth import get_session
from app.services.validation import ensure_values_match_type

router = APIRouter()


def is_protected_record(zone_name: str, record_type: str, record_name: str) -> bool:
    """Apex NS/SOA records are system-managed: editable, never deletable."""
    return record_type in ("NS", "SOA") and record_name.rstrip(".").lower() == zone_name.rstrip(".").lower()


def _get_zone_or_404(db: Session, zone_id: str) -> HostedZone:
    zone = db.get(HostedZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hosted zone not found")
    return zone


def _touch_zone(zone: HostedZone) -> None:
    """Advance the parent zone's updated_at alongside a record mutation.

    HostedZone.updated_at is defined as the latest meaningful change to the
    zone, including its records. Call before commit so the touch lands in the
    same transaction as the record change.
    """
    zone.updated_at = datetime.now(timezone.utc)


def _to_out(rec: DNSRecord) -> DNSRecordOut:
    return DNSRecordOut.model_validate(rec)


@router.get("", response_model=PaginatedRecords)
def list_records(
    zone_id: str,
    q: str = Query(default="", max_length=256),
    record_type: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _s=Depends(get_session),
):
    _get_zone_or_404(db, zone_id)
    query = db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id)
    if record_type:
        normalized = record_type.strip().upper()
        if normalized not in RECORD_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown record type '{record_type}'.",
            )
        query = query.filter(DNSRecord.type == normalized)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(DNSRecord.name.ilike(like), DNSRecord.type.ilike(like)))
    total = query.count()
    rows = query.order_by(DNSRecord.type.asc(), DNSRecord.name.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedRecords(items=[_to_out(r) for r in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=DNSRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    zone_id: str,
    payload: DNSRecordCreate,
    db: Session = Depends(get_db),
    _s=Depends(get_session),
):
    zone = _get_zone_or_404(db, zone_id)
    values = ensure_values_match_type(payload.type, payload.values)
    rec = DNSRecord(
        zone_id=zone.id,
        name=payload.name.strip(),
        type=payload.type,
        values=values,
        ttl=payload.ttl,
        routing_policy=payload.routing_policy,
        description=payload.description,
    )
    db.add(rec)
    _touch_zone(zone)
    db.commit()
    db.refresh(rec)
    return _to_out(rec)


@router.get("/{record_id}", response_model=DNSRecordOut)
def get_record(zone_id: str, record_id: int, db: Session = Depends(get_db), _s=Depends(get_session)):
    _get_zone_or_404(db, zone_id)
    rec = db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id, DNSRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return _to_out(rec)


@router.patch("/{record_id}", response_model=DNSRecordOut)
def update_record(
    zone_id: str, record_id: int, payload: DNSRecordUpdate, db: Session = Depends(get_db), _s=Depends(get_session)
):
    zone = _get_zone_or_404(db, zone_id)
    rec = db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id, DNSRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if payload.name is not None:
        try:
            rec.name = validate_record_name(payload.name)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if payload.values is not None:
        rec.values = ensure_values_match_type(rec.type, payload.values)
    if payload.ttl is not None:
        rec.ttl = payload.ttl
    if payload.routing_policy is not None:
        rec.routing_policy = payload.routing_policy
    if payload.description is not None:
        rec.description = payload.description
    # Apex NS/SOA values stay editable (TTL/values/description); only deletion is blocked.
    _touch_zone(zone)
    db.commit()
    db.refresh(rec)
    return _to_out(rec)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(zone_id: str, record_id: int, db: Session = Depends(get_db), _s=Depends(get_session)):
    zone = _get_zone_or_404(db, zone_id)
    rec = db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id, DNSRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if is_protected_record(rec.zone.name if rec.zone else "", rec.type, rec.name):
        # Mirror Route53: apex NS/SOA cannot be deleted, only edited.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The apex NS and SOA records cannot be deleted.")
    db.delete(rec)
    _touch_zone(zone)
    db.commit()
    return None
