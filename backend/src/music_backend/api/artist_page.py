"""Everything the artist page shows (a test feature, like the artist list: it stands on its own).

One call for the artist and its summaries, and paged calls for the two long lists. A song or an album
is related to an artist by a *role* (see `queries.py`).
"""

from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import Subquery, distinct, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.members import MemberOut, read_members
from music_backend.api.names import artist_name
from music_backend.api.nicknames import NicknameOut, read_nicknames
from music_backend.api.queries import (
    album_card_columns,
    album_roles,
    count,
    description_tree,
    edited_fields,
    get_or_404,
    imports_and_history,
    ordering,
    producers_of,
    raw_of,
    song_roles,
)
from music_backend.api.schemas import (
    ArtistAlbum,
    ArtistName,
    ChangeOut,
    DomNode,
    DomRef,
    ImportRef,
    Page,
    PagingDep,
    RolesQuery,
)
from music_backend.api.series import SeriesOut, read_series
from music_backend.bio import parse_bio
from music_backend.enums import ArtistType, DatePrecision, ImportKind, ImportState, SongArtistRole
from music_backend.models import (
    AlbumTrackView,
    AlbumView,
    Artist,
    ArtistAlias,
    ArtistAliasEdit,
    ArtistEdit,
    ArtistView,
    GeniusResponse,
    Genre,
    SongArtistView,
    SongVideo,
    SongView,
)

router = APIRouter(prefix="/api/v1/artists", tags=["artist page"])


class WorkRoleCount(BaseModel):
    role: str
    works: int


class GenreCount(BaseModel):
    genre: str
    songs: int


class PartialDateOut(BaseModel):
    date: date
    precision: DatePrecision


class ProfileLink(BaseModel):
    kind: str  # a key of Genius `social_links`: instagram, spotify, ...
    url: str


# Genius gives these as bare handles; the other keys are full URLs. Order is the order of the page.
_HANDLE_URLS = {
    "instagram": "https://instagram.com/{}",
    "x": "https://x.com/{}",
    "facebook": "https://facebook.com/{}",
    "tiktok": "https://tiktok.com/@{}",
    "snapchat": "https://snapchat.com/add/{}",
}
_LINK_ORDER = (
    "website", "spotify", "apple_music", "youtube", "soundcloud", "bandcamp", "tidal",
    "amazon_music", "shazam", *_HANDLE_URLS,
)  # fmt: skip


def _profile_links(social_links: dict[str, str]) -> list[ProfileLink]:
    # 503 of the stored artists have a key with an empty string: that is "no link".
    return [
        ProfileLink(kind=kind, url=_HANDLE_URLS.get(kind, "{}").format(social_links[kind]))
        for kind in _LINK_ORDER
        if social_links.get(kind)
    ]


class ArtistCore(BaseModel):
    id: int
    genius_id: int | None
    name: str
    base_name: str
    disambiguator: str | None
    artist_type: ArtistType | None
    import_state: ImportState
    description: str | None
    real_name: str | None  # read from the start of the description when imported, see `bio.py`
    genius_url: str | None
    cover_url: str | None
    is_verified: bool | None
    is_meme_verified: bool | None
    followers_count: int | None
    created_at: datetime
    updated_at: datetime


class ArtistDetail(ArtistCore):
    description_dom: DomNode | None  # the description as Genius writes it, see `DomNode`
    description_refs: list[DomRef]
    born: PartialDateOut | None
    died: PartialDateOut | None
    links: list[ProfileLink]
    aliases: list[str]
    nicknames: list[NicknameOut]
    edited: list[str]  # the fields that were set by hand, see `ArtistPatch`
    members: list[MemberOut]  # of a group
    groups: list[MemberOut]  # the artist belongs to
    songs_count: int
    albums_count: int
    song_roles: list[WorkRoleCount]
    album_roles: list[WorkRoleCount]
    genres: list[GenreCount]
    series: list[SeriesOut]  # the groups of albums that the user made, see `series.py`
    imports: list[ImportRef]
    history: list[ChangeOut]


class ArtistSong(BaseModel):
    id: int
    genius_id: int | None
    base_name: str
    variant: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None
    cover_thumbnail_url: str | None
    genius_url: str | None
    view_count: int | None
    genre: str | None
    album: str | None  # the primary album of the song
    import_state: ImportState
    roles: list[str]
    producers: list[ArtistName]  # credited as "Producer"


class ArtistVideo(BaseModel):
    song_id: int
    song_name: str
    variant: str | None
    url: str
    start_seconds: int | None
    explicit: bool
    official: bool
    release_date: date | None  # of the song
    release_date_precision: DatePrecision | None
    view_count: int | None  # of the song
    artists: list[str]  # the main artists of the song


def _of(roles: Subquery, artist_id: int, work: str) -> Subquery:
    """(work id, role) of one artist."""
    return select(roles.c[work], roles.c.role).where(roles.c.artist_id == artist_id).subquery()


