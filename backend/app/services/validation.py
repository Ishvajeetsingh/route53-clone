"""Validation helpers shared by routers."""

from fastapi import HTTPException
from starlette import status

from app.schemas.dns import validate_record_value


def ensure_values_match_type(rtype: str, values: list[str]) -> list[str]:
    try:
        return [validate_record_value(rtype, v) for v in values]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
