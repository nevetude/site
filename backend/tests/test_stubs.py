"""A stub is an entity Genius only mentioned in a list: what the list did not say must stay NULL."""

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ImportKind, ImportState
from music_backend.imports.common import Follow, Task
from music_backend.models import Album, AlbumArtist, AlbumTrack, Artist, Song
from music_backend.models.base import GeniusEntity
from tests.fakes import (
    UPDATED,
    FakeGenius,
    album_payload,
    artist_payload,
    import_all,
    person,
    related_album,
    song_album,
    song_payload,
    track,
)

type SessionMaker = async_sessionmaker[AsyncSession]

# What a list entry carries, per model. artist_type is also set when somebody lists the stub as a group.
KNOWN_FROM_A_LIST: dict[type[GeniusEntity], set[str]] = {
    Artist: {
        "name",
        "base_name",
        "cover_url",
        "artist_type",
        "genius_url",
        "is_verified",
        "is_meme_verified",
    },
    # a song lists its albums with the date, the cover and the artists
    Album: {
        "name",
        "base_name",
        "cover_url",
        "cover_thumbnail_url",
        "genius_url",
        "release_date",
        "release_date_precision",
        "is_released",
        "genius_updated_at",
    },
    Song: {"name", "base_name", "genius_updated_at"},
}
ALWAYS_SET = {"id", "genius_id", "import_state", "created_at", "updated_at"}


async def test_a_stub_knows_only_what_the_list_said(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(
        artists={
            # imported without following: its member and its group stay stubs (the artist of the album and of its song is
            # another one, because an artist that an album or a song brings walks over its groups)
            1: artist_payload(1, members=(person(2),), groups=(person(3),)),
        },
        albums={
            100: album_payload(
                100,
                primary_artists=[person(60)],
                performance_groups=[{"label": "Label", "artists": [person(10)]}],
                album_relationships=[
                    {"relationship_type": "deluxe_edition_of", "albums": [related_album(200)]}
                ],
            )
        },
        tracks={100: [track(500), track(501, disc=None, number=None)]},
        songs={
            500: song_payload(
                500,
                primary_artists=[person(60)],
                featured_artists=[person(5)],
                album=song_album(300),
                albums=[song_album(300)],
                song_relationships=[
                    {
                        "relationship_type": "samples",
                        "songs": [{"id": 700, "title": "Sampled", "updated_at": UPDATED}],
                    }
                ],
            ),
            501: song_payload(501, primary_artists=[person(60)]),
        },
    )
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100, follow=Follow.NONE))
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 1, follow=Follow.NONE))

    async with sessionmaker() as db:
        for model, known in KNOWN_FROM_A_LIST.items():
            columns = list(inspect(model, raiseerr=True).local_table.columns)
            rows = (
                await db.execute(select(*columns).where(model.import_state == ImportState.STUB))
            ).all()
            assert rows, f"no {model.__name__} stubs: the test would prove nothing"
            for row in rows:
                filled = {name for name, value in row._mapping.items() if value is not None}
                assert filled <= known | ALWAYS_SET, (model.__name__, row._mapping)

        # a stub nobody called a group has no type; one listed as a group is known to be one
        type_rows = await db.execute(select(Artist.genius_id, Artist.artist_type))
        types = dict(type_rows.all())
        assert (types[2], types[3]) == (None, "group")

        # the album import knows the numbers but not the primary album; the song import the reverse
        placements = {
            (album, song): (disc, position, sort_order, is_primary)
            for album, song, disc, position, sort_order, is_primary in await db.execute(
                select(
                    Album.genius_id,
                    Song.genius_id,
                    AlbumTrack.disc_number,
                    AlbumTrack.position,
                    AlbumTrack.sort_order,
                    AlbumTrack.is_primary,
                )
                .join(AlbumTrack, AlbumTrack.album_id == Album.id)
                .join(Song, Song.id == AlbumTrack.song_id)
            )
        }
    assert placements == {
        (100, 500): (1, 1, 1, None),
        (100, 501): (None, None, 2, None),
        (300, 500): (None, None, None, True),
    }


async def test_a_song_tells_the_date_the_cover_and_the_artists_of_its_album_stubs(
    sessionmaker: SessionMaker,
) -> None:
    out_soon = song_album(301, "Next One*", 2026, person(61, "Ann"))
    fake = FakeGenius(
        songs={500: song_payload(500, album=song_album(300), albums=[song_album(300), out_soon])}
    )
    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 500, follow=Follow.NONE))

    async with sessionmaker() as db:
        albums = {a.genius_id: a for a in await db.scalars(select(Album))}
        artists = (
            await db.execute(
                select(Album.genius_id, Artist.genius_id, Artist.genius_url)
                .join(AlbumArtist, AlbumArtist.album_id == Album.id)
                .join(Artist, Artist.id == AlbumArtist.artist_id)
            )
        ).all()
    assert (albums[300].release_date.year, albums[300].is_released) == (2014, True)  # type: ignore[union-attr]
    assert albums[300].cover_thumbnail_url == "https://img/rel-thumb.jpg"
    assert albums[301].is_released is False  # the asterisk of a title that is not out yet
    assert (301, 61, "https://genius.com/artists/61") in artists
