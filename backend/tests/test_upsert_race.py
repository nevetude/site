import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.imports.common import upsert
from music_backend.models import Album

type SessionMaker = async_sessionmaker[AsyncSession]


async def test_two_parallel_imports_of_one_new_album_do_not_fail(
    sessionmaker: SessionMaker,
) -> None:
    """The walk over groups meets the same album from two artists at once (error seen in a real import:
    duplicate key `uq_album_genius_id`): the second insert must wait for the first and update its row."""

    async def import_album(description: str) -> dict[str, list[object]]:
        async with sessionmaker() as db, db.begin():
            _, changes = await upsert(
                db,
                Album,
                372158,
                {"name": "Innocence", "base_name": "Innocence", "description": description},
            )
            await asyncio.sleep(
                0.05
            )  # the other transaction reaches its insert while this one is open
            return changes

    first, second = await asyncio.gather(import_album("one"), import_album("two"))

    async with sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(Album)) == 1
    # one of them created the row, the other changed it
    assert sorted(["genius_id" in first, "genius_id" in second]) == [False, True]
