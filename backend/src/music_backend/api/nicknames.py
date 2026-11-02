"""The names of an artist (see `models/edits.py` and `names.py`): read for the page, and replaced as a whole by the editor,
which is simpler than one call for every spelling and period: the editor holds the list and saves it once."""

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Row, Subquery, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.queries import album_roles, get_or_404, refuse_unknown, song_roles
from music_backend.editing import log_revision, put_edit
from music_backend.enums import DatePrecision, NicknameKind, NicknameScope
from music_backend.models import (
    AlbumView,
    ArtistAlias,
    ArtistAliasEdit,
    ArtistView,
    Nickname,
    NicknamePeriod,
    NicknameSpelling,
    NicknameUse,
    SongView,
)

router = APIRouter(prefix="/api/v1/artists", tags=["nicknames"])


class ReleaseRef(BaseModel):
    """An album or a song a name is tied to."""

    kind: Literal["album", "song"]
    id: int
    name: str
    variant: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None


class PeriodOut(BaseModel):
    id: int
    start: ReleaseRef | None  # none: from the beginning


class UseOut(BaseModel):
    id: int
    release: ReleaseRef
    spelling: str | None  # how the release writes the name
    scope: NicknameScope  # where an alter ego is the name: as an artist, in the credits, or in both


class NicknameOut(BaseModel):
    id: int
    kind: NicknameKind
    name: str
    spellings: list[str]
    periods: list[PeriodOut]  # of a main name: when it was in force
    uses: list[
        UseOut
    ]  # of an alter ego: where it is the name; of a main name: where a spelling is chosen


class PeriodIn(BaseModel):
    start_album_id: int | None = None
    start_song_id: int | None = None


class UseIn(BaseModel):
    album_id: int | None = None
    song_id: int | None = None
    spelling: str | None = None  # one of the `spellings` of the name
    scope: NicknameScope = NicknameScope.ANY


class NicknameIn(BaseModel):
    kind: NicknameKind
    name: str
    spellings: list[str] = Field(default_factory=list)
    periods: list[PeriodIn] = Field(default_factory=list)
    uses: list[UseIn] = Field(default_factory=list)


type Kind = Literal["album", "song"]


def _release_columns(model: type[AlbumView] | type[SongView]) -> list[Any]:
    return [
        model.id,
        model.base_name,
        model.variant,
        model.release_date,
        model.release_date_precision,
    ]


def _ref(kind: Kind, row: Row[Any]) -> ReleaseRef:
    return ReleaseRef(
        kind=kind,
        id=row.id,
        name=row.base_name,
        variant=row.variant,
        release_date=row.release_date,
        release_date_precision=row.release_date_precision,
    )


async def release_refs(
    session: AsyncSession, album_ids: set[int], song_ids: set[int]
) -> dict[tuple[Kind, int], ReleaseRef]:
    """The albums and the songs with these ids, by (kind, id)."""
    albums = await session.execute(
        select(*_release_columns(AlbumView)).where(AlbumView.id.in_(album_ids))
    )
    songs = await session.execute(
        select(*_release_columns(SongView)).where(SongView.id.in_(song_ids))
    )
    found: dict[tuple[Kind, int], ReleaseRef] = {("album", r.id): _ref("album", r) for r in albums}
    found |= {("song", r.id): _ref("song", r) for r in songs}
    return found


async def read_nicknames(session: AsyncSession, artist_id: int) -> list[NicknameOut]:
    nicknames = (
        await session.scalars(
            select(Nickname).where(Nickname.artist_id == artist_id).order_by(Nickname.id)
        )
    ).all()
    ids = [n.id for n in nicknames]
    spellings = (
        await session.scalars(
            select(NicknameSpelling)
            .where(NicknameSpelling.nickname_id.in_(ids))
            .order_by(NicknameSpelling.id)
        )
    ).all()
    periods = (
        await session.scalars(
            select(NicknamePeriod)
            .where(NicknamePeriod.nickname_id.in_(ids))
            .order_by(NicknamePeriod.id)
        )
    ).all()
    uses = (
        await session.scalars(
            select(NicknameUse).where(NicknameUse.nickname_id.in_(ids)).order_by(NicknameUse.id)
        )
    ).all()
    text_of = {s.id: s.text for s in spellings}
    releases = await release_refs(
        session,
        {i for p in periods if (i := p.start_album_id)} | {i for u in uses if (i := u.album_id)},
        {i for p in periods if (i := p.start_song_id)} | {i for u in uses if (i := u.song_id)},
    )

    def ref(album_id: int | None, song_id: int | None) -> ReleaseRef | None:
        if album_id is not None:
            return releases[("album", album_id)]
        return releases[("song", song_id)] if song_id is not None else None

    return [
        NicknameOut(
            id=n.id,
            kind=n.kind,
            name=n.name,
            spellings=[s.text for s in spellings if s.nickname_id == n.id],
            periods=[
                PeriodOut(id=p.id, start=ref(p.start_album_id, p.start_song_id))
                for p in periods
                if p.nickname_id == n.id
            ],
            uses=[
                UseOut(
                    id=u.id,
                    release=ref(u.album_id, u.song_id),  # type: ignore[arg-type]
                    spelling=text_of.get(u.spelling_id) if u.spelling_id else None,
                    scope=u.scope,
                )
                for u in uses
                if u.nickname_id == n.id
            ],
        )
        for n in nicknames
    ]


