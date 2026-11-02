"""SQL pieces shared by the API modules: what a role is, the album card, ordering, counting."""

import re
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import (
    ColumnElement,
    Select,
    Subquery,
    and_,
    case,
    func,
    literal,
    select,
    union,
)
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import literal_column
from sqlalchemy.sql.elements import SQLColumnExpression, UnaryExpression

from music_backend.api.names import artist_name
from music_backend.api.schemas import (
    ArtistAlbum,
    ArtistName,
    ChangeOut,
    DomNode,
    DomRef,
    ImportRef,
)
from music_backend.enums import ImportKind, NicknameScope, SongArtistRole
from music_backend.models import (
    Album,
    AlbumArtistView,
    AlbumCoverArt,
    AlbumCreditView,
    AlbumTrackView,
    AlbumView,
    Artist,
    ArtistView,
    CreditRole,
    GeniusResponse,
    ImportJob,
    Revision,
    SongArtistView,
    SongCreditView,
    SongView,
)


async def get_or_404[M: DeclarativeBase](session: AsyncSession, model: type[M], pk: int) -> M:
    row = await session.get(model, pk)
    if row is None:
        raise HTTPException(404, f"{model.__name__.removesuffix('View')} not found")
    return row


@asynccontextmanager
async def refuse_unknown(session: AsyncSession, message: str) -> AsyncIterator[None]:
    """A write that names an artist, a song or a release that does not exist is a 422 and changes nothing."""
    try:
        yield
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(422, message) from error


def raw_of(entity_type: str, entity_id: int) -> ColumnElement[bool]:
    """The `where` for the Genius response of one entity (`select(GeniusResponse.raw).where(...)`)."""
    return and_(GeniusResponse.entity_type == entity_type, GeniusResponse.entity_id == entity_id)


_ENTITY_PATH = re.compile(r"^/(artists|albums)/(\d+)$")


def _api_paths(node: Mapping[str, Any] | str) -> Iterator[str]:
    if isinstance(node, str):
        return
    if node.get("data") and "api_path" in node["data"]:
        yield node["data"]["api_path"]
    for child in node.get("children") or []:
        yield from _api_paths(child)


async def _refs(
    session: AsyncSession,
    model: type[Artist] | type[Album],
    kind: Literal["artist", "album"],
    found: Mapping[str, tuple[str, int]],
) -> list[DomRef]:
    plural = f"{kind}s"
    wanted = {genius_id for name, genius_id in found.values() if name == plural}
    rows = await session.execute(
        select(model.genius_id, model.id).where(model.genius_id.in_(wanted))
    )
    return [DomRef(api_path=f"/{plural}/{genius_id}", kind=kind, id=pk) for genius_id, pk in rows]


async def description_tree(
    session: AsyncSession, entity_type: str, entity_id: int, path: tuple[str | int, ...]
) -> tuple[DomNode | None, list[DomRef]]:
    """The `dom` tree of a description, read from the stored Genius response (null for a stub), and what its
    links lead to among our pages."""
    raw = await session.scalar(
        select(GeniusResponse.raw[path]).where(raw_of(entity_type, entity_id))
    )
    if raw is None:
        return None, []
    found = {
        m.group(0): (m.group(1), int(m.group(2)))
        for p in _api_paths(raw)
        if (m := _ENTITY_PATH.match(p))
    }
    refs = [
        *await _refs(session, Artist, "artist", found),
        *await _refs(session, Album, "album", found),
    ]
    return DomNode.model_validate(raw), refs


async def edited_fields(session: AsyncSession, edit: Any, entity_id: int) -> list[str]:
    """The fields of the entity that were set by hand (named in `overridden` of its edit row)."""
    key = next(iter(edit.__table__.primary_key.columns))
    names = await session.scalar(select(edit.overridden).where(key == entity_id))
    return list(names or [])


async def count(session: AsyncSession, query: Select[Any]) -> int:
    return await session.scalar(select(func.count()).select_from(query.subquery())) or 0


async def imports_and_history(
    session: AsyncSession,
    entity_type: str,
    entity_id: int,
    genius_id: int | None,
    kinds: list[ImportKind],
) -> tuple[list[ImportRef], list[ChangeOut]]:
    """The jobs that imported this entity (latest first) and the last changes made to it."""
    # A manual entity has no genius_id, and no job has a NULL one: the list is empty then.
    jobs = await session.scalars(
        select(ImportJob)
        .where(ImportJob.genius_id == genius_id, ImportJob.kind.in_(kinds))
        .order_by(ImportJob.id.desc())
        .limit(10)
    )
    revisions = await session.scalars(
        select(Revision)
        .where(Revision.entity_type == entity_type, Revision.entity_id == entity_id)
        .order_by(Revision.id.desc())
        .limit(20)
    )
    return (
        [ImportRef.model_validate(job, from_attributes=True) for job in jobs],
        [ChangeOut.model_validate(row, from_attributes=True) for row in revisions],
    )


def ordering(
    keys: Mapping[str, tuple[SQLColumnExpression[Any], str]],
    sort: str,
    order: str | None,
) -> UnaryExpression[Any]:
    """`keys` maps a sort name to its column and its first direction; unknown values go last."""
    key, first = keys[sort]
    return (key.asc() if (order or first) == "asc" else key.desc()).nulls_last()


# A work is related to an artist by a *role*: Artist or Featured (the credit line) or the label of
# a credit (Writer, Producer, ...). One work can have several roles of the same artist.


