import logging
import os
from collections.abc import Iterator
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection, Error, connect
from psycopg.errors import CheckViolation
from psycopg.rows import dict_row
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inquiries", tags=["inquiries"])

NAME_MAX_LENGTH = 100
CONTENT_MAX_LENGTH = 5000
INQUIRY_COLUMNS = "id, name, email, content, created_at, updated_at"


class InquiryCreate(BaseModel):
    name: str
    email: EmailStr
    content: str

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_text(value, NAME_MAX_LENGTH)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        return _normalize_text(value, CONTENT_MAX_LENGTH)


class InquiryUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    content: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email")
    @classmethod
    def email_not_null(cls, value: EmailStr | None) -> EmailStr | None:
        if value is None:
            raise ValueError("must not be null")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("must not be null")
        return _normalize_text(value, NAME_MAX_LENGTH)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("must not be null")
        return _normalize_text(value, CONTENT_MAX_LENGTH)


class Inquiry(BaseModel):
    id: int
    name: str
    email: str
    content: str
    created_at: datetime
    updated_at: datetime


def _normalize_text(value: str, max_length: int) -> str:
    stripped = value.strip()
    if not stripped or len(stripped) > max_length:
        raise ValueError(f"must be 1 to {max_length} characters")
    return stripped


def database_url() -> str:
    load_dotenv()
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise HTTPException(status_code=500, detail="database is not configured")
    if "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
    return url


def get_connection() -> Iterator[Connection]:
    try:
        conn = connect(database_url(), row_factory=dict_row, connect_timeout=10)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("database connection failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="database request failed") from exc
    try:
        with conn:
            yield conn
    except HTTPException:
        raise
    except Error as exc:
        logger.warning("database request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="database request failed") from exc


def _one(row: dict | None) -> dict:
    if row is None:
        raise HTTPException(status_code=404, detail="inquiry not found")
    return row


@router.post("", status_code=201, response_model=Inquiry)
def create_inquiry(body: InquiryCreate, conn: Connection = Depends(get_connection)) -> dict:
    try:
        row = conn.execute(
            f"""
            insert into inquiries (name, email, content)
            values (%s, %s, %s)
            returning {INQUIRY_COLUMNS}
            """,
            (body.name, str(body.email), body.content),
        ).fetchone()
    except CheckViolation as exc:
        raise HTTPException(status_code=422, detail="inquiry failed validation") from exc
    return _one(row)


@router.get("", response_model=list[Inquiry])
def list_inquiries(conn: Connection = Depends(get_connection)) -> list[dict]:
    return conn.execute(
        f"""
        select {INQUIRY_COLUMNS}
        from inquiries
        order by created_at desc
        """
    ).fetchall()


@router.get("/{inquiry_id}", response_model=Inquiry)
def get_inquiry(inquiry_id: int, conn: Connection = Depends(get_connection)) -> dict:
    row = conn.execute(
        f"""
        select {INQUIRY_COLUMNS}
        from inquiries
        where id = %s
        """,
        (inquiry_id,),
    ).fetchone()
    return _one(row)


@router.patch("/{inquiry_id}", response_model=Inquiry)
def update_inquiry(
    inquiry_id: int,
    body: InquiryUpdate,
    conn: Connection = Depends(get_connection),
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="no fields to update")
    if "email" in changes:
        changes["email"] = str(changes["email"])

    assignments = [f"{column} = %s" for column in ("name", "email", "content") if column in changes]
    values = [changes[column] for column in ("name", "email", "content") if column in changes]
    assignments.append("updated_at = now()")
    values.append(inquiry_id)
    try:
        row = conn.execute(
            f"""
            update inquiries
            set {", ".join(assignments)}
            where id = %s
            returning {INQUIRY_COLUMNS}
            """,
            values,
        ).fetchone()
    except CheckViolation as exc:
        raise HTTPException(status_code=422, detail="inquiry failed validation") from exc
    return _one(row)


@router.delete("/{inquiry_id}", status_code=204)
def delete_inquiry(inquiry_id: int, conn: Connection = Depends(get_connection)) -> None:
    row = conn.execute(
        "delete from inquiries where id = %s returning id",
        (inquiry_id,),
    ).fetchone()
    _one(row)
