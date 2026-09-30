import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from psycopg.errors import CheckViolation
from pydantic import BaseModel, field_validator

from myapp.inquiries import _normalize_text, get_connection

router = APIRouter(prefix="/reservations", tags=["reservations"])

NAME_MAX_LENGTH = 100
NOTE_MAX_LENGTH = 2000
PHONE_PATTERN = re.compile(r"^(010\d{8}|01[16789]\d{7,8})$")
RESERVATION_COLUMNS = "id, name, phone, note, created_at"


class ReservationCreate(BaseModel):
    name: str
    phone: str
    note: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_text(value, NAME_MAX_LENGTH)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if PHONE_PATTERN.fullmatch(digits) is None:
            raise ValueError("must be a Korean mobile number")
        return digits

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > NOTE_MAX_LENGTH:
            raise ValueError(f"must be at most {NOTE_MAX_LENGTH} characters")
        return stripped


class Reservation(BaseModel):
    id: int
    name: str
    phone: str
    note: str | None
    created_at: datetime


@router.post("", status_code=201, response_model=Reservation)
def create_reservation(body: ReservationCreate, conn: Connection = Depends(get_connection)) -> dict:
    try:
        row = conn.execute(
            f"""
            insert into reservations (name, phone, note)
            values (%s, %s, %s)
            returning {RESERVATION_COLUMNS}
            """,
            (body.name, body.phone, body.note),
        ).fetchone()
    except CheckViolation as exc:
        raise HTTPException(status_code=422, detail="reservation failed validation") from exc
    if row is None:
        raise HTTPException(status_code=502, detail="database request failed")
    return row
