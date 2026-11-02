from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import SongArtistRole
from music_backend.models import (
    AlbumArtist,
    ArtistAlias,
    CreditRole,
    Revision,
    SongArtist,
    SongCredit,
)
from tests.factories import make_album, make_artist, make_song, place

type SessionMaker = async_sessionmaker[AsyncSession]

ALBUMS = {
    "Doggystyle": date(1993, 11, 23),
    "Tha Doggfather": date(1996, 11, 12),
    "Reincarnated": date(2013, 4, 23),
    "Bush": date(2015, 5, 12),
}


async def arrange(sessionmaker: SessionMaker) -> dict[str, int]:
    """Snoop on four albums, a song of every album, and a song with an alter ego."""
    ids: dict[str, int] = {}
    async with sessionmaker() as db:
        snoop = await make_artist(db, "Snoop Dogg", genius_id=1)
        ids["artist"] = snoop.id
        for name, released in ALBUMS.items():
            album = await make_album(db, name, release_date=released)
            song = await make_song(db, f"{name} song", release_date=released)
            db.add(AlbumArtist(album_id=album.id, artist_id=snoop.id, position=1))
            db.add(SongArtist(song_id=song.id, artist_id=snoop.id, role=SongArtistRole.PRIMARY))
            await place(db, album, song, position=1, disc_number=1)
            ids[name] = album.id
            ids[f"{name} song"] = song.id
        zilla = await make_song(db, "Zilla", release_date=date(2013, 4, 23))
        db.add(SongArtist(song_id=zilla.id, artist_id=snoop.id, role=SongArtistRole.PRIMARY))
        ids["Zilla"] = zilla.id
        await db.commit()
    return ids


def snoop_names(ids: dict[str, int]) -> list[dict[str, object]]:
    return [
        {"kind": "main", "name": "Snoop Doggy Dogg", "periods": [{}]},
        {
            "kind": "main",
            "name": "Snoop Dogg",
            "spellings": ["SNOOP DOGG"],
            "periods": [
                {"start_album_id": ids["Tha Doggfather"]},
                {"start_album_id": ids["Bush"]},  # the name comes back
            ],
            "uses": [{"album_id": ids["Bush"], "spelling": "SNOOP DOGG"}],
        },
        {
            "kind": "main",
            "name": "Snoop Lion",
            "periods": [{"start_album_id": ids["Reincarnated"]}],
        },
        {"kind": "alter_ego", "name": "Snoopzilla", "uses": [{"song_id": ids["Zilla"]}]},
    ]


