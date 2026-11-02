"""Everything the album page shows: the album with its summaries, the tracklist and the raw response.

The server gives facts and a stable order; how a track number or a relation is worded is the client's
decision.
"""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import ColumnElement, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.names import artist_name
from music_backend.api.queries import (
    album_cards,
    artist_ref_columns,
    count,
    cover_is_explicit,
    description_tree,
    edited_fields,
    get_or_404,
    imports_and_history,
    producers_of,
    raw_of,
)
from music_backend.api.schemas import (
    ArtistAlbum,
    ArtistName,
    ArtistRef,
    ChangeOut,
    DomNode,
    DomRef,
    ImportRef,
)
from music_backend.enums import (
    AlbumRelationType,
    DatePrecision,
    ImportKind,
    ImportState,
    NicknameScope,
    SongArtistRole,
)
from music_backend.models import (
    AlbumArtistView,
    AlbumCoverArt,
    AlbumCreditView,
    AlbumEdit,
    AlbumRelationship,
    AlbumTrackView,
    AlbumView,
    Artist,
    ArtistView,
    CreditRole,
    GeniusResponse,
    Genre,
    SongArtistView,
    SongCreditView,
    SongTagView,
    SongVideo,
    SongView,
    Tag,
)

router = APIRouter(prefix="/api/v1/albums", tags=["album page"])


class CoverOut(BaseModel):
    id: int
    image_url: str
    thumbnail_image_url: str
    genius_url: str
    explicit: bool


class CreditArtist(BaseModel):
    artist: ArtistRef
    tracks: (
        int | None
    )  # tracks of this album with the credit; null for a credit of the album itself


class CreditGroup(BaseModel):
    role: str
    from_album: (
        bool  # given for the album as a whole (Label, Copyright, ...), not summed up from its songs
    )
    artists: list[CreditArtist]


class RelatedAlbums(BaseModel):
    """`inverse` false: this album *is* the type of the others ("deluxe edition of"); true: the others
    are the type of this one ("deluxe editions")."""

    type: AlbumRelationType
    inverse: bool
    albums: list[ArtistAlbum]


class AlbumCore(BaseModel):
    id: int
    genius_id: int | None
    name: str
    base_name: str
    variant: str | None
    disambiguator: str | None
    album_type: str | None
    import_state: ImportState
    language: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None
    is_released: bool | None
    description: str | None
    genius_url: str | None
    cover_url: str | None
    cover_thumbnail_url: str | None
    cover_primary_color: str | None
    cover_secondary_color: str | None
    created_at: datetime
    updated_at: datetime


class AlbumDetail(AlbumCore):
    description_dom: DomNode | None  # the description as Genius writes it, see `DomNode`
    description_refs: list[DomRef]
    artists: list[ArtistRef]
    covers: list[CoverOut]  # every cover Genius knows; the main one is `cover_url`
    edited: list[str]  # the fields that were set by hand, see `AlbumPatch`
    tracks_count: int
    discs_count: int
    genres: list[str]  # of its songs, the most common first
    tags: list[
        str
    ]  # the tags of its songs that are not a genre of the album, the most common first
    credits: list[CreditGroup]
    related: list[RelatedAlbums]
    imports: list[ImportRef]
    history: list[ChangeOut]


class AlbumVideoOut(BaseModel):
    song_id: int
    song_name: str
    url: str
    start_seconds: int | None
    explicit: bool
    official: bool
    release_date: date | None  # of the song, with the precision Genius has
    release_date_precision: DatePrecision | None


class AlbumTrackOut(BaseModel):
    id: int  # of the placement
    song_id: int
    disc_number: int | None
    position: int | None
    base_name: str
    variant: str | None
    genius_url: str | None
    cover_thumbnail_url: str | None
    import_state: ImportState
    explicit: bool | None
    view_count: int | None
    is_primary: bool | None  # the song's primary album is this one
    artists: list[ArtistName]
    featured: list[ArtistName]
    producers: list[ArtistName]  # credited as "Producer", in the order they were imported


