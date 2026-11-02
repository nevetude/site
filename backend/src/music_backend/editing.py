"""Changing what the site shows, without touching what the import wrote (see `models/edits.py`).

Every change is one transaction that writes the edit rows and one `Revision` with what changed on the page: the value
before and after, as the site showed them."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic_core import to_jsonable_python
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from music_backend.enums import DatePrecision, RevisionAction
from music_backend.models import ArtistMember, ArtistMemberEdit, ArtistMemberView, Revision

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import DeclarativeBase


async def put_edit(
    session: AsyncSession, edit: type[DeclarativeBase], key: Mapping[str, Any], **fields: Any
) -> None:
    """Writes the edit row of one row of Genius (`key` names its columns): made when there is none, else its `fields` are
    set. What is not in `fields` stays as it was."""
    await session.execute(
        insert(edit)
        .values(**key, **fields)
        .on_conflict_do_update(index_elements=list(key), set_=fields)
    )


async def log_revision(
    session: AsyncSession,
    entity_type: str,
    entity_id: int,
    user_id: int,
    changes: Mapping[str, Any],
) -> None:
    """`changes` is `{what: [before, after]}`; nothing is written when nothing changed."""
    if changes:
        session.add(
            Revision(
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                action=RevisionAction.UPDATE,
                changes=to_jsonable_python(changes),
            )
        )


async def override_fields(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: int,
    user_id: int,
    view: type[DeclarativeBase],
    edit: type[DeclarativeBase],
    key: str,
    fields: Iterable[str],
    values: Mapping[str, Any],
    reset: Iterable[str] = (),
) -> None:
    """Sets the fields in `values` by hand (a value may be NULL) and resets the ones in `reset` to what Genius has.

    The `edit` row names the fields that were set in `overridden`; it goes away when none is left."""
    names = tuple(fields)

    async def shown() -> dict[str, Any]:
        row = await session.get(view, entity_id, populate_existing=True)
        return {name: getattr(row, name) for name in names}

    before = await shown()
    row = await session.get(edit, entity_id)
    if row is None:
        row = edit(**{key: entity_id, "overridden": []})
        session.add(row)
    overridden = set(row.overridden)  # type: ignore[attr-defined]
    for name, value in values.items():
        setattr(row, name, value)
        overridden.add(name)
    for name in reset:
        setattr(row, name, None)
        overridden.discard(name)
    if overridden:
        row.overridden = sorted(overridden)  # type: ignore[attr-defined]
    else:
        await session.delete(row)
    await session.flush()
    after = await shown()
    await log_revision(
        session,
        entity_type,
        entity_id,
        user_id,
        {name: [before[name], after[name]] for name in names if before[name] != after[name]},
    )
    await session.commit()


@dataclass(slots=True)
class Boundary:
    """One end of the time in a group: a release (the date follows it) or a date."""

    album_id: int | None = None
    song_id: int | None = None
    date: date | None = None
    precision: DatePrecision | None = None


@dataclass(slots=True)
class MemberSpec:
    member_id: int
    start: Boundary | None = None
    end: Boundary | None = None
    has_left: bool = False


def _boundary(prefix: str, boundary: Boundary | None) -> dict[str, object]:
    return {
        f"{prefix}_album_id": boundary.album_id if boundary else None,
        f"{prefix}_song_id": boundary.song_id if boundary else None,
        f"{prefix}_date": boundary.date if boundary else None,
        f"{prefix}_precision": boundary.precision if boundary else None,
    }


async def replace_members(session: AsyncSession, group_id: int, members: list[MemberSpec]) -> None:
    """Makes the group what the list says: who is in it, in what order, and when. A member that Genius lists and is
    not in the list is hidden, not deleted: the import cannot bring them back. Raises `IntegrityError` for an artist
    or a release that does not exist."""
    shown = set(
        await session.scalars(
            select(ArtistMemberView.member_id).where(ArtistMemberView.group_id == group_id)
        )
    )
    for position, item in enumerate(members, start=1):
        await session.execute(
            insert(ArtistMember)
            .values(group_id=group_id, member_id=item.member_id, position=position)
            .on_conflict_do_nothing()
        )
        await put_edit(
            session,
            ArtistMemberEdit,
            {"group_id": group_id, "member_id": item.member_id},
            removed=False,
            position=position,
            has_left=item.has_left,
            **_boundary("start", item.start),
            **_boundary("end", item.end),
        )
    for member_id in shown - {item.member_id for item in members}:
        await put_edit(
            session, ArtistMemberEdit, {"group_id": group_id, "member_id": member_id}, removed=True
        )
    await session.flush()
