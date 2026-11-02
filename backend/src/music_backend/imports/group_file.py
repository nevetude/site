"""A group file in the database: the members of the group and the time of each (see `groups.py`)."""

from typing import TYPE_CHECKING

from sqlalchemy import select

from music_backend.editing import Boundary, MemberSpec, replace_members
from music_backend.groups import Group, parse_partial_date
from music_backend.models import Artist

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _boundary(text: str | None) -> Boundary | None:
    if text is None:
        return None
    day, precision = parse_partial_date(text)
    return Boundary(date=day, precision=precision)


async def apply_group(session: AsyncSession, group: Group) -> None:
    """Makes the members of the group in the database what its file says, in the order of the file. A member that is
    not in the database (the import of that member failed) is left out; one that Genius lists and the file does not is hidden."""
    ids = dict(
        (
            await session.execute(
                select(Artist.genius_id, Artist.id).where(
                    Artist.genius_id.in_([group.genius_id, *(m.genius_id for m in group.members)])
                )
            )
        ).all()
    )
    group_id = ids.get(group.genius_id)
    if group_id is None:
        return
    await replace_members(
        session,
        group_id,
        [
            MemberSpec(ids[m.genius_id], _boundary(m.start), _boundary(m.end), m.has_left)
            for m in group.members
            if m.genius_id in ids and m.genius_id != group.genius_id
        ],
    )
