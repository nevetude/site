"""Changing a song by hand: its fields, its artists and its tags (the credits are in `credits_edit.py`)."""

from datetime import date
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.queries import get_or_404, refuse_unknown
from music_backend.api.song_page import SongDetail, get_song
from music_backend.editing import log_revision, override_fields, put_edit
from music_backend.enums import DatePrecision, SongArtistRole
from music_backend.models import (
    SONG_FIELDS,
    SongArtist,
    SongArtistEdit,
    SongArtistView,
    SongEdit,
    SongTag,
    SongTagEdit,
    SongTagView,
    SongView,
    Tag,
)

router = APIRouter(prefix="/api/v1/songs", tags=["song edit"])

type SongField = Literal[
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
]


class SongPatch(BaseModel):
    """See `AlbumPatch`."""

    model_config = ConfigDict(extra="forbid")

    base_name: str | None = None
    variant: str | None = None
    release_date: date | None = None
    release_date_precision: DatePrecision | None = None
    cover_url: str | None = None
    cover_thumbnail_url: str | None = None
    cover_primary_color: str | None = None
    cover_secondary_color: str | None = None
    description: str | None = None
    genre_id: int | None = None
    reset: list[SongField] = Field(default_factory=list)


@router.patch("/{song_id}")
async def patch_song(
    song_id: int, body: SongPatch, session: SessionDep, user: EditorDep
) -> SongDetail:
    await get_or_404(session, SongView, song_id)
    await override_fields(
        session,
        entity_type="song",
        entity_id=song_id,
        user_id=user.id,
        view=SongView,
        edit=SongEdit,
        key="song_id",
        fields=SONG_FIELDS,
        values=body.model_dump(exclude_unset=True, exclude={"reset"}),
        reset=body.reset,
    )
    return await get_song(song_id, session, user)


class SongArtistsIn(BaseModel):
    """The artists of the song, in the order they are shown: the main ones, then the guests."""

    artists: list[int]
    featured: list[int] = Field(default_factory=list)


@router.put("/{song_id}/artists")
async def put_song_artists(
    song_id: int, body: SongArtistsIn, session: SessionDep, user: EditorDep
) -> SongDetail:
    """Makes the artists of the song what the lists say. One of Genius that is not in them is hidden, not deleted
    (the import cannot bring it back); one that Genius does not have is added."""
    await get_or_404(session, SongView, song_id)
    before = [
        [row.artist_id, row.role.value]
        for row in await session.execute(
            select(SongArtistView.artist_id, SongArtistView.role)
            .where(SongArtistView.song_id == song_id)
            .order_by(SongArtistView.role, SongArtistView.position.nulls_last())
        )
    ]
    existing = {
        (row.artist_id, row.role)
        for row in await session.scalars(select(SongArtist).where(SongArtist.song_id == song_id))
    }
    wanted: set[tuple[int, SongArtistRole]] = set()
    async with refuse_unknown(session, "An artist of the song is not known"):
        for role, ids in (
            (SongArtistRole.PRIMARY, body.artists),
            (SongArtistRole.FEATURED, body.featured),
        ):
            for position, artist_id in enumerate(ids, start=1):
                wanted.add((artist_id, role))
                if (artist_id, role) not in existing:
                    session.add(
                        SongArtist(
                            song_id=song_id, artist_id=artist_id, role=role, position=position
                        )
                    )
                    await session.flush()
                key = {"song_id": song_id, "artist_id": artist_id, "role": role}
                await put_edit(session, SongArtistEdit, key, removed=False, position=position)
        for artist_id, role in existing - wanted:
            key = {"song_id": song_id, "artist_id": artist_id, "role": role}
            await put_edit(session, SongArtistEdit, key, removed=True)
        await session.flush()
    after = [[a, SongArtistRole.PRIMARY.value] for a in body.artists] + [
        [a, SongArtistRole.FEATURED.value] for a in body.featured
    ]
    await log_revision(
        session, "song", song_id, user.id, {"artists": [before, after]} if before != after else {}
    )
    await session.commit()
    return await get_song(song_id, session, user)


@router.put("/{song_id}/tags")
async def put_song_tags(
    song_id: int, body: list[str], session: SessionDep, user: EditorDep
) -> SongDetail:
    """Makes the tags of the song the names in the list (a name that is not a tag yet is made one)."""
    await get_or_404(session, SongView, song_id)
    before = sorted(
        await session.scalars(
            select(Tag.name)
            .join(SongTagView, SongTagView.tag_id == Tag.id)
            .where(SongTagView.song_id == song_id)
        )
    )
    wanted: set[int] = set()
    for name in dict.fromkeys(body):
        tag = await session.scalar(select(Tag).where(Tag.name == name).order_by(Tag.id))
        if tag is None:
            tag = Tag(name=name, base_name=name)
            session.add(tag)
            await session.flush()
        wanted.add(tag.id)
    existing = set(await session.scalars(select(SongTag.tag_id).where(SongTag.song_id == song_id)))
    session.add_all(SongTag(song_id=song_id, tag_id=tag_id) for tag_id in wanted - existing)
    await session.flush()
    for tag_id in existing | wanted:
        key = {"song_id": song_id, "tag_id": tag_id}
        await put_edit(session, SongTagEdit, key, removed=tag_id not in wanted)
    after = sorted(dict.fromkeys(body))
    await log_revision(
        session, "song", song_id, user.id, {"tags": [before, after]} if before != after else {}
    )
    await session.commit()
    return await get_song(song_id, session, user)