async def _role_counts(session: AsyncSession, roles: Subquery, key: str) -> list[WorkRoleCount]:
    count = func.count(distinct(roles.c[key]))
    rows = await session.execute(
        select(roles.c.role, count).group_by(roles.c.role).order_by(count.desc(), roles.c.role)
    )
    return [WorkRoleCount(role=role, works=works) for role, works in rows]


@router.get("/{artist_id}")
async def get_artist(artist_id: int, session: SessionDep, _: UserDep) -> ArtistDetail:
    artist = await get_or_404(session, ArtistView, artist_id)
    songs = _of(song_roles(), artist_id, "song_id")
    albums = _of(album_roles(), artist_id, "album_id")
    aliases = await session.scalars(
        select(ArtistAlias.name)
        .outerjoin(ArtistAliasEdit, ArtistAliasEdit.alias_id == ArtistAlias.id)
        .where(ArtistAlias.artist_id == artist_id, ~func.coalesce(ArtistAliasEdit.removed, False))
        .order_by(ArtistAlias.name)
    )
    genre_count = func.count(distinct(SongView.id))
    genres = await session.execute(
        select(Genre.name, genre_count)
        .join(SongView, SongView.genre_id == Genre.id)
        .where(SongView.id.in_(select(songs.c.song_id)))
        .group_by(Genre.name)
        .order_by(genre_count.desc(), Genre.name)
        .limit(12)
    )
    imports, history = await imports_and_history(
        session, "artist", artist_id, artist.genius_id, [ImportKind.DISCOGRAPHY, ImportKind.ARTIST]
    )
    dom, refs = await description_tree(session, "artist", artist_id, ("description", "dom"))
    edited = await edited_fields(session, ArtistEdit, artist_id)
    if "description" in edited:  # a text written by hand has no tree of Genius
        dom, refs = None, []
    bio = parse_bio(artist.description)
    social_links = await session.scalar(
        select(GeniusResponse.raw["social_links"]).where(raw_of("artist", artist_id))
    )
    # The title of the page is the name the artist has now.
    core = ArtistCore.model_validate(artist, from_attributes=True).model_dump()
    core["base_name"] = await session.scalar(select(artist_name(artist_id)))
    return ArtistDetail(
        **core,
        description_dom=dom,
        description_refs=refs,
        born=PartialDateOut(date=bio.born[0], precision=bio.born[1]) if bio else None,
        died=PartialDateOut(date=bio.died[0], precision=bio.died[1]) if bio and bio.died else None,
        links=_profile_links(social_links) if social_links else [],
        aliases=list(aliases),
        nicknames=await read_nicknames(session, artist_id),
        edited=edited,
        members=await read_members(session, group_id=artist_id),
        groups=await read_members(session, member_id=artist_id),
        series=await read_series(session, artist_id),
        songs_count=await count(session, select(songs.c.song_id).distinct()),
        albums_count=await count(session, select(albums.c.album_id).distinct()),
        song_roles=await _role_counts(session, songs, "song_id"),
        album_roles=await _role_counts(session, albums, "album_id"),
        genres=[GenreCount(genre=name, songs=count_) for name, count_ in genres],
        imports=imports,
        history=history,
    )


@router.get("/{artist_id}/raw")
async def get_artist_raw(artist_id: int, session: SessionDep, _: UserDep) -> dict[str, Any] | None:
    """The untouched Genius response the artist was last imported from (null for a stub)."""
    await get_or_404(session, ArtistView, artist_id)
    return await session.scalar(select(GeniusResponse.raw).where(raw_of("artist", artist_id)))


