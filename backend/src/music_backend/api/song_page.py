"""Everything the song page shows: the song with its artists, credits, albums, relations and clips.

Like the album page, the server gives facts and a stable order. Lyrics are not here: the API has none and
they are never scraped.
"""

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.names import artist_name
from music_backend.api.queries import (
    album_cards,
    artist_ref_columns,
    description_tree,
    edited_fields,
    get_or_404,
    imports_and_history,
    raw_of,
)
from music_backend.api.schemas import ArtistAlbum, ArtistRef, ChangeOut, DomNode, DomRef, ImportRef
from music_backend.enums import (
    DatePrecision,
    ImportKind,
    ImportState,
    NicknameScope,
    SongArtistRole,
    SongRelationType,
)
from music_backend.lyrics import parse_lyrics
from music_backend.models import (
    AlbumTrackView,
    Artist,
    ArtistView,
    CreditRole,
    GeniusResponse,
    Genre,
    SongArtistView,
    SongAudio,
    SongCreditView,
    SongEdit,
    SongRelationship,
    SongTagView,
    SongVideo,
    SongView,
    Tag,
)

router = APIRouter(prefix="/api/v1/songs", tags=["song page"])


class SongCard(BaseModel):
    """A song in a list of related songs."""

    id: int
    genius_id: int | None
    base_name: str
    variant: str | None
    cover_thumbnail_url: str | None
    genius_url: str | None
    import_state: ImportState
    artists: list[str]  # the primary artists, in the order Genius lists them


class RelatedSongs(BaseModel):
    """`inverse` false: this song *is* the type of the others ("remix of"); true: the others are the
    type of this one ("remixes")."""

    type: SongRelationType
    inverse: bool
    songs: list[SongCard]


class SongCreditGroup(BaseModel):
    role: str
    artists: list[ArtistRef]


class SongPlacement(BaseModel):
    """The song on one album."""

    album: ArtistAlbum
    disc_number: int | None
    position: int | None
    is_primary: bool | None  # the song's primary album


class SongVideoOut(BaseModel):
    url: str
    start_seconds: int | None
    explicit: bool
    official: bool


class SongAudioOut(BaseModel):
    provider: str
    url: str


class StanzaOut(BaseModel):
    title: str | None
    lines: list[str]


class LyricsOut(BaseModel):
    stanzas: list[StanzaOut]


class SongDetail(BaseModel):
    id: int
    genius_id: int | None
    name: str
    base_name: str
    variant: str | None
    disambiguator: str | None
    import_state: ImportState
    language: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None
    description: str | None
    description_dom: DomNode | None  # the description as Genius writes it, see `DomNode`
    description_refs: list[DomRef]
    recording_location: str | None
    explicit: bool | None
    instrumental: bool | None
    lyrics_state: str | None  # Genius value: complete, incomplete, unreleased
    genius_url: str | None
    cover_url: str | None
    cover_thumbnail_url: str | None
    cover_primary_color: str | None
    cover_secondary_color: str | None
    view_count: int | None
    genre: str | None
    tags: list[str]
    artists: list[ArtistRef]
    featured: list[ArtistRef]
    credits: list[SongCreditGroup]
    albums: list[SongPlacement]
    related: list[RelatedSongs]
    videos: list[SongVideoOut]
    audios: list[SongAudioOut]
    created_at: datetime
    updated_at: datetime
    imports: list[ImportRef]
    history: list[ChangeOut]
    edited: list[str]  # the fields that were set by hand, see `SongPatch`


async def _artists(
    session: AsyncSession, song_id: int, role: SongArtistRole, released: date | None
) -> list[ArtistRef]:
    """The artists with the names they had on the day the song came out."""
    name = artist_name(ArtistView.id, on=released, song_id=song_id)
    rows = await session.execute(
        select(*artist_ref_columns(name))
        .join(SongArtistView, SongArtistView.artist_id == ArtistView.id)
        .where(SongArtistView.song_id == song_id, SongArtistView.role == role)
        .order_by(SongArtistView.position.nulls_last(), name)
    )
    return [ArtistRef.model_validate(row, from_attributes=True) for row in rows]