@router.put("/{artist_id}/nicknames")
async def put_nicknames(
    artist_id: int, body: list[NicknameIn], session: SessionDep, user: EditorDep
) -> list[NicknameOut]:
    """Replaces all the names of the artist with the list in the body (ids of the old ones are gone with them)."""
    await get_or_404(session, ArtistView, artist_id)
    before = await read_nicknames(session, artist_id)
    mine = select(Nickname.id).where(Nickname.artist_id == artist_id)
    for table in (NicknameUse, NicknamePeriod, NicknameSpelling):
        await session.execute(delete(table).where(table.nickname_id.in_(mine)))
    await session.execute(delete(Nickname).where(Nickname.artist_id == artist_id))
    async with refuse_unknown(session, "A release of the names is not known"):
        for item in body:
            nickname = Nickname(artist_id=artist_id, kind=item.kind, name=item.name)
            session.add(nickname)
            await session.flush()
            written = {
                text: NicknameSpelling(nickname_id=nickname.id, text=text)
                for text in dict.fromkeys(item.spellings)
            }
            session.add_all(written.values())
            await session.flush()
            # A main name that is never in force would be no name: with no period it is the name from the beginning.
            periods = item.periods or ([PeriodIn()] if item.kind is NicknameKind.MAIN else [])
            session.add_all(
                NicknamePeriod(
                    nickname_id=nickname.id,
                    start_album_id=p.start_album_id,
                    start_song_id=p.start_song_id,
                )
                for p in periods
            )
            for use in item.uses:
                if use.spelling and use.spelling not in written:
                    raise HTTPException(422, f"{use.spelling} is not a spelling of {item.name}")
                session.add(
                    NicknameUse(
                        nickname_id=nickname.id,
                        album_id=use.album_id,
                        song_id=use.song_id,
                        spelling_id=written[use.spelling].id if use.spelling else None,
                        scope=use.scope,
                    )
                )
        await session.flush()
    after = await read_nicknames(session, artist_id)
    await log_revision(
        session,
        "artist",
        artist_id,
        user.id,
        {"nicknames": [[n.model_dump() for n in before], [n.model_dump() for n in after]]}
        if before != after
        else {},
    )
    await session.commit()
    return after


@router.get("/{artist_id}/releases")
async def search_releases(
    artist_id: int, session: SessionDep, _: EditorDep, q: str = "", limit: int = 30
) -> list[ReleaseRef]:
    """The albums and the songs the artist is on, the newest first, whose names have `q` in them: to pick the release a
    name starts with or is tied to."""
    await get_or_404(session, ArtistView, artist_id)

    async def find(
        kind: Kind, model: type[AlbumView] | type[SongView], roles: Subquery, key: str
    ) -> list[ReleaseRef]:
        rows = await session.execute(
            select(*_release_columns(model))
            .where(
                model.id.in_(select(roles.c[key]).where(roles.c.artist_id == artist_id)),
                model.base_name.ilike(f"%{q}%"),
            )
            .order_by(model.release_date.desc().nulls_last(), func.lower(model.base_name))
            .limit(limit)
        )
        return [_ref(kind, row) for row in rows]

    found = [
        *await find("album", AlbumView, album_roles(), "album_id"),
        *await find("song", SongView, song_roles(), "song_id"),
    ]
    found.sort(
        key=lambda r: (
            r.release_date is None,
            -(r.release_date or date.min).toordinal(),
            r.name.lower(),
        )
    )
    return found[:limit]


@router.put("/{artist_id}/aliases")
async def put_aliases(
    artist_id: int, body: list[str], session: SessionDep, user: EditorDep
) -> list[str]:
    """Keeps the aliases of Genius that are in the body and takes the others away; the import cannot bring them back."""
    await get_or_404(session, ArtistView, artist_id)
    aliases = (
        await session.execute(
            select(ArtistAlias.id, ArtistAlias.name).where(ArtistAlias.artist_id == artist_id)
        )
    ).all()
    kept = set(body)
    for alias_id, name in aliases:
        await put_edit(session, ArtistAliasEdit, {"alias_id": alias_id}, removed=name not in kept)
    shown = sorted(name for _, name in aliases if name in kept)
    await log_revision(
        session,
        "artist",
        artist_id,
        user.id,
        {"aliases": [sorted(name for _, name in aliases), shown]},
    )
    await session.commit()
    return shown