@router.get("/{artist_id}/songs")
async def list_artist_songs(
    artist_id: int,
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    roles: RolesQuery,
    sort: Literal["name", "released", "views"] = "released",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistSong]:
    """Songs the artist is on in any role; with `roles` only those where it has every one of them."""
    await get_or_404(session, ArtistView, artist_id)
    role = _of(song_roles(), artist_id, "song_id")
    all_roles = array_agg(distinct(role.c.role))  # type: ignore[no-untyped-call]  # untyped upstream
    having = [all_roles.contains(roles)] if roles else []
    album = (
        select(AlbumView.base_name)
        .join(AlbumTrackView, AlbumTrackView.album_id == AlbumView.id)
        .where(AlbumTrackView.song_id == SongView.id)
        .order_by(AlbumTrackView.is_primary.desc().nulls_last(), AlbumTrackView.id)
        .limit(1)
        .correlate(SongView)
        .scalar_subquery()
    )
    name_key = func.lower(SongView.base_name)
    keys = {
        "name": (name_key, "asc"),
        "released": (SongView.release_date, "desc"),
        "views": (SongView.view_count, "desc"),
    }

    rows = await session.execute(
        select(
            SongView.id,
            SongView.genius_id,
            SongView.base_name,
            SongView.variant,
            SongView.release_date,
            SongView.release_date_precision,
            SongView.cover_thumbnail_url,
            SongView.genius_url,
            SongView.view_count,
            Genre.name.label("genre"),
            album.label("album"),
            SongView.import_state,
            all_roles.label("roles"),
        )
        .join(role, role.c.song_id == SongView.id)
        .outerjoin(Genre, Genre.id == SongView.genre_id)
        .group_by(*SongView.__table__.c, Genre.name)
        .having(*having)
        .order_by(ordering(keys, sort, order), name_key, SongView.id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    matching = select(role.c.song_id).group_by(role.c.song_id).having(*having)
    songs = rows.all()
    producers = await producers_of(session, [row.id for row in songs])
    return Page.of(
        [ArtistSong(**row._mapping, producers=producers.get(row.id, [])) for row in songs],
        await count(session, matching),
        paging,
    )


@router.get("/{artist_id}/videos")
async def list_artist_videos(
    artist_id: int,
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    sort: Literal["name", "released", "views"] = "released",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistVideo]:
    """The clips Genius links from the songs the artist is on in any role, each address once."""
    await get_or_404(session, ArtistView, artist_id)
    role = _of(song_roles(), artist_id, "song_id")
    named = artist_name(Artist.id, on=SongView.release_date, song_id=SongView.id)
    artists = (
        select(func.array_agg(aggregate_order_by(named, SongArtistView.position.nulls_last())))
        .select_from(SongArtistView)
        .join(Artist, Artist.id == SongArtistView.artist_id)
        .where(SongArtistView.song_id == SongView.id, SongArtistView.role == SongArtistRole.PRIMARY)
        .correlate(SongView)
        .scalar_subquery()
    )
    # A clip shared by several songs of the artist is shown once, with the song that came first.
    first = func.row_number().over(partition_by=SongVideo.url, order_by=SongView.id).label("first")
    base = (
        select(
            SongView.id.label("song_id"),
            SongView.base_name.label("song_name"),
            SongView.variant,
            SongVideo.url,
            SongVideo.start_seconds,
            SongVideo.explicit,
            SongVideo.official,
            SongView.release_date,
            SongView.release_date_precision,
            SongView.view_count,
            artists.label("artists"),
            first,
        )
        .join(SongVideo, SongVideo.song_id == SongView.id)
        .where(SongView.id.in_(select(role.c.song_id)))
        .subquery()
    )
    keys = {
        "name": (func.lower(base.c.song_name), "asc"),
        "released": (base.c.release_date, "desc"),
        "views": (base.c.view_count, "desc"),
    }
    rows = await session.execute(
        select(base)
        .where(base.c.first == 1)
        .order_by(ordering(keys, sort, order), func.lower(base.c.song_name), base.c.song_id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    matching = select(base.c.url).where(base.c.first == 1)
    return Page.of(
        [ArtistVideo(**{**row._mapping, "artists": row.artists or []}) for row in rows],
        await count(session, matching),
        paging,
    )


@router.get("/{artist_id}/albums")
async def list_artist_albums(
    artist_id: int,
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    roles: RolesQuery,
    include_unreleased: bool = False,
    q: str | None = None,
    sort: Literal["name", "released", "views"] = "released",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistAlbum]:
    """Albums the artist is on in any role (main or credited); `roles` as for the songs. Albums that are
    not out yet are left out unless `include_unreleased` is set."""
    await get_or_404(session, ArtistView, artist_id)
    role = _of(album_roles(), artist_id, "album_id")
    all_roles = array_agg(distinct(role.c.role))  # type: ignore[no-untyped-call]  # untyped upstream
    having = [all_roles.contains(roles)] if roles else []
    # A stub has NULL (unknown) and counts as released.
    filters = [] if include_unreleased else [AlbumView.is_released.is_not(False)]
    if q:
        filters.append(AlbumView.base_name.ilike(f"%{q}%"))
    name_key = func.lower(AlbumView.base_name)
    keys = {
        "name": (name_key, "asc"),
        "released": (AlbumView.release_date, "desc"),
        "views": (AlbumView.view_count, "desc"),
    }

    rows = await session.execute(
        select(*album_card_columns(), all_roles.label("roles"))
        .join(role, role.c.album_id == AlbumView.id)
        .where(*filters)
        .group_by(*AlbumView.__table__.c)
        .having(*having)
        .order_by(ordering(keys, sort, order), name_key, AlbumView.id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    matching = (
        select(role.c.album_id)
        .join(AlbumView, AlbumView.id == role.c.album_id)
        .where(*filters)
        .group_by(role.c.album_id)
        .having(*having)
    )
    return Page.of(
        [ArtistAlbum(**row._mapping) for row in rows], await count(session, matching), paging
    )
