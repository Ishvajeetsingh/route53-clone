"""Pydantic schemas with Route53-aware validation."""

import ipaddress
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

RECORD_TYPES = ["A", "AAAA", "CNAME", "TXT", "MX", "NS", "PTR", "SRV", "CAA", "SOA"]
ROUTING_POLICIES = ["Simple", "Weighted", "Latency", "Failover", "Geolocation"]

_HOSTNAME = re.compile(r"^(?=.{1,253}\.?$)([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.?$")
# Record *names* may also carry service labels such as _sip._tcp or _dmarc.
_RECORD_NAME = re.compile(r"^(?=.{1,253}\.?$)([a-zA-Z0-9_]([a-zA-Z0-9_\-]{0,61}[a-zA-Z0-9_])?\.)*[a-zA-Z0-9_]([a-zA-Z0-9_\-]{0,61}[a-zA-Z0-9_])?\.?$")


def _is_hostname(v: str) -> bool:
    return v == "." or bool(_HOSTNAME.match(v))


def validate_record_name(name: str) -> str:
    v = name.strip()
    if not v:
        raise ValueError("Record name must not be empty")
    if len(v) > 1024:
        raise ValueError("Record name is too long")
    if v == "@":
        return v
    core = v[2:] if v.startswith("*.") else v
    if not _RECORD_NAME.match(core):
        raise ValueError("Record name must be a valid hostname (e.g. www.example.com, @ for apex)")
    return v


def validate_record_value(rtype: str, value: str) -> str:
    v = value.strip()
    if not v:
        raise ValueError("value must not be empty")
    if rtype == "A":
        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError("A record must be a valid IPv4 address (e.g. 192.0.2.1)") from None
    elif rtype == "AAAA":
        try:
            ipaddress.IPv6Address(v)
        except ValueError:
            raise ValueError("AAAA record must be a valid IPv6 address (e.g. 2001:db8::1)") from None
    elif rtype in ("CNAME", "NS", "PTR"):
        if not _is_hostname(v):
            raise ValueError(f"{rtype} record must be a valid hostname")
    elif rtype == "MX":
        parts = v.split()
        if len(parts) != 2 or not parts[0].isdigit() or not 0 <= int(parts[0]) <= 65535 or not _is_hostname(parts[1]):
            raise ValueError("MX record must look like '10 mail.example.com'")
    elif rtype == "SRV":
        parts = v.split()
        if (
            len(parts) != 4
            or not all(p.isdigit() for p in parts[:3])
            or not 0 <= int(parts[2]) <= 65535
            or not _is_hostname(parts[3])
        ):
            raise ValueError("SRV record must look like '10 5 443 target.example.com'")
    elif rtype == "CAA":
        parts = v.split(None, 2)
        if (
            len(parts) != 3
            or not parts[0].isdigit()
            or not 0 <= int(parts[0]) <= 255
            or parts[1] not in ("issue", "issuewild", "iodef")
        ):
            raise ValueError("CAA record must look like '0 issue \"ca.example.com\"'")
    elif rtype == "TXT":
        if len(v) > 4096:
            raise ValueError("TXT value is too long")
    elif rtype == "SOA":
        if len(v.split()) < 2:
            raise ValueError("SOA record must include nameserver and contact")
    return v


# ---------- Auth ----------


def ensure_utc(value: datetime) -> datetime:
    """Attach UTC to naive datetimes.

    SQLite's CURRENT_TIMESTAMP (and therefore every existing row) is UTC but
    comes back naive. Interpreting those values as UTC keeps the API's ISO-8601
    output unambiguous without rewriting stored data.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    username: str
    display_name: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# ---------- Hosted zones ----------


class HostedZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=1024)
    type: Literal["Public", "Private"] = "Public"

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        v = v.strip().lower()
        if not _HOSTNAME.match(v):
            raise ValueError("Enter a valid domain name (e.g. example.com)")
        return v.rstrip(".") + "."


class HostedZoneUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=1024)
    type: Literal["Public", "Private"] | None = None


class HostedZoneOut(BaseModel):
    id: str
    name: str
    description: str
    type: str
    record_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at", "updated_at")
    def serialize_utc(self, value: datetime) -> str:
        return ensure_utc(value).isoformat()


# ---------- Records ----------


class DNSRecordCreate(BaseModel):
    name: str = Field(min_length=1, max_length=1024)
    type: Literal["A", "AAAA", "CNAME", "TXT", "MX", "NS", "PTR", "SRV", "CAA", "SOA"] = "A"
    values: list[str] = Field(min_length=1, max_length=32)
    ttl: int = Field(default=300, ge=1, le=2147483647)
    routing_policy: Literal["Simple", "Weighted", "Latency", "Failover", "Geolocation"] = "Simple"
    description: str = Field(default="", max_length=1024)

    @model_validator(mode="after")
    def check_values(self):
        cleaned = [validate_record_value(self.type, v) for v in self.values]
        object.__setattr__(self, "values", cleaned)
        if self.type == "CNAME" and len(cleaned) != 1:
            raise ValueError("CNAME records must have exactly one value")
        object.__setattr__(self, "name", validate_record_name(self.name))
        return self


class DNSRecordUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=1024)
    values: list[str] | None = Field(default=None, min_length=1, max_length=32)
    ttl: int | None = Field(default=None, ge=1, le=2147483647)
    routing_policy: Literal["Simple", "Weighted", "Latency", "Failover", "Geolocation"] | None = None
    description: str | None = Field(default=None, max_length=1024)


class DNSRecordOut(BaseModel):
    id: int
    zone_id: str
    name: str
    type: str
    values: list[str]
    ttl: int
    routing_policy: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at", "updated_at")
    def serialize_utc(self, value: datetime) -> str:
        return ensure_utc(value).isoformat()


class PaginatedZones(BaseModel):
    items: list[HostedZoneOut]
    total: int
    page: int
    page_size: int


class PaginatedRecords(BaseModel):
    items: list[DNSRecordOut]
    total: int
    page: int
    page_size: int
