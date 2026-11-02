"""What people add to Genius's data: the nicknames of an artist, and the edits laid over the imported rows.

The import writes only the tables of `catalog.py` and never reads these: the edits are applied when the data is shown
(the views of `views.py`). A field that was set by hand is named in `overridden` of its `*_edit` row; the value may be
NULL (a date taken away), which is why a name list and not "the column is not NULL" says what was edited.
Resetting a field to Genius is taking its name out of the list."""

from datetime import date

from sqlalchemy import ARRAY, Text, false, text
from sqlalchemy.orm import Mapped, mapped_column

from music_backend.enums import (
    AlbumType,
    ArtistType,
    DatePrecision,
    NicknameKind,
    NicknameScope,
    SongArtistRole,
)
from music_backend.models.base import Base, IdMixin, Timestamps, enum_column, fk

# The fields of each entity that can be overridden: the names in `overridden` and the columns of the `*_edit` row.
ALBUM_FIELDS = (
    "base_name",
    "variant",
    "album_type",
    "is_released",
    "release_date",
    "release_date_precision",
    "cover_url",
    "cover_thumbnail_url",
    "cover_primary_color",
    "cover_secondary_color",
    "description",
)
ARTIST_FIELDS = ("disambiguator", "artist_type", "description", "real_name", "cover_url")
SONG_FIELDS = (
    "base_name",
    "variant",
    "release_date",
    "release_date_precision",
    "cover_url",
    "cover_thumbnail_url",
    "cover_primary_color",
    "cover_secondary_color",
    "description",
    "genre_id",
)

# --- nicknames --------------------------------------------------------------------------------------


class Nickname(Base, IdMixin):
    """A name of an artist. The `main` ones follow each other in time (`NicknamePeriod`); an `alter_ego` is tied to
    releases (`NicknameUse`). Every name has spellings (`NicknameSpelling`) that mean the same name."""

    __tablename__ = "nickname"

    artist_id: Mapped[int] = fk("artist", index=True)
    kind: Mapped[NicknameKind] = enum_column(NicknameKind)
    name: Mapped[str]


class NicknameSpelling(Base, IdMixin):
    """Bladee, BLADEE and bladee are one name: this is a way to write it that is not the name itself."""

    __tablename__ = "nickname_spelling"

    nickname_id: Mapped[int] = fk("nickname", index=True)
    text: Mapped[str]


class NicknamePeriod(Base, IdMixin):
    """A main name is in force from the release `start_*` on, until the next period starts. The first period has no
    start (from the beginning). A name that came back (Snoop Dogg) has two periods."""

    __tablename__ = "nickname_period"

    nickname_id: Mapped[int] = fk("nickname", index=True)
    start_album_id: Mapped[int | None] = fk("album", nullable=True)
    start_song_id: Mapped[int | None] = fk("song", nullable=True)


class NicknameUse(Base, IdMixin):
    """A name on a release (an album, or a song): for an alter ego this is what makes it the name shown there, for a
    main name only `spelling_id` matters (how this release writes it)."""

    __tablename__ = "nickname_use"

    nickname_id: Mapped[int] = fk("nickname", index=True)
    album_id: Mapped[int | None] = fk("album", nullable=True, index=True)
    song_id: Mapped[int | None] = fk("song", nullable=True, index=True)
    spelling_id: Mapped[int | None] = fk("nickname_spelling", nullable=True)
    # Where an alter ego is the name on the release; a main name is written the same everywhere.
    scope: Mapped[NicknameScope] = enum_column(
        NicknameScope, default=NicknameScope.ANY, server_default=NicknameScope.ANY.value
    )


# --- fields set by hand -------------------------------------------------------------------------------


def overridden_column() -> Mapped[list[str]]:
    return mapped_column(ARRAY(Text), server_default=text("'{}'"))


class AlbumEdit(Base, Timestamps):
    __tablename__ = "album_edit"

    album_id: Mapped[int] = fk("album", primary_key=True)
    overridden: Mapped[list[str]] = overridden_column()
    base_name: Mapped[str | None]
    variant: Mapped[str | None]
    album_type: Mapped[AlbumType | None] = enum_column(AlbumType, nullable=True)
    is_released: Mapped[bool | None]
    release_date: Mapped[date | None]
    release_date_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    cover_url: Mapped[str | None]
    cover_thumbnail_url: Mapped[str | None]
    cover_primary_color: Mapped[str | None]
    cover_secondary_color: Mapped[str | None]
    description: Mapped[str | None]


