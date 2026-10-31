from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NoteStatus(StrEnum):
    saved = "saved"
    researching = "researching"
    complete = "complete"
    failed = "failed"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    context: Mapped[str | None] = mapped_column(Text)
    status: Mapped[NoteStatus] = mapped_column(
        Enum(NoteStatus, native_enum=False, create_constraint=True),
        default=NoteStatus.saved,
    )
    research_summary: Mapped[str | None] = mapped_column(Text)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    researched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
