from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ImportKind, SongArtistRole
from music_backend.imports.common import Task
from music_backend.models import (
    AlbumCredit,
    CreditRole,
    Genre,
    SongArtist,
    SongCredit,
    SongTag,
    Tag,
)
from tests.factories import make_album, make_artist, make_song
from tests.fakes import FakeGenius, import_all, person, song_payload

type SessionMaker = async_sessionmaker[AsyncSession]


async def arrange(sessionmaker: SessionMaker) -> dict[str, int]:
    """A song sung by Ann and Bob with Cat as a guest, produced by Dan, tagged rap and trap."""
    ids: dict[str, int] = {}
    async with sessionmaker() as db:
        for name, genius_id in (("Ann", 1), ("Bob", 2), ("Cat", 3), ("Dan", 4), ("Eve", 5)):
            ids[name] = (await make_artist(db, name, genius_id=genius_id)).id
        song = await make_song(db, "Song", genius_id=500)
        album = await make_album(db, "Album", genius_id=100)
        ids["song"], ids["album"] = song.id, album.id
        producer = CreditRole(name="Producer")
        label = CreditRole(name="Label")
        db.add_all([producer, label])
        await db.flush()
        db.add_all(
            [
                SongArtist(
                    song_id=song.id, artist_id=ids["Ann"], role=SongArtistRole.PRIMARY, position=1
                ),
                SongArtist(
                    song_id=song.id, artist_id=ids["Bob"], role=SongArtistRole.PRIMARY, position=2
                ),
                SongArtist(
                    song_id=song.id, artist_id=ids["Cat"], role=SongArtistRole.FEATURED, position=1
                ),
                SongCredit(song_id=song.id, artist_id=ids["Dan"], role_id=producer.id),
                AlbumCredit(album_id=album.id, artist_id=ids["Eve"], role_id=label.id),
            ]
        )
        for name in ("rap", "trap"):
            tag = Tag(name=name, base_name=name)
            db.add(tag)
            await db.flush()
            db.add(SongTag(song_id=song.id, tag_id=tag.id))
        await db.commit()
    return ids


def names(artists: list[dict[str, object]]) -> list[object]:
    return [a["base_name"] for a in artists]


async def test_the_artists_of_a_song_are_what_the_lists_say(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    saved = await api.put(
        f"/api/v1/songs/{ids['song']}/artists",
        json={"artists": [ids["Bob"]], "featured": [ids["Ann"], ids["Eve"]]},
    )

    assert saved.status_code == 200
    page = saved.json()
    assert names(page["artists"]) == ["Bob"]
    assert names(page["featured"]) == ["Ann", "Eve"]  # Ann moved to the guests, Eve is new
    # the rows of Genius are still there (Cat is hidden, not deleted)
    async with sessionmaker() as db:
        rows = (await db.scalars(select(SongArtist).where(SongArtist.song_id == ids["song"]))).all()
    assert len(rows) == 5
    # the artist pages follow: Cat has no songs now
    cat = (await api.get(f"/api/v1/artists/{ids['Cat']}/songs")).json()
    assert cat["total"] == 0


async def test_the_import_does_not_bring_back_what_the_user_took_out(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(
        f"/api/v1/songs/{ids['song']}/artists", json={"artists": [ids["Ann"]], "featured": []}
    )

    fake = FakeGenius(
        songs={
            500: song_payload(
                500,
                primary_artists=[person(1, "Ann"), person(2, "Bob")],
                featured_artists=[person(3, "Cat")],
            )
        }
    )
    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 500))

    page = (await api.get(f"/api/v1/songs/{ids['song']}")).json()
    assert (names(page["artists"]), names(page["featured"])) == (["Ann"], [])


async def test_credits_of_a_song_and_of_an_album_are_replaced_by_role_and_artist(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    song = (
        await api.put(
            f"/api/v1/songs/{ids['song']}/credits",
            json=[
                {"role": "Writer", "artist_id": ids["Eve"]},  # a role that is new
                {"role": "Producer", "artist_id": ids["Dan"]},  # kept
                {"role": "Producer", "artist_id": ids["Bob"]},
            ],
        )
    ).json()

    assert [(c["role"], names(c["artists"])) for c in song["credits"]] == [
        ("Producer", ["Dan", "Bob"]),
        ("Writer", ["Eve"]),
    ]
    album = (
        await api.put(
            f"/api/v1/albums/{ids['album']}/credits",
            json=[{"role": "Label", "artist_id": ids["Dan"]}],  # Eve is replaced by Dan
        )
    ).json()
    label = next(g for g in album["credits"] if g["role"] == "Label")
    assert [a["artist"]["base_name"] for a in label["artists"]] == ["Dan"]
    # taking all away
    empty = (await api.put(f"/api/v1/songs/{ids['song']}/credits", json=[])).json()
    assert empty["credits"] == []
    async with sessionmaker() as db:
        # the credit of Genius is hidden, and the roles are in the dictionary
        assert len((await db.scalars(select(SongCredit))).all()) == 3
        assert {r.name for r in await db.scalars(select(CreditRole))} == {
            "Producer",
            "Label",
            "Writer",
        }
    roles = (await api.get("/api/v1/credit-roles")).json()
    assert [r["name"] for r in roles] == ["Label", "Producer", "Writer"]


async def test_the_tags_of_a_song_are_the_names_in_the_list(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    page = (await api.put(f"/api/v1/songs/{ids['song']}/tags", json=["trap", "drill"])).json()

    assert page["tags"] == ["drill", "trap"]  # rap is taken out, drill is a new tag
    found = (await api.get("/api/v1/tags?q=dri")).json()
    assert [t["name"] for t in found] == ["drill"]
    again = (await api.put(f"/api/v1/songs/{ids['song']}/tags", json=["rap"])).json()
    assert again["tags"] == ["rap"]  # a tag that was hidden is shown again


async def test_the_genre_is_picked_from_the_dictionary_or_made(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    made = (await api.post("/api/v1/genres", json={"name": "Phonk"})).json()
    again = (await api.post("/api/v1/genres", json={"name": "Phonk"})).json()
    assert made == again  # one genre for one name

    page = (await api.patch(f"/api/v1/songs/{ids['song']}", json={"genre_id": made["id"]})).json()

    assert page["genre"] == "Phonk"
    assert page["edited"] == ["genre_id"]
    async with sessionmaker() as db:
        assert [g.genius_id for g in await db.scalars(select(Genre))] == [None]
    assert [g["name"] for g in (await api.get("/api/v1/genres?q=pho")).json()] == ["Phonk"]
