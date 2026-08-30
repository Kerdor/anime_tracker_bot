from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    library: Mapped[list["UserMedia"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_original: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    year: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sources: Mapped[list["MediaSource"]] = relationship(back_populates="media", cascade="all, delete-orphan")
    library_entries: Mapped[list["UserMedia"]] = relationship(back_populates="media")
    genres: Mapped[list["Genre"]] = relationship(secondary="media_genres", back_populates="media")


class MediaSource(Base):
    __tablename__ = "media_sources"
    __table_args__ = (UniqueConstraint("source", "source_id", "media_type", name="uq_media_source"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    media: Mapped["Media"] = relationship(back_populates="sources")


class UserMedia(Base):
    __tablename__ = "user_media"
    __table_args__ = (UniqueConstraint("user_id", "media_id", name="uq_user_media"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="library")
    media: Mapped["Media"] = relationship(back_populates="library_entries")


class Genre(Base):
    __tablename__ = "genres"
    __table_args__ = (UniqueConstraint("name", name="uq_genre_name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    media: Mapped[list["Media"]] = relationship(secondary="media_genres", back_populates="genres")


class MediaGenre(Base):
    __tablename__ = "media_genres"
    __table_args__ = (UniqueConstraint("media_id", "genre_id", name="uq_media_genre"),)

    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)