async def _related(session: AsyncSession, album_id: int) -> list[RelatedAlbums]:
    rows = (
        await session.execute(
            select(AlbumRelationship).where(
                (AlbumRelationship.album_id == album_id)
                | (AlbumRelationship.related_album_id == album_id)
            )
        )
    ).scalars()
    found: dict[tuple[AlbumRelationType, bool], list[int]] = {}
    for row in rows:
        inverse = row.related_album_id == album_id
        other = row.album_id if inverse else row.related_album_id
        found.setdefault((row.type, inverse), []).append(other)
    cards = await album_cards(session, [i for ids in found.values() for i in ids])
    return [
        RelatedAlbums(
            type=kind,
            inverse=inverse,
            albums=sorted(
                (cards[i] for i in ids),
                key=lambda a: (a.release_date is None, a.release_date or date.min, a.id),
                reverse=True,
            ),
        )
        for (kind, inverse), ids in sorted(found.items())
    ]


async def _genres(session: AsyncSession, album_id: int) -> list[str]:
    songs = func.count()
    rows = await session.scalars(
        select(Genre.name)
        .join(SongView, SongView.genre_id == Genre.id)
        .join(AlbumTrackView, AlbumTrackView.song_id == SongView.id)
        .where(AlbumTrackView.album_id == album_id)
        .group_by(Genre.name)
        .order_by(songs.desc(), Genre.name)
        .limit(5)
    )
    return list(rows)


async def _tags(session: AsyncSession, album_id: int, genres: list[str]) -> list[str]:
    songs = func.count()
    rows = await session.scalars(
        select(Tag.name)
        .join(SongTagView, SongTagView.tag_id == Tag.id)
        .join(AlbumTrackView, AlbumTrackView.song_id == SongTagView.song_id)
        .where(AlbumTrackView.album_id == album_id, Tag.name.not_in(genres))
        .group_by(Tag.name)
        .order_by(songs.desc(), Tag.name)
        .limit(8)
    )
    return list(rows)


async def _credits(
    session: AsyncSession, album_id: int, released: date | None
) -> list[CreditGroup]:
    """The credits of the album itself, then the credits of its songs summed up by role. Everybody has the name of the
    day the album came out."""
    name = artist_name(ArtistView.id, on=released, album_id=album_id, scope=NicknameScope.CREDIT)
    own = await session.execute(
        select(*artist_ref_columns(name), CreditRole.name.label("role"))
        .select_from(AlbumCreditView)
        .join(ArtistView, ArtistView.id == AlbumCreditView.artist_id)
        .join(CreditRole, CreditRole.id == AlbumCreditView.role_id)
        .where(AlbumCreditView.album_id == album_id)
    )
    songs = await session.execute(
        select(
            *artist_ref_columns(name),
            CreditRole.name.label("role"),
            func.count(distinct(AlbumTrackView.song_id)).label("tracks"),
        )
        .select_from(AlbumTrackView)
        .join(SongCreditView, SongCreditView.song_id == AlbumTrackView.song_id)
        .join(ArtistView, ArtistView.id == SongCreditView.artist_id)
        .join(CreditRole, CreditRole.id == SongCreditView.role_id)
        .where(AlbumTrackView.album_id == album_id)
        .group_by(*ArtistView.__table__.c, CreditRole.name)
    )
    # One group per role: the same role can be given for the album and for its songs (the Label of both).
    groups: dict[str, dict[int, CreditArtist]] = {}
    from_album: set[str] = set()
    for row in own:
        from_album.add(row.role)
        artist = ArtistRef.model_validate(row, from_attributes=True)
        groups.setdefault(row.role, {})[artist.id] = CreditArtist(artist=artist, tracks=None)
    for row in songs:
        artist = ArtistRef.model_validate(row, from_attributes=True)
        groups.setdefault(row.role, {})[artist.id] = CreditArtist(artist=artist, tracks=row.tracks)
    ordered = sorted(groups.items(), key=lambda g: (g[0] not in from_album, -len(g[1]), g[0]))
    return [
        CreditGroup(
            role=role,
            from_album=role in from_album,
            artists=sorted(
                members.values(),
                key=lambda c: (-(c.tracks or 0), c.artist.base_name.lower()),
            ),
        )
        for role, members in ordered
    ]


