"""Changing the credits of an album or of a song by hand: a list of (role, artist) that replaces the credits."""

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.album_page import AlbumDetail, get_album
from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.queries import get_or_404, refuse_unknown
from music_backend.api.song_page import SongDetail, get_song
from music_backend.editing import log_revision, put_edit
from music_backend.imports.common import find_or_insert
from music_backend.models import (
    AlbumCredit,
    AlbumCreditEdit,
    AlbumCreditView,
    AlbumView,
    CreditRole,
    SongCredit,
    SongCreditEdit,
    SongCreditView,
    SongView,
)

albums = APIRouter(prefix="/api/v1/albums", tags=["album edit"])
songs = APIRouter(prefix="/api/v1/songs", tags=["song edit"])


class CreditIn(BaseModel):
    role: str  # the name of the role; a role that is not in the dictionary yet is added
    artist_id: int


@dataclass(frozen=True, slots=True)
class CreditTable:
    """The tables of the credits of one kind of entity: the rows of Genius, the edits over them, the view."""

    owner: str  # the column that names the album or the song
    base: Any
    edit: Any
    edit_key: str
    view: Any


SONG_CREDITS = CreditTable("song_id", SongCredit, SongCreditEdit, "song_credit_id", SongCreditView)
ALBUM_CREDITS = CreditTable(
    "album_id", AlbumCredit, AlbumCreditEdit, "album_credit_id", AlbumCreditView
)


async def replace_credits(
    session: AsyncSession, table: CreditTable, owner_id: int, wanted: list[CreditIn]
) -> dict[str, object]:
    """Makes the credits of the album or song what `wanted` says; returns what changed, as the history keeps it.

    A credit of Genius that is not wanted is hidden, not deleted (the import cannot bring it back). One that is wanted
    and hidden is shown again, and one that is not there is added."""
    owner, base, edit, view = table.owner, table.base, table.edit, table.view

    async def pairs() -> set[tuple[int, int]]:
        rows = await session.execute(
            select(view.role_id, view.artist_id).where(getattr(view, owner) == owner_id)
        )
        return {(role_id, artist_id) for role_id, artist_id in rows}

    before = await pairs()
    roles = {
        name: (await find_or_insert(session, CreditRole, {"name": name})).id
        for name in dict.fromkeys(c.role for c in wanted)
    }
    goal = {(roles[c.role], c.artist_id) for c in wanted}
    existing: dict[tuple[int, int], list[Any]] = {}
    for row in await session.scalars(select(base).where(getattr(base, owner) == owner_id)):
        existing.setdefault((row.role_id, row.artist_id), []).append(row)
    async with refuse_unknown(session, "An artist of the credits is not known"):
        for pair in goal:
            if pair not in existing:
                role_name = next(name for name, pk in roles.items() if pk == pair[0])
                session.add(
                    base(
                        **{owner: owner_id},
                        role_id=pair[0],
                        artist_id=pair[1],
                        label_text=role_name,
                    )
                )
        await session.flush()
        for pair, rows in existing.items():
            for row in rows:
                await put_edit(session, edit, {table.edit_key: row.id}, removed=pair not in goal)
        await session.flush()
    after = await pairs()
    names = {pk: name for name, pk in roles.items()}
    names.update(dict((await session.execute(select(CreditRole.id, CreditRole.name))).all()))

    def show(items: set[tuple[int, int]]) -> list[list[object]]:
        return sorted([names[role_id], artist_id] for role_id, artist_id in items)

    return {"credits": [show(before), show(after)]} if before != after else {}


@songs.put("/{song_id}/credits")
async def put_song_credits(
    song_id: int, body: list[CreditIn], session: SessionDep, user: EditorDep
) -> SongDetail:
    await get_or_404(session, SongView, song_id)
    changes = await replace_credits(session, SONG_CREDITS, song_id, body)
    await log_revision(session, "song", song_id, user.id, changes)
    await session.commit()
    return await get_song(song_id, session, user)


@albums.put("/{album_id}/credits")
async def put_album_credits(
    album_id: int, body: list[CreditIn], session: SessionDep, user: EditorDep
) -> AlbumDetail:
    await get_or_404(session, AlbumView, album_id)
    changes = await replace_credits(session, ALBUM_CREDITS, album_id, body)
    await log_revision(session, "album", album_id, user.id, changes)
    await session.commit()
    return await get_album(album_id, session, user)
