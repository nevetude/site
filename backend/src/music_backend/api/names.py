"""The name an artist has on a release, as SQL: the nicknames of `models/edits.py`.

`artist_name(artist, on=, album_id=, song_id=)` is the name to show for the artist in a place that has a date (the
release the artist is on, or a clip of it): in a query it stands where `Artist.base_name` stood. The rules:

1. An alter ego tied to this album or this song is the name there, and nothing else is shown, in the places its scope
   says: `artist` in the lines of artists, `credit` in the credits, `any` in both. The place tells which it is with
   `scope`. So on one release the main name can be the artist and an alter ego the producer.
2. Else the main nickname in force on the date: the one whose period started last, not after it (a period with no
   start is in force from the beginning). With no date known the latest period wins.
3. A spelling chosen for the release is written instead of the name.
4. An artist with no nicknames keeps the name Genius gave.

If the date is earlier than the start of every period (the first one has a start the user gave), the first period is
taken. Dates are the effective ones: the release a period starts with can have been changed by hand.
"""

from datetime import date
from typing import Any, Literal

from sqlalchemy import ColumnElement, Date, and_, false, func, literal, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import SQLColumnExpression

from music_backend.enums import NicknameKind, NicknameScope
from music_backend.models import (
    AlbumView,
    Artist,
    Nickname,
    NicknamePeriod,
    NicknameSpelling,
    NicknameUse,
    SongView,
)

type Column = SQLColumnExpression[Any] | int | date | None


def _on_release(use: Any, album_id: Column, song_id: Column) -> ColumnElement[bool]:
    """The uses of a name on this album or on this song."""
    conditions = []
    if album_id is not None:
        conditions.append(use.album_id == album_id)
    if song_id is not None:
        conditions.append(use.song_id == song_id)
    return or_(*conditions) if conditions else false()


def artist_name(
    artist_id: Column,
    *,
    on: Column = None,
    album_id: Column = None,
    song_id: Column = None,
    scope: Literal[NicknameScope.ARTIST, NicknameScope.CREDIT] = NicknameScope.ARTIST,
) -> ColumnElement[str]:
    when: SQLColumnExpression[Any] | None = (
        literal(on, Date) if isinstance(on, date) else on  # type: ignore[assignment]
    )

    alter_nick = aliased(Nickname)
    alter_use = aliased(NicknameUse)
    alter_spelling = aliased(NicknameSpelling)
    alter_ego = (
        select(func.coalesce(alter_spelling.text, alter_nick.name))
        .select_from(alter_use)
        .join(alter_nick, alter_nick.id == alter_use.nickname_id)
        .outerjoin(alter_spelling, alter_spelling.id == alter_use.spelling_id)
        .where(
            alter_nick.artist_id == artist_id,
            alter_nick.kind == NicknameKind.ALTER_EGO,
            alter_use.scope.in_([scope, NicknameScope.ANY]),
            _on_release(alter_use, album_id, song_id),
        )
        .order_by(alter_use.id)
        .limit(1)
        .correlate_except(alter_use, alter_nick, alter_spelling)
        .scalar_subquery()
    )

    def main(*, in_force: bool) -> ColumnElement[str]:
        """The main nickname with its spelling: `in_force` the one on the date, else the first one of all."""
        nick = aliased(Nickname)
        period = aliased(NicknamePeriod)
        use = aliased(NicknameUse)
        spelling = aliased(NicknameSpelling)
        album = aliased(AlbumView)
        song = aliased(SongView)
        starts = func.coalesce(album.release_date, song.release_date)
        query = (
            select(func.coalesce(spelling.text, nick.name))
            .select_from(period)
            .join(nick, nick.id == period.nickname_id)
            .outerjoin(album, album.id == period.start_album_id)
            .outerjoin(song, song.id == period.start_song_id)
            .outerjoin(use, and_(use.nickname_id == nick.id, _on_release(use, album_id, song_id)))
            .outerjoin(spelling, spelling.id == use.spelling_id)
            .where(nick.artist_id == artist_id, nick.kind == NicknameKind.MAIN)
        )
        if in_force:
            if when is not None:
                query = query.where(or_(when.is_(None), starts.is_(None), starts <= when))
            query = query.order_by(starts.desc().nulls_last(), period.id.desc())
        else:
            query = query.order_by(starts.asc().nulls_first(), period.id)
        return (
            query.limit(1)
            .correlate_except(nick, period, use, spelling, album, song)
            .scalar_subquery()
        )

    # An alias: the query around can be on `artist` itself, and then the artist is the one of its row.
    genius = aliased(Artist)
    own = select(genius.base_name).where(genius.id == artist_id).correlate_except(genius)
    return func.coalesce(
        alter_ego, main(in_force=True), main(in_force=False), own.scalar_subquery()
    )
