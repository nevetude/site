from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.names import artist_name
from music_backend.enums import NicknameKind, NicknameScope
from music_backend.models import Nickname, NicknamePeriod, NicknameSpelling, NicknameUse
from tests.factories import make_album, make_artist, make_song


async def name(session: AsyncSession, artist_id: int, **context: object) -> str:
    return str(await session.scalar(select(artist_name(artist_id, **context))))  # type: ignore[arg-type]


async def snoop(session: AsyncSession) -> int:
    """Snoop Doggy Dogg, then Snoop Dogg, then Snoop Lion, and Snoop Dogg again: one name with two periods."""
    artist = await make_artist(session, "Snoop Dogg")
    album = {
        year: await make_album(session, name, release_date=when)
        for year, name, when in [
            (1996, "Tha Doggfather", date(1996, 11, 12)),
            (2013, "Reincarnated", date(2013, 4, 23)),
            (2015, "Bush", date(2015, 5, 12)),
        ]
    }
    doggy = Nickname(artist_id=artist.id, kind=NicknameKind.MAIN, name="Snoop Doggy Dogg")
    dogg = Nickname(artist_id=artist.id, kind=NicknameKind.MAIN, name="Snoop Dogg")
    lion = Nickname(artist_id=artist.id, kind=NicknameKind.MAIN, name="Snoop Lion")
    session.add_all([doggy, dogg, lion])
    await session.flush()
    session.add_all(
        [
            NicknamePeriod(nickname_id=doggy.id),  # from the beginning
            NicknamePeriod(nickname_id=dogg.id, start_album_id=album[1996].id),
            NicknamePeriod(nickname_id=lion.id, start_album_id=album[2013].id),
            NicknamePeriod(nickname_id=dogg.id, start_album_id=album[2015].id),  # and back
        ]
    )
    await session.flush()
    return artist.id


async def test_the_main_name_follows_the_dates_and_a_name_can_come_back(
    session: AsyncSession,
) -> None:
    artist = await snoop(session)

    assert await name(session, artist, on=date(1993, 11, 23)) == "Snoop Doggy Dogg"
    assert (
        await name(session, artist, on=date(1996, 11, 12)) == "Snoop Dogg"
    )  # the day of the release counts
    assert await name(session, artist, on=date(2013, 4, 22)) == "Snoop Dogg"
    assert await name(session, artist, on=date(2013, 4, 23)) == "Snoop Lion"
    assert await name(session, artist, on=date(2015, 5, 12)) == "Snoop Dogg"
    # no date: the latest name
    assert await name(session, artist) == "Snoop Dogg"


async def test_a_release_without_a_date_gets_the_latest_name(session: AsyncSession) -> None:
    artist = await snoop(session)
    undated = await make_album(session, "Unreleased")

    # the date of the release is a column, and it is NULL
    assert (
        await session.scalar(
            select(artist_name(artist, on=undated.release_date, album_id=undated.id))
        )
        == "Snoop Dogg"
    )
    assert undated.release_date is None


async def test_before_the_first_start_the_first_name_is_taken(session: AsyncSession) -> None:
    artist = await make_artist(session, "From Genius")
    album = await make_album(session, "Start", release_date=date(2010, 1, 1))
    nick = Nickname(artist_id=artist.id, kind=NicknameKind.MAIN, name="First")
    session.add(nick)
    await session.flush()
    session.add(NicknamePeriod(nickname_id=nick.id, start_album_id=album.id))
    await session.flush()

    assert await name(session, artist.id, on=date(2005, 1, 1)) == "First"


async def test_an_artist_without_nicknames_keeps_the_name_of_genius(session: AsyncSession) -> None:
    artist = await make_artist(session, "Plain")

    assert await name(session, artist.id, on=date(2020, 1, 1)) == "Plain"


