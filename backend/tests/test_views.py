from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.enums import DatePrecision
from music_backend.models import (
    AlbumEdit,
    AlbumTrackEdit,
    AlbumTrackView,
    AlbumView,
    ArtistEdit,
    ArtistMember,
    ArtistMemberEdit,
    ArtistMemberView,
    ArtistView,
    SongEdit,
    SongView,
)
from tests.factories import make_album, make_artist, make_song, place

PAIRS = [
    ("artist", "artist_view"),
    ("album", "album_view"),
    ("song", "song_view"),
    ("album_track", "album_track_view"),
    ("song_artist", "song_artist_view"),
    ("song_credit", "song_credit_view"),
    ("album_credit", "album_credit_view"),
    ("song_tag", "song_tag_view"),
]


async def columns(session: AsyncSession, name: str) -> set[str]:
    rows = await session.execute(
        text("select column_name from information_schema.columns where table_name = :n"),
        {"n": name},
    )
    return {row[0] for row in rows}


async def test_every_column_of_a_table_is_in_its_view(session: AsyncSession) -> None:
    """A column added to a table must also be added to its view, or the site would not see it."""
    for table, view in PAIRS:
        assert await columns(session, table) <= await columns(session, view), table


async def test_a_view_is_the_table_until_a_field_is_set_by_hand(session: AsyncSession) -> None:
    album = await make_album(
        session, "Genius title", variant="Deluxe", release_date=date(2012, 10, 22)
    )
    await session.flush()
    album_id = album.id  # read before `expire_all`: a lazy load is not allowed in async code

    plain = await session.scalar(select(AlbumView).where(AlbumView.id == album_id))
    assert (plain.base_name, plain.variant, plain.release_date) == (  # type: ignore[union-attr]
        "Genius title",
        "Deluxe",
        date(2012, 10, 22),
    )

    # the title is changed, the date is taken away (NULL is a value too), the variant is left alone
    session.add(
        AlbumEdit(album_id=album_id, overridden=["base_name", "release_date"], base_name="My title")
    )
    await session.flush()
    session.expire_all()
    edited = await session.scalar(select(AlbumView).where(AlbumView.id == album_id))
    assert (edited.base_name, edited.variant, edited.release_date) == (  # type: ignore[union-attr]
        "My title",
        "Deluxe",
        None,
    )

    # a value in the edit row that is not named in `overridden` does not count: this is how a field is reset
    row = await session.get(AlbumEdit, album_id)
    row.overridden = ["release_date"]  # type: ignore[union-attr]
    await session.flush()
    session.expire_all()
    reset = await session.scalar(select(AlbumView).where(AlbumView.id == album_id))
    assert (reset.base_name, reset.release_date) == ("Genius title", None)  # type: ignore[union-attr]


async def test_artist_and_song_views_overlay_their_own_fields(session: AsyncSession) -> None:
    artist = await make_artist(session, "Thom")
    song = await make_song(session, "Old name")
    session.add(ArtistEdit(artist_id=artist.id, overridden=["description"], description="by hand"))
    session.add(
        SongEdit(
            song_id=song.id,
            overridden=["base_name", "release_date", "release_date_precision"],
            base_name="New name",
            release_date=date(2020, 1, 1),
            release_date_precision=DatePrecision.YEAR,
        )
    )
    await session.flush()

    seen_artist = await session.scalar(select(ArtistView).where(ArtistView.id == artist.id))
    seen_song = await session.scalar(select(SongView).where(SongView.id == song.id))
    assert seen_artist.description == "by hand"  # type: ignore[union-attr]
    assert (seen_song.base_name, seen_song.release_date, seen_song.release_date_precision) == (  # type: ignore[union-attr]
        "New name",
        date(2020, 1, 1),
        DatePrecision.YEAR,
    )


async def test_members_hide_the_removed_and_take_their_time_from_a_release_or_a_date(
    session: AsyncSession,
) -> None:
    group = await make_artist(session, "Group")
    ann, bob, cat = [await make_artist(session, n) for n in ("Ann", "Bob", "Cat")]
    album = await make_album(session, "Joined on", release_date=date(2013, 5, 1))
    session.add_all(
        ArtistMember(group_id=group.id, member_id=m.id, position=i)
        for i, m in enumerate((ann, bob, cat))
    )
    session.add_all(
        [
            ArtistMemberEdit(group_id=group.id, member_id=bob.id, removed=True),
            ArtistMemberEdit(
                group_id=group.id, member_id=ann.id, position=9, start_album_id=album.id
            ),
            ArtistMemberEdit(
                group_id=group.id,
                member_id=cat.id,
                start_date=date(2012, 1, 1),
                start_precision=DatePrecision.YEAR,
                end_date=date(2014, 1, 1),
                end_precision=DatePrecision.YEAR,
            ),
        ]
    )
    await session.flush()

    rows = (
        await session.scalars(
            select(ArtistMemberView)
            .where(ArtistMemberView.group_id == group.id)
            .order_by(ArtistMemberView.position)
        )
    ).all()

    assert [r.member_id for r in rows] == [cat.id, ann.id]  # Bob is gone, Ann moved to the end
    assert [(r.starts_on, r.ends_on, r.has_left) for r in rows] == [
        (date(2012, 1, 1), date(2014, 1, 1), False),
        (date(2013, 5, 1), None, False),  # the date follows the release
    ]


async def test_tracks_hide_the_removed_and_take_the_order_of_the_user(
    session: AsyncSession,
) -> None:
    album = await make_album(session, "Album")
    first, second, third = [await make_song(session, n) for n in ("One", "Two", "Three")]
    tracks = [
        await place(session, album, song, position=i + 1)
        for i, song in enumerate((first, second, third))
    ]
    session.add_all(
        [
            AlbumTrackEdit(album_track_id=tracks[0].id, position=3),
            AlbumTrackEdit(album_track_id=tracks[1].id, removed=True),
            AlbumTrackEdit(album_track_id=tracks[2].id, position=1),
        ]
    )
    await session.flush()

    rows = (
        await session.scalars(
            select(AlbumTrackView)
            .where(AlbumTrackView.album_id == album.id)
            .order_by(AlbumTrackView.position)
        )
    ).all()

    assert [(r.song_id, r.position) for r in rows] == [(third.id, 1), (first.id, 3)]