async def _credits(
    session: AsyncSession, song_id: int, released: date | None
) -> list[SongCreditGroup]:
    name = artist_name(ArtistView.id, on=released, song_id=song_id, scope=NicknameScope.CREDIT)
    rows = await session.execute(
        select(*artist_ref_columns(name), CreditRole.name.label("role"))
        .select_from(SongCreditView)
        .join(ArtistView, ArtistView.id == SongCreditView.artist_id)
        .join(CreditRole, CreditRole.id == SongCreditView.role_id)
        .where(SongCreditView.song_id == song_id)
        .order_by(SongCreditView.id)
    )
    groups: dict[str, list[ArtistRef]] = {}
    for row in rows:
        groups.setdefault(row.role, []).append(ArtistRef.model_validate(row, from_attributes=True))
    return [SongCreditGroup(role=role, artists=artists) for role, artists in sorted(groups.items())]


async def _albums(session: AsyncSession, song_id: int) -> list[SongPlacement]:
    placed = (
        await session.scalars(
            select(AlbumTrackView)
            .where(AlbumTrackView.song_id == song_id)
            .order_by(AlbumTrackView.is_primary.desc().nulls_last(), AlbumTrackView.id)
        )
    ).all()
    cards = await album_cards(session, [track.album_id for track in placed])
    return [
        SongPlacement(
            album=cards[track.album_id],
            disc_number=track.disc_number,
            position=track.position,
            is_primary=track.is_primary,
        )
        for track in placed
    ]


async def _cards(session: AsyncSession, ids: list[int]) -> dict[int, SongCard]:
    named = artist_name(Artist.id, on=SongView.release_date, song_id=SongView.id)
    artists = (
        select(func.array_agg(aggregate_order_by(named, SongArtistView.position)))
        .select_from(SongArtistView)
        .join(Artist, Artist.id == SongArtistView.artist_id)
        .where(SongArtistView.song_id == SongView.id, SongArtistView.role == SongArtistRole.PRIMARY)
        .correlate(SongView)
        .scalar_subquery()
    )
    rows = await session.execute(
        select(
            SongView.id,
            SongView.genius_id,
            SongView.base_name,
            SongView.variant,
            SongView.cover_thumbnail_url,
            SongView.genius_url,
            SongView.import_state,
            func.coalesce(artists, []).label("artists"),
        ).where(SongView.id.in_(ids))
    )
    return {row.id: SongCard(**row._mapping) for row in rows}


async def _related(session: AsyncSession, song_id: int) -> list[RelatedSongs]:
    rows = (
        await session.execute(
            select(SongRelationship).where(
                (SongRelationship.song_id == song_id)
                | (SongRelationship.related_song_id == song_id)
            )
        )
    ).scalars()
    found: dict[tuple[SongRelationType, bool], list[int]] = {}
    for row in rows:
        inverse = row.related_song_id == song_id
        found.setdefault((row.type, inverse), []).append(
            row.song_id if inverse else row.related_song_id
        )
    cards = await _cards(session, [i for ids in found.values() for i in ids])
    return [
        RelatedSongs(type=kind, inverse=inverse, songs=[cards[i] for i in ids])
        for (kind, inverse), ids in sorted(found.items())
    ]