async def test_an_alter_ego_is_the_name_on_the_release_it_is_tied_to(session: AsyncSession) -> None:
    artist = await snoop(session)
    song = await make_song(session, "As Snoopzilla", release_date=date(2013, 4, 23))
    other = await make_song(session, "Plain song", release_date=date(2013, 4, 23))
    zilla = Nickname(artist_id=artist, kind=NicknameKind.ALTER_EGO, name="Snoopzilla")
    session.add(zilla)
    await session.flush()
    session.add(NicknameUse(nickname_id=zilla.id, song_id=song.id))
    await session.flush()

    assert await name(session, artist, on=date(2013, 4, 23), song_id=song.id) == "Snoopzilla"
    # another song of the same day has the main name of the day
    assert await name(session, artist, on=date(2013, 4, 23), song_id=other.id) == "Snoop Lion"


async def test_an_alter_ego_of_an_album_is_the_name_in_every_song_of_it(
    session: AsyncSession,
) -> None:
    artist = await make_artist(session, "Eminem")
    album = await make_album(session, "The Slim Shady LP", release_date=date(1999, 2, 23))
    shady = Nickname(artist_id=artist.id, kind=NicknameKind.ALTER_EGO, name="Slim Shady")
    session.add(shady)
    await session.flush()
    session.add(NicknameUse(nickname_id=shady.id, album_id=album.id))
    await session.flush()

    assert await name(session, artist.id, on=date(1999, 2, 23), album_id=album.id) == "Slim Shady"
    # the same artist on another album is not the alter ego
    assert await name(session, artist.id, on=date(2000, 1, 1)) == "Eminem"


async def test_a_spelling_chosen_for_a_release_is_written_instead_of_the_name(
    session: AsyncSession,
) -> None:
    artist = await make_artist(session, "Bladee")
    loud = await make_album(session, "Loud cover", release_date=date(2016, 1, 1))
    quiet = await make_album(session, "Quiet cover", release_date=date(2017, 1, 1))
    nick = Nickname(artist_id=artist.id, kind=NicknameKind.MAIN, name="Bladee")
    session.add(nick)
    await session.flush()
    spelling = NicknameSpelling(nickname_id=nick.id, text="BLADEE")
    session.add_all([NicknamePeriod(nickname_id=nick.id), spelling])
    await session.flush()
    session.add(NicknameUse(nickname_id=nick.id, album_id=loud.id, spelling_id=spelling.id))
    await session.flush()

    assert await name(session, artist.id, on=date(2016, 1, 1), album_id=loud.id) == "BLADEE"
    assert await name(session, artist.id, on=date(2017, 1, 1), album_id=quiet.id) == "Bladee"


async def test_one_release_can_show_the_main_name_as_artist_and_an_alter_ego_as_producer(
    session: AsyncSession,
) -> None:
    artist = await make_artist(session, "Metro")
    album = await make_album(session, "Heroes", release_date=date(2016, 9, 16))
    ego = Nickname(artist_id=artist.id, kind=NicknameKind.ALTER_EGO, name="Metro Beats")
    session.add_all([ego, Nickname(artist_id=artist.id, kind=NicknameKind.MAIN, name="Metro")])
    await session.flush()
    session.add(NicknameUse(nickname_id=ego.id, album_id=album.id, scope=NicknameScope.CREDIT))
    await session.flush()

    day = date(2016, 9, 16)
    credit = NicknameScope.CREDIT
    assert (
        await name(session, artist.id, on=day, album_id=album.id) == "Metro"
    )  # the line of artists
    assert await name(session, artist.id, on=day, album_id=album.id, scope=credit) == "Metro Beats"


async def test_an_alter_ego_for_the_artist_line_only_leaves_the_credits_the_main_name(
    session: AsyncSession,
) -> None:
    artist = await make_artist(session, "Eminem")
    album = await make_album(session, "The Slim Shady LP", release_date=date(1999, 2, 23))
    shady = Nickname(artist_id=artist.id, kind=NicknameKind.ALTER_EGO, name="Slim Shady")
    session.add(shady)
    await session.flush()
    session.add(NicknameUse(nickname_id=shady.id, album_id=album.id, scope=NicknameScope.ARTIST))
    await session.flush()

    day = date(1999, 2, 23)
    assert await name(session, artist.id, on=day, album_id=album.id) == "Slim Shady"
    credit = NicknameScope.CREDIT
    assert await name(session, artist.id, on=day, album_id=album.id, scope=credit) == "Eminem"
