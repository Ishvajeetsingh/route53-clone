from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette import status

from app.database import get_db
from app.models.dns import DNSRecord, HostedZone
from app.schemas.dns import HostedZoneCreate, HostedZoneOut, HostedZoneUpdate, PaginatedZones
from app.services.auth import get_session

router = APIRouter()

DEFAULT_NS = [
    "ns-1.awsdns-1.com.",
    "ns-2.awsdns-2.net.",
    "ns-3.awsdns-3.org.",
    "ns-4.awsdns-4.co.uk.",
]


def _to_out(zone: HostedZone, record_count: int = 0) -> HostedZoneOut:
    return HostedZoneOut(
        id=zone.id,
        name=zone.name,
        description=zone.description,
        type=zone.type,
        record_count=record_count,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


@router.get("", response_model=PaginatedZones)
def list_zones(
    q: str = Query(default="", max_length=256),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _s=Depends(get_session),
):
    query = db.query(HostedZone)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(HostedZone.name.ilike(like))
    total = query.count()
    zones = query.order_by(HostedZone.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    ids = [z.id for z in zones]
    counts: dict[str, int] = {}
    if ids:
        rows = db.query(DNSRecord.zone_id, func.count(DNSRecord.id)).filter(DNSRecord.zone_id.in_(ids)).group_by(DNSRecord.zone_id).all()
        counts = {zone_id: c for zone_id, c in rows}
    return PaginatedZones(
        items=[_to_out(z, counts.get(z.id, 0)) for z in zones], total=total, page=page, page_size=page_size
    )


@router.post("", response_model=HostedZoneOut, status_code=status.HTTP_201_CREATED)
def create_zone(payload: HostedZoneCreate, db: Session = Depends(get_db), _s=Depends(get_session)):
    existing = db.query(HostedZone).filter(func.lower(HostedZone.name) == payload.name.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A hosted zone with this domain already exists.")
    zone = HostedZone(name=payload.name, description=payload.description, type=payload.type)
    db.add(zone)
    db.flush()
    # Mirror Route53: every zone starts with apex NS + SOA records.
    db.add(
        DNSRecord(
            zone_id=zone.id, name=payload.name, type="NS", values=list(DEFAULT_NS), ttl=172800,
            routing_policy="Simple", description="Default name servers",
        )
    )
    db.add(
        DNSRecord(
            zone_id=zone.id, name=payload.name, type="SOA",
            values=["ns-1.awsdns-1.com. awsdns-hostmaster.amazon.com. 1 7200 900 1209600 86400"],
            ttl=900, routing_policy="Simple", description="Start of authority",
        )
    )
    db.commit()
    db.refresh(zone)
    return _to_out(zone, 2)


@router.get("/{zone_id}", response_model=HostedZoneOut)
def get_zone(zone_id: str, db: Session = Depends(get_db), _s=Depends(get_session)):
    zone = db.get(HostedZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hosted zone not found")
    count = db.query(func.count(DNSRecord.id)).filter(DNSRecord.zone_id == zone_id).scalar() or 0
    return _to_out(zone, count)


@router.patch("/{zone_id}", response_model=HostedZoneOut)
def update_zone(zone_id: str, payload: HostedZoneUpdate, db: Session = Depends(get_db), _s=Depends(get_session)):
    zone = db.get(HostedZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hosted zone not found")
    if payload.description is not None:
        zone.description = payload.description
    if payload.type is not None:
        zone.type = payload.type
    db.commit()
    db.refresh(zone)
    count = db.query(func.count(DNSRecord.id)).filter(DNSRecord.zone_id == zone_id).scalar() or 0
    return _to_out(zone, count)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(zone_id: str, db: Session = Depends(get_db), _s=Depends(get_session)):
    zone = db.get(HostedZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hosted zone not found")
    # Explicit child delete in the same transaction: SQLite does not enforce
    # ON DELETE CASCADE without PRAGMA foreign_keys, so records must be
    # removed here rather than relying on the database.
    db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id).delete(synchronize_session=False)
    db.delete(zone)
    db.commit()
    return None
