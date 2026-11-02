"""The members of a group with the time each was in it (see `ArtistMemberEdit`): read for the page, and replaced as a
whole by the editor. The list in the body is the group as the user wants it: who is in it, in what order, and when."""

import asyncio
import datetime as dt

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.names import artist_name
from music_backend.api.nicknames import ReleaseRef, release_refs
from music_backend.api.queries import artist_ref_columns, get_or_404, refuse_unknown
from music_backend.api.schemas import ArtistRef
from music_backend.editing import Boundary, MemberSpec, log_revision, replace_members
from music_backend.enums import DatePrecision
from music_backend.groups import Group, GroupMember, format_partial_date, load_group, save_group
from music_backend.models import Artist, ArtistMemberView, ArtistView

router = APIRouter(prefix="/api/v1/artists", tags=["members"])


class MemberOut(BaseModel):
    """The artist on the other side of a membership (a member of the group, or the group of a member) and the time
    of it. `starts_on` and `ends_on` are dates (of the release it is tied to, or the date that was given); no
    `ends_on` is "now", or, with `has_left`, a time nobody knows."""

    artist: ArtistRef
    starts_on: dt.date | None
    starts_precision: DatePrecision | None
    ends_on: dt.date | None
    ends_precision: DatePrecision | None
    has_left: bool
    start: ReleaseRef | None  # the release the start is tied to, if it is
    end: ReleaseRef | None


class BoundaryIn(BaseModel):
    """One end of the time in the group: a release (the date follows it) or a date (a year is enough)."""

    album_id: int | None = None
    song_id: int | None = None
    date: dt.date | None = None
    precision: DatePrecision | None = None


class MemberIn(BaseModel):
    member_id: int
    start: BoundaryIn | None = None
    end: BoundaryIn | None = None
    has_left: bool = False


async def read_members(
    session: AsyncSession, *, group_id: int | None = None, member_id: int | None = None
) -> list[MemberOut]:
    """The members of a group (`group_id`), or the groups of a member (`member_id`), in the order of the user. The
    names are the ones the artists have now."""
    other = ArtistMemberView.member_id if group_id is not None else ArtistMemberView.group_id
    name = artist_name(ArtistView.id)
    rows = (
        await session.execute(
            select(
                *artist_ref_columns(name),
                ArtistMemberView.starts_on,
                ArtistMemberView.starts_precision,
                ArtistMemberView.ends_on,
                ArtistMemberView.ends_precision,
                ArtistMemberView.has_left,
                ArtistMemberView.start_album_id,
                ArtistMemberView.start_song_id,
                ArtistMemberView.end_album_id,
                ArtistMemberView.end_song_id,
            )
            .join(ArtistMemberView, other == ArtistView.id)
            .where(
                ArtistMemberView.group_id == group_id
                if group_id is not None
                else ArtistMemberView.member_id == member_id
            )
            .order_by(ArtistMemberView.position.nulls_last(), name)
        )
    ).all()
    releases = await release_refs(
        session,
        {i for r in rows for i in (r.start_album_id, r.end_album_id) if i},
        {i for r in rows for i in (r.start_song_id, r.end_song_id) if i},
    )

    def ref(album_id: int | None, song_id: int | None) -> ReleaseRef | None:
        if album_id is not None:
            return releases[("album", album_id)]
        return releases[("song", song_id)] if song_id is not None else None

    return [
        MemberOut(
            artist=ArtistRef.model_validate(row, from_attributes=True),
            starts_on=row.starts_on,
            starts_precision=row.starts_precision,
            ends_on=row.ends_on,
            ends_precision=row.ends_precision,
            has_left=row.has_left,
            start=ref(row.start_album_id, row.start_song_id),
            end=ref(row.end_album_id, row.end_song_id),
        )
        for row in rows
    ]


@router.put("/{group_id}/members")
async def put_members(
    group_id: int, body: list[MemberIn], request: Request, session: SessionDep, user: EditorDep
) -> list[MemberOut]:
    """Makes the group what the list says. A member that Genius lists and is not in the list is hidden, not deleted:
    the import cannot bring them back."""
    await get_or_404(session, ArtistView, group_id)
    before = await read_members(session, group_id=group_id)
    specs = [
        MemberSpec(
            item.member_id,
            Boundary(**item.start.model_dump()) if item.start else None,
            Boundary(**item.end.model_dump()) if item.end else None,
            item.has_left,
        )
        for item in body
    ]
    async with refuse_unknown(session, "An artist or a release of the list is not known"):
        await replace_members(session, group_id, specs)
    after = await read_members(session, group_id=group_id)

    def summary(members: list[MemberOut]) -> list[dict[str, object]]:
        return [
            {
                "id": m.artist.id,
                "name": m.artist.base_name,
                "starts_on": m.starts_on,
                "ends_on": m.ends_on,
                "has_left": m.has_left,
            }
            for m in members
        ]

    await log_revision(
        session,
        "artist",
        group_id,
        user.id,
        {"members": [summary(before), summary(after)]} if summary(before) != summary(after) else {},
    )
    await session.commit()
    await _write_group_file(request, session, group_id, after)
    return after


async def _write_group_file(
    request: Request, session: AsyncSession, group_id: int, members: list[MemberOut]
) -> None:
    """The file of the group (see `groups.py`) is kept as the page has the group, so a clean database can be filled
    again from it. Only an artist of Genius has one: the file is named by the Genius id."""
    group = await session.get(Artist, group_id)
    if group is None or group.genius_id is None:
        return
    directory = request.app.state.settings.groups_dir
    old = await asyncio.to_thread(load_group, directory, group.genius_id)
    file = Group(
        genius_id=group.genius_id,
        name=group.base_name,
        members=[
            GroupMember(
                genius_id=m.artist.genius_id,
                name=m.artist.base_name,
                start=format_partial_date(m.starts_on, m.starts_precision) if m.starts_on else None,
                end=format_partial_date(m.ends_on, m.ends_precision) if m.ends_on else None,
                has_left=m.has_left,
            )
            for m in members
            if m.artist.genius_id is not None
        ],
        discographies=old.discographies if old else False,
    )
    await asyncio.to_thread(save_group, directory, file)