@router.get("/{album_id}")
async def get_album(album_id: int, session: SessionDep, _: UserDep) -> AlbumDetail:
    album = await get_or_404(session, AlbumView, album_id)
    name = artist_name(ArtistView.id, on=album.release_date, album_id=album_id)
    artists = await session.execute(
        select(*artist_ref_columns(name))
        .join(AlbumArtistView, AlbumArtistView.artist_id == ArtistView.id)
        .where(AlbumArtistView.album_id == album_id)
        .order_by(AlbumArtistView.position.nulls_last(), name)
    )
    covers = await session.scalars(
        select(AlbumCoverArt)
        .where(AlbumCoverArt.album_id == album_id)
        .order_by(AlbumCoverArt.position)
    )
    tracks = select(AlbumTrackView).where(AlbumTrackView.album_id == album_id)
    discs = select(func.coalesce(AlbumTrackView.disc_number, 1)).where(
        AlbumTrackView.album_id == album_id
    )
    dom, refs = await description_tree(
        session,
        "album",
        album_id,
        ("description_annotation", "annotations", 0, "body", "dom"),
    )
    genres = await _genres(session, album_id)
    edited = await edited_fields(session, AlbumEdit, album_id)
    if "description" in edited:  # a text written by hand has no tree of Genius
        dom, refs = None, []
    imports, history = await imports_and_history(
        session, "album", album_id, album.genius_id, [ImportKind.ALBUM]
    )
    return AlbumDetail(
        **AlbumCore.model_validate(album, from_attributes=True).model_dump(),
        description_dom=dom,
        description_refs=refs,
        artists=[ArtistRef.model_validate(a, from_attributes=True) for a in artists],
        covers=[CoverOut.model_validate(c, from_attributes=True) for c in covers],
        edited=edited,
        tracks_count=await count(session, tracks),
        discs_count=await count(session, discs.distinct()),
        genres=genres,
        tags=await _tags(session, album_id, genres),
        credits=await _credits(session, album_id, album.release_date),
        related=await _related(session, album_id),
        imports=imports,
        history=history,
    )


class AlbumNeighbor(BaseModel):
    id: int
    base_name: str
    variant: str | None
    cover_thumbnail_url: str | None
    cover_explicit: bool


class AlbumNeighbors(BaseModel):
    previous: AlbumNeighbor | None
    next: AlbumNeighbor | None


@router.get("/{album_id}/neighbors")
async def get_album_neighbors(
    album_id: int, session: SessionDep, _: UserDep, artist_id: int | None = None
) -> AlbumNeighbors:
    """The albums of an artist just before and just after this one by the date (an album with no date comes last, then
    by id). The artist is the one asked for, else the first one of the album."""
    album = await get_or_404(session, AlbumView, album_id)
    if artist_id is None:
        artist_id = await session.scalar(
            select(AlbumArtistView.artist_id)
            .where(AlbumArtistView.album_id == album_id)
            .order_by(AlbumArtistView.position.nulls_last(), AlbumArtistView.artist_id)
            .limit(1)
        )
    if artist_id is None:
        return AlbumNeighbors(previous=None, next=None)

    own = select(AlbumArtistView.album_id).where(AlbumArtistView.artist_id == artist_id)
    day, here = album.release_date, AlbumView.release_date
    if day is None:
        before = here.is_not(None) | (AlbumView.id < album_id)
        after = here.is_(None) & (AlbumView.id > album_id)
    else:
        before = (here < day) | ((here == day) & (AlbumView.id < album_id))
        after = here.is_(None) | (here > day) | ((here == day) & (AlbumView.id > album_id))

    async def nearest(condition: ColumnElement[bool], first: bool) -> AlbumNeighbor | None:
        order = (
            (AlbumView.release_date.desc().nulls_first(), AlbumView.id.desc())
            if first
            else (AlbumView.release_date.asc().nulls_last(), AlbumView.id.asc())
        )
        found = (
            await session.execute(
                select(
                    AlbumView.id,
                    AlbumView.base_name,
                    AlbumView.variant,
                    AlbumView.cover_thumbnail_url,
                    cover_is_explicit().label("cover_explicit"),
                )
                .where(AlbumView.id.in_(own), AlbumView.id != album_id, condition)
                .order_by(*order)
                .limit(1)
            )
        ).first()
        return AlbumNeighbor.model_validate(found, from_attributes=True) if found else None

    return AlbumNeighbors(previous=await nearest(before, True), next=await nearest(after, False))


