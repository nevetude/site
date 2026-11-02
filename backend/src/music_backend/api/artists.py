"""The artist list of the home page (a test feature: it may go away, so it stands on its own).

The server answers with facts and filters on facts; which of them make a "block" on the page is the
client's decision.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Subquery, distinct, exists, func, or_, select, union

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.names import artist_name
from music_backend.api.queries import (
    album_roles,
    artist_ref_columns,
    count,
    ordering,
    song_roles,
)
from music_backend.api.schemas import ArtistRef, Page, PagingDep, RolesQuery
from music_backend.enums import ArtistType, ImportKind, ImportState, JobStatus
from music_backend.models import (
    ArtistAlias,
    ArtistView,
    ImportJob,
    Nickname,
    NicknameSpelling,
    SongArtistView,
)

router = APIRouter(prefix="/api/v1/artists", tags=["artists"])


class ArtistFilters(BaseModel):
    import_state: ImportState | None = None
    is_group: bool | None = None
    # Whether a successful import of the artist's discography was run for it by hand.
    discography_imported: bool | None = None


class ArtistCard(BaseModel):
    id: int
    genius_id: int | None
    base_name: str
    cover_url: str | None
    genius_url: str | None
    is_verified: bool | None
    followers_count: int | None
    tracks_count: int  # songs on which the artist is a primary or a featured artist
    artist_type: ArtistType | None
    import_state: ImportState


class RoleCount(BaseModel):
    role: str
    artists: int


def _conditions(filters: ArtistFilters) -> list[ColumnElement[bool]]:
    where: list[ColumnElement[bool]] = []
    if filters.import_state is not None:
        where.append(ArtistView.import_state == filters.import_state)
    if filters.is_group is True:
        where.append(ArtistView.artist_type == ArtistType.GROUP)
    elif filters.is_group is False:
        where.append(
            or_(ArtistView.artist_type.is_(None), ArtistView.artist_type != ArtistType.GROUP)
        )
    if filters.discography_imported is not None:
        imported = exists().where(
            ImportJob.kind == ImportKind.DISCOGRAPHY,
            ImportJob.status == JobStatus.SUCCEEDED,
            ImportJob.genius_id == ArtistView.genius_id,
        )
        where.append(imported if filters.discography_imported else ~imported)
    return where


def _artist_roles() -> Subquery:
    """(artist_id, role) for every role an artist has, in songs and in albums."""
    songs, albums = song_roles(), album_roles()
    return union(
        select(songs.c.artist_id, songs.c.role), select(albums.c.artist_id, albums.c.role)
    ).subquery("artist_role")


@router.get("")
async def list_artists(
    filters: Annotated[ArtistFilters, Depends()],
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    roles: RolesQuery,
    sort: Literal["name", "followers", "tracks"] = "name",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistCard]:
    """Artists matching all the filters and having every one of `roles` (all of them, not any)."""
    tracks = (
        select(func.count(distinct(SongArtistView.song_id)))
        .where(SongArtistView.artist_id == ArtistView.id)
        .correlate(ArtistView)
        .scalar_subquery()
    )
    artist_roles = _artist_roles()
    where = _conditions(filters)
    where += [
        exists().where(artist_roles.c.artist_id == ArtistView.id, artist_roles.c.role == role)
        for role in roles
    ]
    current = artist_name(ArtistView.id)  # the name the artist has now
    name_key = func.lower(current)
    keys = {
        "name": (name_key, "asc"),
        "followers": (ArtistView.followers_count, "desc"),
        "tracks": (tracks, "desc"),
    }

    rows = await session.execute(
        select(
            ArtistView.id,
            ArtistView.genius_id,
            current.label("base_name"),
            ArtistView.cover_url,
            ArtistView.genius_url,
            ArtistView.is_verified,
            ArtistView.followers_count,
            tracks.label("tracks_count"),
            ArtistView.artist_type,
            ArtistView.import_state,
        )
        .where(*where)
        .order_by(ordering(keys, sort, order), name_key, ArtistView.id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    total = await count(session, select(ArtistView.id).where(*where))
    return Page.of([ArtistCard(**row._mapping) for row in rows], total, paging)


@router.get("/search")
async def search_artists(
    q: str, session: SessionDep, _: UserDep, limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[ArtistRef]:
    """The artists of the library whose name has `q` in it: the name Genius gave, an alias, a nickname or a spelling of
    one. For picking an artist to put in a group; an artist that is not in the library is found on Genius and imported."""
    like = f"%{q}%"
    named = or_(
        ArtistView.base_name.ilike(like),
        exists().where(ArtistAlias.artist_id == ArtistView.id, ArtistAlias.name.ilike(like)),
        exists().where(
            Nickname.artist_id == ArtistView.id,
            or_(
                Nickname.name.ilike(like),
                exists().where(
                    NicknameSpelling.nickname_id == Nickname.id, NicknameSpelling.text.ilike(like)
                ),
            ),
        ),
    )
    name = artist_name(ArtistView.id)
    rows = await session.execute(
        select(*artist_ref_columns(name)).where(named).order_by(func.lower(name)).limit(limit)
    )
    return [ArtistRef.model_validate(row, from_attributes=True) for row in rows]


@router.get("/roles")
async def list_artist_roles(
    filters: Annotated[ArtistFilters, Depends()],
    session: SessionDep,
    _: UserDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 40,
) -> list[RoleCount]:
    """The roles found among the artists matching the filters, the most common first."""
    artist_roles = _artist_roles()
    count = func.count(distinct(artist_roles.c.artist_id))
    rows = await session.execute(
        select(artist_roles.c.role, count.label("artists"))
        .join(ArtistView, ArtistView.id == artist_roles.c.artist_id)
        .where(*_conditions(filters))
        .group_by(artist_roles.c.role)
        .order_by(count.desc(), artist_roles.c.role)
        .limit(limit)
    )
    return [RoleCount(role=role, artists=artists) for role, artists in rows]
