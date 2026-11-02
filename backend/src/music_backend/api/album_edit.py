"""Changing an album by hand: its fields, and its tracklist as a whole."""

from datetime import date
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from music_backend.api.album_page import AlbumDetail, AlbumTrackOut, get_album, list_album_tracks
from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.queries import get_or_404, refuse_unknown
from music_backend.editing import log_revision, override_fields, put_edit
from music_backend.enums import AlbumType, DatePrecision
from music_backend.models import (
    ALBUM_FIELDS,
    AlbumArtist,
    AlbumArtistEdit,
    AlbumArtistView,
    AlbumEdit,
    AlbumTrack,
    AlbumTrackEdit,
    AlbumTrackView,
    AlbumView,
)

router = APIRouter(prefix="/api/v1/albums", tags=["album edit"])

type AlbumField = Literal[
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
]


class AlbumPatch(BaseModel):
    """Only what is in the body is changed (a value may be null: a date taken away); `reset` puts fields back to what
    Genius has. The cover is four fields, set together."""

    model_config = ConfigDict(extra="forbid")

    base_name: str | None = None
    variant: str | None = None
    album_type: AlbumType | None = None
    is_released: bool | None = None
    release_date: date | None = None
    release_date_precision: DatePrecision | None = None
    cover_url: str | None = None
    cover_thumbnail_url: str | None = None
    cover_primary_color: str | None = None
    cover_secondary_color: str | None = None
    description: str | None = None
    reset: list[AlbumField] = Field(default_factory=list)


@router.patch("/{album_id}")
async def patch_album(
    album_id: int, body: AlbumPatch, session: SessionDep, user: EditorDep
) -> AlbumDetail:
    await get_or_404(session, AlbumView, album_id)
    await override_fields(
        session,
        entity_type="album",
        entity_id=album_id,
        user_id=user.id,
        view=AlbumView,
        edit=AlbumEdit,
        key="album_id",
        fields=ALBUM_FIELDS,
        values=body.model_dump(exclude_unset=True, exclude={"reset"}),
        reset=body.reset,
    )
    return await get_album(album_id, session, user)


class TrackIn(BaseModel):
    song_id: int
    disc_number: int | None = None


@router.put("/{album_id}/artists")
async def put_album_artists(
    album_id: int, body: list[int], session: SessionDep, user: EditorDep
) -> list[int]:
    """Makes the artists of the album what the list says, in its order. One of Genius that is not in it is hidden, not
    deleted (the import cannot bring it back); one that Genius does not have is added."""
    await get_or_404(session, AlbumView, album_id)
    before = list(
        await session.scalars(
            select(AlbumArtistView.artist_id)
            .where(AlbumArtistView.album_id == album_id)
            .order_by(AlbumArtistView.position.nulls_last())
        )
    )
    existing = set(
        await session.scalars(select(AlbumArtist.artist_id).where(AlbumArtist.album_id == album_id))
    )
    async with refuse_unknown(session, "An artist of the album is not known"):
        for position, artist_id in enumerate(body, start=1):
            if artist_id not in existing:
                session.add(AlbumArtist(album_id=album_id, artist_id=artist_id, position=position))
                await session.flush()
            key = {"album_id": album_id, "artist_id": artist_id}
            await put_edit(session, AlbumArtistEdit, key, removed=False, position=position)
        for artist_id in existing - set(body):
            key = {"album_id": album_id, "artist_id": artist_id}
            await put_edit(session, AlbumArtistEdit, key, removed=True)
        await session.flush()
    await log_revision(
        session, "album", album_id, user.id, {"artists": [before, body]} if before != body else {}
    )
    await session.commit()
    return body


@router.put("/{album_id}/tracks")
async def put_tracks(
    album_id: int, body: list[TrackIn], session: SessionDep, user: EditorDep
) -> list[AlbumTrackOut]:
    """Makes the tracklist what the list says, in its order. A track of Genius that is not in it is hidden, not
    deleted (the import cannot bring it back); a song that Genius does not put on the album is added."""
    await get_or_404(session, AlbumView, album_id)
    before = list(
        await session.scalars(
            select(AlbumTrackView.song_id).where(AlbumTrackView.album_id == album_id)
        )
    )
    rows: dict[int, AlbumTrack] = {}
    for row in await session.scalars(
        select(AlbumTrack).where(AlbumTrack.album_id == album_id).order_by(AlbumTrack.id)
    ):
        rows.setdefault(row.song_id, row)
    kept: set[int] = set()
    numbers: dict[int, int] = {}  # the last number on each disc
    async with refuse_unknown(session, "A song of the list is not known"):
        for item in body:
            disc = item.disc_number or 1
            numbers[disc] = numbers.get(disc, 0) + 1
            track = rows.get(item.song_id) or AlbumTrack(album_id=album_id, song_id=item.song_id)
            if track.id is None:
                session.add(track)
                await session.flush()
            kept.add(track.id)
            key = {"album_track_id": track.id}
            await put_edit(
                session,
                AlbumTrackEdit,
                key,
                removed=False,
                disc_number=item.disc_number,
                position=numbers[disc],
            )
        hidden = select(AlbumTrack.id).where(
            AlbumTrack.album_id == album_id, AlbumTrack.id.not_in(kept)
        )
        for track_id in await session.scalars(hidden):
            await put_edit(session, AlbumTrackEdit, {"album_track_id": track_id}, removed=True)
        await session.flush()
    after = [item.song_id for item in body]
    await log_revision(
        session,
        "album",
        album_id,
        user.id,
        {"tracklist": [before, after]} if before != after else {},
    )
    await session.commit()
    return await list_album_tracks(album_id, session, user)
