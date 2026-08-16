"""Initial relational data model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.database import Base


def utc_now() -> datetime:
    """Return a naive UTC timestamp suitable for SQLite."""

    return datetime.utcnow()


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    messages: Mapped[list["Message"]] = relationship(back_populates="person", cascade="all, delete-orphan")
    memories: Mapped[list["Memory"]] = relationship(back_populates="person", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="person", cascade="all, delete-orphan")
    photos: Mapped[list["Photo"]] = relationship(back_populates="person", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_person_id", "person_id"),
        Index("ix_messages_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    person: Mapped[Person] = relationship(back_populates="messages")


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memories_person_id", "person_id"),
        Index("ix_memories_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    person: Mapped[Person] = relationship(back_populates="memories")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_person_id", "person_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    person: Mapped[Person] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (Index("ix_conversation_messages_conversation_id", "conversation_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (
        Index("ix_photos_person_id", "person_id"),
        Index("ix_photos_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    person: Mapped[Person] = relationship(back_populates="photos")