@router.get("/search")
async def search_songs(
    q: str, session: SessionDep, _: UserDep, limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[SongCard]:
    """The songs of the library whose name has `q` in it, for picking a song to put on an album."""
    ids = await session.scalars(
        select(SongView.id)
        .where(SongView.base_name.ilike(f"%{q}%"))
        .order_by(func.lower(SongView.base_name), SongView.id)
        .limit(limit)
    )
    order = list(ids)
    cards = await _cards(session, order)
    return [cards[i] for i in order]


@router.get("/{song_id}")
async def get_song(song_id: int, session: SessionDep, _: UserDep) -> SongDetail:
    song = await get_or_404(session, SongView, song_id)
    dom, refs = await description_tree(session, "song", song_id, ("description", "dom"))
    edited = await edited_fields(session, SongEdit, song_id)
    if "description" in edited:  # a text written by hand has no tree of Genius
        dom, refs = None, []
    imports, history = await imports_and_history(
        session, "song", song_id, song.genius_id, [ImportKind.SONG]
    )
    genre = (
        await session.scalar(select(Genre.name).where(Genre.id == song.genre_id))
        if song.genre_id
        else None
    )
    tags = await session.scalars(
        select(Tag.name)
        .join(SongTagView, SongTagView.tag_id == Tag.id)
        .where(SongTagView.song_id == song_id)
        .order_by(Tag.name)
    )
    videos = await session.scalars(
        select(SongVideo).where(SongVideo.song_id == song_id).order_by(SongVideo.id)
    )
    audios = await session.scalars(
        select(SongAudio).where(SongAudio.song_id == song_id).order_by(SongAudio.id)
    )
    return SongDetail(
        id=song.id,
        genius_id=song.genius_id,
        name=song.name,
        base_name=song.base_name,
        variant=song.variant,
        disambiguator=song.disambiguator,
        import_state=song.import_state,
        language=song.language,
        release_date=song.release_date,
        release_date_precision=song.release_date_precision,
        description=song.description,
        description_dom=dom,
        description_refs=refs,
        recording_location=song.recording_location,
        explicit=song.explicit,
        instrumental=song.instrumental,
        lyrics_state=song.lyrics_state,
        genius_url=song.genius_url,
        cover_url=song.cover_url,
        cover_thumbnail_url=song.cover_thumbnail_url,
        cover_primary_color=song.cover_primary_color,
        cover_secondary_color=song.cover_secondary_color,
        view_count=song.view_count,
        genre=genre,
        tags=list(tags),
        artists=await _artists(session, song_id, SongArtistRole.PRIMARY, song.release_date),
        featured=await _artists(session, song_id, SongArtistRole.FEATURED, song.release_date),
        credits=await _credits(session, song_id, song.release_date),
        albums=await _albums(session, song_id),
        related=await _related(session, song_id),
        videos=[SongVideoOut.model_validate(v, from_attributes=True) for v in videos],
        audios=[SongAudioOut.model_validate(a, from_attributes=True) for a in audios],
        created_at=song.created_at,
        updated_at=song.updated_at,
        imports=imports,
        history=history,
        edited=edited,
    )


@router.get("/{song_id}/raw")
async def get_song_raw(song_id: int, session: SessionDep, _: UserDep) -> dict[str, Any] | None:
    """The untouched Genius response the song was last imported from (null for a stub)."""
    await get_or_404(session, SongView, song_id)
    return await session.scalar(select(GeniusResponse.raw).where(raw_of("song", song_id)))


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


# One text for every song that has no file of its own: for looking at a page with a text in it.
DEMO_LYRICS = "demo.txt"


@router.get("/{song_id}/lyrics")
async def get_song_lyrics(
    song_id: int, request: Request, session: SessionDep, _: UserDep
) -> LyricsOut | None:
    """The text of the song from `<lyrics_dir>/<genius id>.txt`, else `demo.txt`; null when there is neither."""
    song = await get_or_404(session, SongView, song_id)
    own = [] if song.genius_id is None else [f"{song.genius_id}.txt"]
    for name in [*own, DEMO_LYRICS]:
        text = await asyncio.to_thread(_read, request.app.state.settings.lyrics_dir / name)
        if text is not None:
            return LyricsOut(
                stanzas=[StanzaOut(title=s.title, lines=s.lines) for s in parse_lyrics(text)]
            )
    return None