@router.get("/{album_id}/tracks")
async def list_album_tracks(album_id: int, session: SessionDep, _: UserDep) -> list[AlbumTrackOut]:
    """The tracklist in order: by disc, then by position (when Genius has none, by order of arrival)."""
    album = await get_or_404(session, AlbumView, album_id)
    rows = (
        await session.execute(
            select(AlbumTrackView, SongView)
            .join(SongView, SongView.id == AlbumTrackView.song_id)
            .where(AlbumTrackView.album_id == album_id)
            .order_by(
                func.coalesce(AlbumTrackView.disc_number, 1),
                AlbumTrackView.position.nulls_last(),
                AlbumTrackView.sort_order.nulls_last(),
                AlbumTrackView.id,
            )
        )
    ).all()
    # The names of the day of the song (of the album, for a song with no date of its own); an alter ego of the album counts.
    credited_name = artist_name(
        Artist.id,
        on=func.coalesce(SongView.release_date, album.release_date),
        album_id=album_id,
        song_id=SongArtistView.song_id,
    )
    credited = await session.execute(
        select(SongArtistView.song_id, SongArtistView.role, Artist.id, credited_name)
        .join(Artist, Artist.id == SongArtistView.artist_id)
        .join(SongView, SongView.id == SongArtistView.song_id)
        .where(SongArtistView.song_id.in_([song.id for _, song in rows]))
        .order_by(SongArtistView.position.nulls_last(), credited_name)
    )
    producers = await producers_of(session, [song.id for _, song in rows], album_id)
    primary: dict[int, list[ArtistName]] = {}
    featured: dict[int, list[ArtistName]] = {}
    for song_id, role, artist_id, name in credited:
        target = primary if role is SongArtistRole.PRIMARY else featured
        target.setdefault(song_id, []).append(ArtistName(id=artist_id, base_name=name))
    return [
        AlbumTrackOut(
            id=track.id,
            song_id=song.id,
            disc_number=track.disc_number,
            position=track.position,
            base_name=song.base_name,
            variant=song.variant,
            genius_url=song.genius_url,
            cover_thumbnail_url=song.cover_thumbnail_url,
            import_state=song.import_state,
            explicit=song.explicit,
            view_count=song.view_count,
            is_primary=track.is_primary,
            artists=primary.get(song.id, []),
            featured=featured.get(song.id, []),
            producers=producers.get(song.id, []),
        )
        for track, song in rows
    ]


@router.get("/{album_id}/videos")
async def list_album_videos(album_id: int, session: SessionDep, _: UserDep) -> list[AlbumVideoOut]:
    """The clips Genius links from the songs of the album, in the order of the tracklist, each address once."""
    await get_or_404(session, AlbumView, album_id)
    rows = await session.execute(
        select(SongVideo, SongView)
        .join(SongView, SongView.id == SongVideo.song_id)
        .join(AlbumTrackView, AlbumTrackView.song_id == SongView.id)
        .where(AlbumTrackView.album_id == album_id)
        .order_by(
            func.coalesce(AlbumTrackView.disc_number, 1),
            AlbumTrackView.position.nulls_last(),
            AlbumTrackView.sort_order.nulls_last(),
            AlbumTrackView.id,
            SongVideo.id,
        )
    )
    videos: dict[str, AlbumVideoOut] = {}
    for link, song in rows:
        videos.setdefault(
            link.url,
            AlbumVideoOut(
                song_id=song.id,
                song_name=song.base_name,
                url=link.url,
                start_seconds=link.start_seconds,
                explicit=link.explicit,
                official=link.official,
                release_date=song.release_date,
                release_date_precision=song.release_date_precision,
            ),
        )
    return list(videos.values())


@router.get("/{album_id}/raw")
async def get_album_raw(album_id: int, session: SessionDep, _: UserDep) -> dict[str, Any] | None:
    """The untouched Genius response the album was last imported from (null for a stub)."""
    await get_or_404(session, AlbumView, album_id)
    return await session.scalar(select(GeniusResponse.raw).where(raw_of("album", album_id)))