async def test_the_names_are_replaced_as_a_whole_and_read_back(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    saved = await api.put(f"/api/v1/artists/{ids['artist']}/nicknames", json=snoop_names(ids))

    assert saved.status_code == 200
    got = saved.json()
    assert [(n["kind"], n["name"]) for n in got] == [
        ("main", "Snoop Doggy Dogg"),
        ("main", "Snoop Dogg"),
        ("main", "Snoop Lion"),
        ("alter_ego", "Snoopzilla"),
    ]
    assert [p["start"] and p["start"]["name"] for p in got[1]["periods"]] == [
        "Tha Doggfather",
        "Bush",
    ]
    assert got[1]["uses"][0]["spelling"] == "SNOOP DOGG"
    assert got[3]["uses"][0]["release"] == {
        "kind": "song",
        "id": ids["Zilla"],
        "name": "Zilla",
        "variant": None,
        "release_date": "2013-04-23",
        "release_date_precision": None,
    }
    # the page of the artist has them, and is titled with the name now
    page = (await api.get(f"/api/v1/artists/{ids['artist']}")).json()
    assert page["base_name"] == "Snoop Dogg"
    assert [n["name"] for n in page["nicknames"]] == [n["name"] for n in got]
    # replacing again with fewer names takes the others away
    left = await api.put(
        f"/api/v1/artists/{ids['artist']}/nicknames", json=[{"kind": "main", "name": "Only"}]
    )
    assert [n["name"] for n in left.json()] == ["Only"]


async def test_every_page_shows_the_name_of_the_day_of_its_release(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(f"/api/v1/artists/{ids['artist']}/nicknames", json=snoop_names(ids))

    async def album_artist(name: str) -> str:
        album = (await api.get(f"/api/v1/albums/{ids[name]}")).json()
        return str(album["artists"][0]["base_name"])

    assert await album_artist("Doggystyle") == "Snoop Doggy Dogg"
    assert await album_artist("Tha Doggfather") == "Snoop Dogg"
    assert await album_artist("Reincarnated") == "Snoop Lion"
    assert await album_artist("Bush") == "SNOOP DOGG"  # the spelling chosen for this album
    # a track on the album page, and the card in a list, have the same name
    tracks = (await api.get(f"/api/v1/albums/{ids['Reincarnated']}/tracks")).json()
    assert tracks[0]["artists"][0]["base_name"] == "Snoop Lion"
    cards = (
        await api.get(f"/api/v1/artists/{ids['artist']}/albums?sort=released&order=asc")
    ).json()["items"]
    assert [c["artists"] for c in cards] == [
        ["Snoop Doggy Dogg"], ["Snoop Dogg"], ["Snoop Lion"], ["SNOOP DOGG"],
    ]  # fmt: skip
    # the song page, with the alter ego tied to a song
    assert (await api.get(f"/api/v1/songs/{ids['Zilla']}")).json()["artists"][0][
        "base_name"
    ] == "Snoopzilla"
    plain = (await api.get(f"/api/v1/songs/{ids['Reincarnated song']}")).json()
    assert plain["artists"][0]["base_name"] == "Snoop Lion"


async def test_the_list_of_artists_has_the_latest_name(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(f"/api/v1/artists/{ids['artist']}/nicknames", json=snoop_names(ids))

    items = (await api.get("/api/v1/artists")).json()["items"]

    assert [a["base_name"] for a in items] == ["Snoop Dogg"]


async def test_the_start_of_a_period_follows_the_date_of_its_release(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(f"/api/v1/artists/{ids['artist']}/nicknames", json=snoop_names(ids))
    # Reincarnated is put back: Snoop Lion starts later than Bush, so Bush is no longer his
    await api.patch(f"/api/v1/albums/{ids['Reincarnated']}", json={"release_date": "2016-01-01"})

    album = (await api.get(f"/api/v1/albums/{ids['Bush']}")).json()
    assert album["artists"][0]["base_name"] == "SNOOP DOGG"
    after = (await api.get(f"/api/v1/albums/{ids['Reincarnated']}")).json()
    assert after["artists"][0]["base_name"] == "Snoop Lion"  # 2016: after both Snoop Dogg periods


async def test_releases_of_the_artist_are_found_for_the_picker(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    found = (await api.get(f"/api/v1/artists/{ids['artist']}/releases?q=bush")).json()

    assert [(r["kind"], r["name"]) for r in found] == [("album", "Bush"), ("song", "Bush song")]
    everything = (await api.get(f"/api/v1/artists/{ids['artist']}/releases?limit=3")).json()
    assert [r["release_date"] for r in everything] == ["2015-05-12", "2015-05-12", "2013-04-23"]


async def test_a_release_that_does_not_exist_is_refused_and_a_change_is_in_the_history(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    refused = await api.put(
        f"/api/v1/artists/{ids['artist']}/nicknames",
        json=[{"kind": "main", "name": "X", "periods": [{"start_album_id": 999999}]}],
    )
    assert refused.status_code == 422
    assert (await api.get(f"/api/v1/artists/{ids['artist']}")).json()["nicknames"] == []

    await api.put(
        f"/api/v1/artists/{ids['artist']}/nicknames", json=[{"kind": "main", "name": "Y"}]
    )

    async with sessionmaker() as db:
        revisions = (
            await db.scalars(select(Revision).where(Revision.entity_type == "artist"))
        ).all()
    assert [list(r.changes) for r in revisions] == [["nicknames"]]


async def test_an_alias_taken_away_is_not_shown_and_the_import_does_not_bring_it_back(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        artist = await make_artist(db, "Thom")
        db.add_all(ArtistAlias(artist_id=artist.id, name=name) for name in ("Radio", "Head"))
        await db.commit()

    kept = await api.put(f"/api/v1/artists/{artist.id}/aliases", json=["Head"])

    assert kept.json() == ["Head"]
    assert (await api.get(f"/api/v1/artists/{artist.id}")).json()["aliases"] == ["Head"]
    await api.put(f"/api/v1/artists/{artist.id}/aliases", json=["Head", "Radio"])
    assert (await api.get(f"/api/v1/artists/{artist.id}")).json()["aliases"] == ["Head", "Radio"]


async def test_one_release_shows_the_main_name_as_artist_and_an_alter_ego_as_producer(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    album, song = ids["Reincarnated"], ids["Reincarnated song"]
    async with sessionmaker() as db:
        producer = CreditRole(name="Producer")
        db.add(producer)
        await db.flush()
        db.add(SongCredit(song_id=song, artist_id=ids["artist"], role_id=producer.id))
        await db.commit()
    names = snoop_names(ids)
    names.append(
        {
            "kind": "alter_ego",
            "name": "Snoop Beats",
            "uses": [{"album_id": album, "scope": "credit"}],
        }
    )
    saved = (await api.put(f"/api/v1/artists/{ids['artist']}/nicknames", json=names)).json()
    assert saved[-1]["uses"][0]["scope"] == "credit"  # the scope is kept and read back

    page = (await api.get(f"/api/v1/albums/{album}")).json()
    assert page["artists"][0]["base_name"] == "Snoop Lion"  # the line of artists: the main name
    tracks = (await api.get(f"/api/v1/albums/{album}/tracks")).json()
    assert tracks[0]["artists"][0]["base_name"] == "Snoop Lion"
    assert tracks[0]["producers"][0]["base_name"] == "Snoop Beats"  # the credits: the alter ego