class ArtistEdit(Base, Timestamps):
    __tablename__ = "artist_edit"

    artist_id: Mapped[int] = fk("artist", primary_key=True)
    overridden: Mapped[list[str]] = overridden_column()
    disambiguator: Mapped[str | None]
    artist_type: Mapped[ArtistType | None] = enum_column(ArtistType, nullable=True)
    description: Mapped[str | None]
    real_name: Mapped[str | None]
    cover_url: Mapped[str | None]


class SongEdit(Base, Timestamps):
    __tablename__ = "song_edit"

    song_id: Mapped[int] = fk("song", primary_key=True)
    overridden: Mapped[list[str]] = overridden_column()
    base_name: Mapped[str | None]
    variant: Mapped[str | None]
    release_date: Mapped[date | None]
    release_date_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    cover_url: Mapped[str | None]
    cover_thumbnail_url: Mapped[str | None]
    cover_primary_color: Mapped[str | None]
    cover_secondary_color: Mapped[str | None]
    description: Mapped[str | None]
    genre_id: Mapped[int | None] = fk("genre", nullable=True)


# --- lists: what was taken out, and what the user added to a row ------------------------------------------


class ArtistMemberEdit(Base):
    """A member of a group as the user has it. `removed` hides the row of Genius (the import does not bring it back),
    the rest is new: the order, and the time the artist was in the group. Each end of the time is a release (the date
    follows it) or a date (a year is enough); no end and `has_left` false means he is in the group now, no end and `has_left`
    true that he left at a time nobody knows."""

    __tablename__ = "artist_member_edit"

    group_id: Mapped[int] = fk("artist", primary_key=True)
    member_id: Mapped[int] = fk("artist", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())
    position: Mapped[int | None]
    start_album_id: Mapped[int | None] = fk("album", nullable=True)
    start_song_id: Mapped[int | None] = fk("song", nullable=True)
    start_date: Mapped[date | None]
    start_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    end_album_id: Mapped[int | None] = fk("album", nullable=True)
    end_song_id: Mapped[int | None] = fk("song", nullable=True)
    end_date: Mapped[date | None]
    end_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    has_left: Mapped[bool] = mapped_column(default=False, server_default=false())


class AlbumTrackEdit(Base):
    """A track of an album as the user has it: `removed` hides the row of Genius, the order is the user's own."""

    __tablename__ = "album_track_edit"

    album_track_id: Mapped[int] = fk("album_track", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())
    disc_number: Mapped[int | None]
    position: Mapped[int | None]


class ArtistAliasEdit(Base):
    """An alias of Genius that the user took away: the import adds aliases by name and never brings this one back."""

    __tablename__ = "artist_alias_edit"

    alias_id: Mapped[int] = fk("artist_alias", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())


class AlbumArtistEdit(Base):
    """An artist of an album as the user has it: `removed` hides the row of Genius, `position` is the user's order."""

    __tablename__ = "album_artist_edit"

    album_id: Mapped[int] = fk("album", primary_key=True)
    artist_id: Mapped[int] = fk("artist", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())
    position: Mapped[int | None]


class SongArtistEdit(Base):
    """An artist of a song (primary or featured) as the user has it: `removed` hides the row of Genius, `position` is
    the order of the user."""

    __tablename__ = "song_artist_edit"

    song_id: Mapped[int] = fk("song", primary_key=True)
    artist_id: Mapped[int] = fk("artist", primary_key=True)
    role: Mapped[SongArtistRole] = enum_column(SongArtistRole, primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())
    position: Mapped[int | None]


class SongCreditEdit(Base):
    """A credit of a song (a role and an artist): `removed` hides the row of Genius."""

    __tablename__ = "song_credit_edit"

    song_credit_id: Mapped[int] = fk("song_credit", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())


class AlbumCreditEdit(Base):
    """A credit of an album: `removed` hides the row of Genius."""

    __tablename__ = "album_credit_edit"

    album_credit_id: Mapped[int] = fk("album_credit", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())


class SongTagEdit(Base):
    """A tag of a song: `removed` hides the row of Genius."""

    __tablename__ = "song_tag_edit"

    song_id: Mapped[int] = fk("song", primary_key=True)
    tag_id: Mapped[int] = fk("tag", primary_key=True)
    removed: Mapped[bool] = mapped_column(default=False, server_default=false())
