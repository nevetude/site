from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.factories import make_album, make_artist

type SessionMaker = async_sessionmaker[AsyncSession]


async def test_a_series_shows_its_albums_oldest_first_and_an_album_may_be_in_two(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        artist = (await make_artist(db, "Smokey")).id
        late = (await make_album(db, "Vol 3", release_date=date(2015, 1, 1))).id
        early = (await make_album(db, "Vol 1", release_date=date(2013, 1, 1))).id
        undated = (await make_album(db, "Vol 4")).id
        await db.commit()

    saved = await api.put(
        f"/api/v1/artists/{artist}/series",
        json=[
            {"name": "Evil Wayz", "album_ids": [undated, late, early]},
            {"name": "Best", "album_ids": [late]},
        ],
    )

    assert saved.status_code == 200
    assert [(s["name"], [a["base_name"] for a in s["albums"]]) for s in saved.json()] == [
        ("Evil Wayz", ["Vol 1", "Vol 3", "Vol 4"]),  # by the date, the album with none last
        ("Best", ["Vol 3"]),
    ]
    page = (await api.get(f"/api/v1/artists/{artist}")).json()
    assert [s["name"] for s in page["series"]] == ["Evil Wayz", "Best"]


async def test_the_list_replaces_the_series_and_an_unknown_album_is_refused(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        artist = (await make_artist(db, "Smokey")).id
        album = (await make_album(db, "Vol 1")).id
        await db.commit()
    await api.put(f"/api/v1/artists/{artist}/series", json=[{"name": "Old", "album_ids": [album]}])

    refused = await api.put(
        f"/api/v1/artists/{artist}/series", json=[{"name": "New", "album_ids": [999999]}]
    )
    assert refused.status_code == 422
    assert [s["name"] for s in (await api.get(f"/api/v1/artists/{artist}")).json()["series"]] == [
        "Old"
    ]  # nothing was changed

    await api.put(f"/api/v1/artists/{artist}/series", json=[])
    assert (await api.get(f"/api/v1/artists/{artist}")).json()["series"] == []


async def test_the_albums_of_an_artist_are_found_by_name(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    from sqlalchemy import insert

    from music_backend.models import AlbumArtist

    async with sessionmaker() as db:
        artist = (await make_artist(db, "Smokey")).id
        for title in ("Evil Wayz", "Codeine Demonz"):
            album = (await make_album(db, title)).id
            await db.execute(insert(AlbumArtist).values(album_id=album, artist_id=artist))
        await db.commit()

    found = (
        await api.get(f"/api/v1/artists/{artist}/albums?q=wayz&include_unreleased=true")
    ).json()

    assert [a["base_name"] for a in found["items"]] == ["Evil Wayz"]
