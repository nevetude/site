from datetime import date

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ImportKind, UserRole
from music_backend.imports.common import Task
from music_backend.models import Album, AlbumArtist, AppUser, Artist, Revision, Song
from tests.factories import make_album, make_artist, make_song
from tests.fakes import FakeGenius, album_payload, import_all

type SessionMaker = async_sessionmaker[AsyncSession]


async def one_album(sessionmaker: SessionMaker) -> int:
    async with sessionmaker() as db:
        artist = await make_artist(db, "Thom", genius_id=10)
        album = await make_album(
            db,
            "Genius title",
            genius_id=100,
            variant="Deluxe",
            release_date=date(2012, 10, 22),
            description="by Genius",
            is_released=True,
        )
        db.add(AlbumArtist(album_id=album.id, artist_id=artist.id, position=1))
        await db.commit()
        return album.id


async def test_me_says_who_is_calling_and_whether_they_can_edit(api: AsyncClient) -> None:
    me = (await api.get("/api/v1/me")).json()

    assert (me["login"], me["role"], me["can_edit"]) == ("admin", "admin", True)


async def test_a_field_is_changed_by_hand_and_the_row_of_genius_stays(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album = await one_album(sessionmaker)

    changed = await api.patch(
        f"/api/v1/albums/{album}",
        json={
            "base_name": "My title",
            "release_date": None,  # taken away, which is a change too
            "album_type": "ep",
            "is_released": False,
            "description": "my own text",
        },
    )

    assert changed.status_code == 200
    got = changed.json()
    assert (got["base_name"], got["release_date"], got["album_type"], got["is_released"]) == (
        "My title",
        None,
        "ep",
        False,
    )
    assert got["variant"] == "Deluxe"  # not touched: still Genius's
    assert got["description"] == "my own text"
    assert got["description_dom"] is None
    assert sorted(got["edited"]) == [
        "album_type", "base_name", "description", "is_released", "release_date",
    ]  # fmt: skip
    # what the import wrote is as it was
    async with sessionmaker() as db:
        row = await db.get(Album, album)
        assert (row.base_name, row.release_date, row.description) == (  # type: ignore[union-attr]
            "Genius title",
            date(2012, 10, 22),
            "by Genius",
        )
        revisions = (await db.scalars(select(Revision).where(Revision.entity_id == album))).all()
    assert len(revisions) == 1
    assert revisions[0].changes["base_name"] == ["Genius title", "My title"]
    assert revisions[0].user_id is not None


async def test_a_field_goes_back_to_genius_with_reset(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album = await one_album(sessionmaker)
    await api.patch(f"/api/v1/albums/{album}", json={"base_name": "Mine", "variant": None})

    reset = (await api.patch(f"/api/v1/albums/{album}", json={"reset": ["base_name"]})).json()

    assert (reset["base_name"], reset["variant"], reset["edited"]) == (
        "Genius title",
        None,
        ["variant"],
    )
    # nothing left: the edit row is gone
    final = (await api.patch(f"/api/v1/albums/{album}", json={"reset": ["variant"]})).json()
    assert (final["variant"], final["edited"]) == ("Deluxe", [])


async def test_lists_and_sorting_follow_the_edited_values(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album = await one_album(sessionmaker)
    async with sessionmaker() as db:
        artist = await db.scalar(select(Artist.id))
        other = await make_album(db, "Other", release_date=date(2015, 1, 1))
        db.add(AlbumArtist(album_id=other.id, artist_id=artist, position=1))
        await db.commit()
    before = (await api.get(f"/api/v1/artists/{artist}/albums?sort=released&order=asc")).json()
    assert [a["base_name"] for a in before["items"]] == ["Genius title", "Other"]

    await api.patch(f"/api/v1/albums/{album}", json={"release_date": "2020-05-05"})

    after = (await api.get(f"/api/v1/artists/{artist}/albums?sort=released&order=asc")).json()
    assert [a["base_name"] for a in after["items"]] == ["Other", "Genius title"]
    # the unreleased are left out of the list of an artist, by the status that was set by hand
    await api.patch(f"/api/v1/albums/{album}", json={"is_released": False})
    hidden = (await api.get(f"/api/v1/artists/{artist}/albums")).json()
    assert [a["base_name"] for a in hidden["items"]] == ["Other"]


async def test_the_import_goes_on_writing_its_rows_under_the_edits(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album = await one_album(sessionmaker)
    await api.patch(f"/api/v1/albums/{album}", json={"base_name": "Mine"})

    # Genius renames the album; the import writes it, the site still shows the title of the user
    fake = FakeGenius(albums={100: album_payload(100, name="Renamed by Genius")})
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    got = (await api.get(f"/api/v1/albums/{album}")).json()
    assert got["base_name"] == "Mine"
    await api.patch(f"/api/v1/albums/{album}", json={"reset": ["base_name"]})
    assert (await api.get(f"/api/v1/albums/{album}")).json()["base_name"] == "Renamed by Genius"


async def test_an_artist_and_a_song_are_changed_the_same_way(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        artist = await make_artist(db, "Thom", description="Genius text", artist_type=None)
        song = await make_song(db, "Old", release_date=date(2000, 1, 1))
        await db.commit()
        artist_id, song_id = artist.id, song.id

    got = (
        await api.patch(
            f"/api/v1/artists/{artist_id}",
            json={
                "artist_type": "group",
                "cover_url": "https://x/y.jpg",
                "real_name": "Thomas Y.",
                "disambiguator": "UK",
            },
        )
    ).json()
    assert (got["artist_type"], got["cover_url"]) == ("group", "https://x/y.jpg")
    assert (got["real_name"], got["disambiguator"]) == ("Thomas Y.", "UK")
    assert got["description"] == "Genius text"

    changed = (
        await api.patch(
            f"/api/v1/songs/{song_id}",
            json={
                "base_name": "New",
                "release_date": "2001-02-03",
                "release_date_precision": "month",
            },
        )
    ).json()
    assert (changed["base_name"], changed["release_date"], changed["release_date_precision"]) == (
        "New",
        "2001-02-03",
        "month",
    )
    assert sorted(changed["edited"]) == ["base_name", "release_date", "release_date_precision"]
    async with sessionmaker() as db:
        assert (await db.get(Song, song_id)).base_name == "Old"  # type: ignore[union-attr]


async def test_only_an_editor_may_write(api: AsyncClient, sessionmaker: SessionMaker) -> None:
    album = await one_album(sessionmaker)
    async with sessionmaker() as db:
        await api.get("/api/v1/me")  # makes the admin
        await db.execute(update(AppUser).values(role=UserRole.VIEWER))
        await db.commit()

    denied = await api.patch(f"/api/v1/albums/{album}", json={"base_name": "No"})

    assert denied.status_code == 403
    assert (await api.get("/api/v1/me")).json()["can_edit"] is False
    assert (await api.get(f"/api/v1/albums/{album}")).json()["base_name"] == "Genius title"


async def test_a_field_that_does_not_exist_is_refused(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album = await one_album(sessionmaker)

    assert (await api.patch(f"/api/v1/albums/{album}", json={"genius_id": 5})).status_code == 422
    assert (await api.patch("/api/v1/albums/999999", json={"base_name": "x"})).status_code == 404


async def test_the_artists_of_an_album_are_changed_and_the_import_does_not_bring_back_a_removed_one(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    from tests.factories import make_artist

    async with sessionmaker() as db:
        album = (await make_album(db, "Record")).id
        first = (await make_artist(db, "First")).id
        second = (await make_artist(db, "Second")).id
        await db.commit()

    saved = await api.put(f"/api/v1/albums/{album}/artists", json=[first, second])

    assert saved.status_code == 200
    page = (await api.get(f"/api/v1/albums/{album}")).json()
    assert [a["base_name"] for a in page["artists"]] == ["First", "Second"]
    await api.put(f"/api/v1/albums/{album}/artists", json=[second])
    page = (await api.get(f"/api/v1/albums/{album}")).json()
    assert [a["base_name"] for a in page["artists"]] == ["Second"]
    assert (await api.put(f"/api/v1/albums/{album}/artists", json=[999999])).status_code == 422