def song_roles() -> Subquery:
    """(artist_id, song_id, role)"""
    return union(
        select(
            SongArtistView.artist_id,
            SongArtistView.song_id,
            case(
                (SongArtistView.role == SongArtistRole.PRIMARY, literal("Artist")),
                else_=literal("Featured"),
            ).label("role"),
        ),
        select(SongCreditView.artist_id, SongCreditView.song_id, CreditRole.name).join(
            CreditRole, CreditRole.id == SongCreditView.role_id
        ),
    ).subquery("song_role")


def album_roles() -> Subquery:
    """(artist_id, album_id, role)"""
    return union(
        select(
            AlbumArtistView.artist_id, AlbumArtistView.album_id, literal("Artist").label("role")
        ),
        select(AlbumCreditView.artist_id, AlbumCreditView.album_id, CreditRole.name).join(
            CreditRole, CreditRole.id == AlbumCreditView.role_id
        ),
    ).subquery("album_role")


def cover_is_explicit() -> ColumnElement[bool]:
    """Whether the cover the album shows is marked explicit: its cover art (the one with the same picture) says so."""
    return (
        select(AlbumCoverArt.id)
        .where(
            AlbumCoverArt.album_id == AlbumView.id,
            AlbumCoverArt.image_url == AlbumView.cover_url,
            AlbumCoverArt.explicit,
        )
        .correlate(AlbumView)
        .exists()
    )


def album_card_columns() -> list[Any]:
    """The columns of `ArtistAlbum` except `roles`."""
    track_count = (
        select(func.count())
        .where(AlbumTrackView.album_id == AlbumView.id)
        .correlate(AlbumView)
        .scalar_subquery()
    )
    # An album nobody is listed on (only credits) would give NULL, not an empty list.
    empty: ColumnElement[Any] = literal_column("'{}'")
    album_artist_name = artist_name(Artist.id, on=AlbumView.release_date, album_id=AlbumView.id)
    artists = (
        select(func.array_agg(aggregate_order_by(album_artist_name, AlbumArtistView.position)))
        .select_from(AlbumArtistView)
        .join(Artist, Artist.id == AlbumArtistView.artist_id)
        .where(AlbumArtistView.album_id == AlbumView.id)
        .correlate(AlbumView)
        .scalar_subquery()
    )
    labels = (
        select(func.array_agg(aggregate_order_by(album_artist_name, album_artist_name)))
        .select_from(AlbumCreditView)
        .join(CreditRole, CreditRole.id == AlbumCreditView.role_id)
        .join(Artist, Artist.id == AlbumCreditView.artist_id)
        .where(AlbumCreditView.album_id == AlbumView.id, CreditRole.name == "Label")
        .correlate(AlbumView)
        .scalar_subquery()
    )
    return [
        AlbumView.id,
        AlbumView.genius_id,
        AlbumView.base_name,
        AlbumView.variant,
        AlbumView.album_type,
        AlbumView.release_date,
        AlbumView.release_date_precision,
        AlbumView.is_released,
        AlbumView.cover_url,
        AlbumView.cover_thumbnail_url,
        cover_is_explicit().label("cover_explicit"),
        AlbumView.genius_url,
        track_count.label("tracks_count"),
        AlbumView.view_count,
        AlbumView.import_state,
        func.coalesce(artists, empty).label("artists"),
        func.coalesce(labels, empty).label("labels"),
    ]


def artist_ref_columns(name: ColumnElement[str]) -> list[Any]:
    """The columns of an `ArtistRef`, with the name the place wants (see `artist_name`)."""
    return [
        ArtistView.id,
        ArtistView.genius_id,
        name.label("base_name"),
        ArtistView.cover_url,
        ArtistView.artist_type,
        ArtistView.import_state,
    ]


async def producers_of(
    session: AsyncSession, song_ids: list[int], album_id: int | None = None
) -> dict[int, list[ArtistName]]:
    """The artists credited as "Producer" on each of the songs, in the order they were imported. Their names are the
    ones of the day of the song; `album_id` is the album they are shown on (an alter ego can be tied to it)."""
    name = artist_name(
        Artist.id,
        on=SongView.release_date,
        album_id=album_id,
        song_id=SongCreditView.song_id,
        scope=NicknameScope.CREDIT,
    )
    rows = await session.execute(
        select(SongCreditView.song_id, Artist.id, name)
        .join(Artist, Artist.id == SongCreditView.artist_id)
        .join(SongView, SongView.id == SongCreditView.song_id)
        .join(CreditRole, CreditRole.id == SongCreditView.role_id)
        .where(CreditRole.name == "Producer", SongCreditView.song_id.in_(song_ids))
        .order_by(SongCreditView.id)
    )
    producers: dict[int, list[ArtistName]] = {}
    for song_id, artist_id, producer in rows:
        producers.setdefault(song_id, []).append(ArtistName(id=artist_id, base_name=producer))
    return producers


async def album_cards(session: AsyncSession, ids: list[int]) -> dict[int, ArtistAlbum]:
    """The album card of each id (see `album_card_columns`), for a list that is not an artist's."""
    rows = await session.execute(select(*album_card_columns()).where(AlbumView.id.in_(ids)))
    # The roles are an artist's, and this is not an artist's list.
    return {row.id: ArtistAlbum(**row._mapping, roles=[]) for row in rows}
