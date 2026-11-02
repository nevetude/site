"""The read side: views of the catalog tables with the edits of `edits.py` laid over them (see its docstring).

Every API read of an album, an artist, a song, the members of a group or the tracks of an album goes through these
classes, so what the site shows is Genius's data as the user has changed it. The import writes the tables and never
reads a view. The views are made by the migration; the classes have the columns of the tables by the shared mixins
(`ArtistColumns`, ...), and `tests/test_views.py` checks that every column of a table is in its view.
They are not on `Base.metadata`, so Alembic does not make tables of them."""

from datetime import date, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped

from music_backend.enums import DatePrecision, SongArtistRole
from music_backend.models.base import (
    GeniusEntity,
    IdMixin,
    Named,
    Timestamps,
    enum_column,
    fk,
)
from music_backend.models.catalog import AlbumColumns, ArtistColumns, SongColumns


class ViewBase(DeclarativeBase):
    type_annotation_map = {datetime: DateTime(timezone=True)}  # noqa: RUF012


class ArtistView(ViewBase, IdMixin, Timestamps, GeniusEntity, Named, ArtistColumns):
    __tablename__ = "artist_view"


class AlbumView(ViewBase, IdMixin, Timestamps, GeniusEntity, Named, AlbumColumns):
    __tablename__ = "album_view"


class SongView(ViewBase, IdMixin, Timestamps, GeniusEntity, Named, SongColumns):
    __tablename__ = "song_view"


class ArtistMemberView(ViewBase):
    """The members of a group without the removed ones, in the order of the user. `starts_on` and `ends_on` are the
    dates of the time in the group (the date of the release it is tied to, or the date given), NULL when unknown;
    `has_left` with no `ends_on` is a member who left at an unknown time."""

    __tablename__ = "artist_member_view"

    group_id: Mapped[int] = fk("artist", primary_key=True)
    member_id: Mapped[int] = fk("artist", primary_key=True)
    position: Mapped[int | None]
    start_album_id: Mapped[int | None] = fk("album", nullable=True)
    start_song_id: Mapped[int | None] = fk("song", nullable=True)
    end_album_id: Mapped[int | None] = fk("album", nullable=True)
    end_song_id: Mapped[int | None] = fk("song", nullable=True)
    starts_on: Mapped[date | None]
    starts_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    ends_on: Mapped[date | None]
    ends_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    has_left: Mapped[bool]


class AlbumTrackView(ViewBase, IdMixin):
    """The tracks of an album without the removed ones, in the order of the user."""

    __tablename__ = "album_track_view"

    album_id: Mapped[int] = fk("album", index=True)
    song_id: Mapped[int] = fk("song", index=True)
    disc_number: Mapped[int | None]
    position: Mapped[int | None]
    sort_order: Mapped[int | None]
    is_primary: Mapped[bool | None]


class AlbumArtistView(ViewBase):
    """The artists of an album without the removed ones, in the order of the user."""

    __tablename__ = "album_artist_view"

    album_id: Mapped[int] = fk("album", primary_key=True)
    artist_id: Mapped[int] = fk("artist", primary_key=True)
    position: Mapped[int | None]


class SongArtistView(ViewBase):
    """The artists of a song (primary and featured) without the removed ones, in the order of the user."""

    __tablename__ = "song_artist_view"

    song_id: Mapped[int] = fk("song", primary_key=True)
    artist_id: Mapped[int] = fk("artist", primary_key=True)
    role: Mapped[SongArtistRole] = enum_column(SongArtistRole, primary_key=True)
    position: Mapped[int | None]


class SongCreditView(ViewBase, IdMixin):
    """The credits of a song without the removed ones."""

    __tablename__ = "song_credit_view"

    song_id: Mapped[int] = fk("song", index=True)
    artist_id: Mapped[int] = fk("artist", index=True)
    role_id: Mapped[int] = fk("credit_role")
    label_text: Mapped[str | None]


class AlbumCreditView(ViewBase, IdMixin):
    """The credits of an album without the removed ones."""

    __tablename__ = "album_credit_view"

    album_id: Mapped[int] = fk("album", index=True)
    artist_id: Mapped[int] = fk("artist", index=True)
    role_id: Mapped[int] = fk("credit_role")
    label_text: Mapped[str | None]


class SongTagView(ViewBase):
    """The tags of a song without the removed ones."""

    __tablename__ = "song_tag_view"

    song_id: Mapped[int] = fk("song", primary_key=True)
    tag_id: Mapped[int] = fk("tag", primary_key=True)
