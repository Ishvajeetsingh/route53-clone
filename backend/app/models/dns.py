"""SQLAlchemy models: HostedZone 1 -> many DNSRecord."""

import datetime
import secrets

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_zone_id() -> str:
    # Route53-like hosted zone id, e.g. Z1A2B3C4D5E6F7
    return "Z" + secrets.token_hex(7).upper()[:13]


class HostedZone(Base):
    __tablename__ = "hosted_zones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_zone_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="Public")  # Public | Private
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    records: Mapped[list["DNSRecord"]] = relationship(
        "DNSRecord", back_populates="zone", cascade="all, delete-orphan", passive_deletes=True
    )


class DNSRecord(Base):
    __tablename__ = "dns_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("hosted_zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(1024), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    values: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ttl: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    routing_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="Simple")
    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    zone: Mapped["HostedZone"] = relationship("HostedZone", back_populates="records")

    __table_args__ = (
        Index("ix_dns_records_zone_type", "zone_id", "type"),
        Index("ix_dns_records_zone_name", "zone_id", "name"),
    )
