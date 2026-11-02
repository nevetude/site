from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ImportKind
from music_backend.imports.common import Task
from music_backend.models import Album, AlbumTrack, Song
from tests.factories import make_artist, make_song
from tests.fakes import FakeGenius, album_payload, import_all, song_payload, track

type SessionMaker = async_sessionmaker[AsyncSession]


def genius() -> FakeGenius:
    return FakeGenius(
        albums={100: album_payload(100, "Record")},
        tracks={100: [track(500, number=1), track(501, number=2), track(502, number=3)]},
        songs={i: song_payload(i, f"Song {i}") for i in (500, 501, 502)},
    )


async def imported(sessionmaker: SessionMaker) -> tuple[int, dict[int, int]]:
    """The album and its three songs as the import makes them: the album id, and the song ids by Genius id."""
    await import_all(sessionmaker, genius(), Task(ImportKind.ALBUM, 100))
    async with sessionmaker() as db:
        album = await db.scalar(select(Album.id))
        songs = dict((await db.execute(select(Song.genius_id, Song.id))).all())
    return album, songs  # type: ignore[return-value]


async def names(api: AsyncClient, album: int) -> list[str]:
    tracks = (await api.get(f"/api/v1/albums/{album}/tracks")).json()
    return [t["base_name"] for t in tracks]


async def test_the_tracklist_is_what_the_list_says_in_its_order(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album, songs = await imported(sessionmaker)
    assert await names(api, album) == ["Song 500", "Song 501", "Song 502"]
    async with sessionmaker() as db:
        extra = (await make_song(db, "Added by hand")).id
        await db.commit()

    # reordered, one taken out, one added
    saved = await api.put(
        f"/api/v1/albums/{album}/tracks",
        json=[{"song_id": songs[502]}, {"song_id": songs[500]}, {"song_id": extra}],
    )

    assert saved.status_code == 200
    assert [(t["base_name"], t["position"]) for t in saved.json()] == [
        ("Song 502", 1),
        ("Song 500", 2),
        ("Added by hand", 3),
    ]
    page = (await api.get(f"/api/v1/albums/{album}")).json()
    assert page["tracks_count"] == 3
    # the rows of Genius are as the import wrote them; the hidden track is still there
    async with sessionmaker() as db:
        rows = (await db.scalars(select(AlbumTrack).where(AlbumTrack.album_id == album))).all()
    # Genius's numbers are as the import wrote them; the row that was added has none of its own
    assert sorted(r.position for r in rows if r.position) == [1, 2, 3]
    assert len(rows) == 4


async def test_the_import_does_not_change_the_tracklist_of_the_user(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album, songs = await imported(sessionmaker)
    await api.put(
        f"/api/v1/albums/{album}/tracks", json=[{"song_id": songs[502]}, {"song_id": songs[501]}]
    )

    await import_all(sessionmaker, genius(), Task(ImportKind.ALBUM, 100))

    assert await names(api, album) == ["Song 502", "Song 501"]


async def test_tracks_are_numbered_on_each_disc(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album, songs = await imported(sessionmaker)

    saved = await api.put(
        f"/api/v1/albums/{album}/tracks",
        json=[
            {"song_id": songs[500], "disc_number": 1},
            {"song_id": songs[501], "disc_number": 2},
            {"song_id": songs[502], "disc_number": 1},
        ],
    )

    assert [(t["base_name"], t["disc_number"], t["position"]) for t in saved.json()] == [
        ("Song 500", 1, 1),
        ("Song 502", 1, 2),
        ("Song 501", 2, 1),
    ]


async def test_a_song_that_is_not_known_is_refused(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    album, _ = await imported(sessionmaker)

    refused = await api.put(f"/api/v1/albums/{album}/tracks", json=[{"song_id": 999999}])

    assert refused.status_code == 422
    assert await names(api, album) == ["Song 500", "Song 501", "Song 502"]


async def test_songs_of_the_library_are_found_by_name(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        artist = await make_artist(db, "Thom")
        await make_song(db, "Paranoid Android")
        await make_song(db, "Android Lust")
        await make_song(db, "Other")
        await db.commit()
        assert artist.id

    found = (await api.get("/api/v1/songs/search?q=android")).json()

    assert [s["base_name"] for s in found] == ["Android Lust", "Paranoid Android"]
