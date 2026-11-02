from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.api.queries import raw_of
from music_backend.enums import ArtistType, ImportKind, ImportState
from music_backend.imports.artist import handle_discography
from music_backend.imports.common import Context, Follow, Task
from music_backend.imports.runner import NodeState, Progress, run_tasks
from music_backend.models import Artist, ArtistAlias, ArtistMember, GeniusResponse, Revision
from tests.fakes import FakeGenius, artist_payload, description, import_all, person

type SessionMaker = async_sessionmaker[AsyncSession]


async def artist_by_genius_id(sm: SessionMaker, genius_id: int) -> Artist:
    async with sm() as db:
        return await db.get_one(
            Artist, await db.scalar(select(Artist.id).where(Artist.genius_id == genius_id))
        )


async def test_artist_fields_aliases_and_name_parts(sessionmaker: SessionMaker) -> None:
    payload = artist_payload(
        38515,
        "tora (RUS)",
        name_components={"base_name": "tora", "disambiguator": "RUS"},
        alternate_names=["AFX", "AFX", "Polygon Window"],
        is_verified=True,
        image_url="https://img/a.jpg",
    )

    await import_all(
        sessionmaker, FakeGenius(artists={38515: payload}), Task(ImportKind.ARTIST, 38515)
    )

    artist = await artist_by_genius_id(sessionmaker, 38515)
    assert (artist.name, artist.base_name, artist.disambiguator) == ("tora (RUS)", "tora", "RUS")
    assert (artist.artist_type, artist.import_state) == (ArtistType.PERSON, ImportState.FULL)
    assert (artist.description, artist.genius_url, artist.cover_url) == (
        "A bio",
        "https://genius.com/artists/38515",
        "https://img/a.jpg",
    )
    assert (artist.is_verified, artist.followers_count) == (True, 289)
    async with sessionmaker() as db:
        aliases = await db.scalars(
            select(ArtistAlias.name).where(ArtistAlias.artist_id == artist.id)
        )
        assert sorted(aliases) == ["AFX", "Polygon Window"]  # duplicates in the source collapse


@pytest.mark.parametrize(
    ("text", "stored"), [("", None), ("?", None), ("A real bio", "A real bio")]
)
async def test_placeholder_descriptions_are_stored_as_empty(
    sessionmaker: SessionMaker, text: str, stored: str | None
) -> None:
    payload = artist_payload(21, description=description(text))

    await import_all(sessionmaker, FakeGenius(artists={21: payload}), Task(ImportKind.ARTIST, 21))

    assert (await artist_by_genius_id(sessionmaker, 21)).description == stored


async def test_the_real_name_is_read_from_the_start_of_the_description(
    sessionmaker: SessionMaker,
) -> None:
    text = "Richard Roe (born June 17, 1987) is a rapper."
    payload = artist_payload(22, description=description(text))

    await import_all(sessionmaker, FakeGenius(artists={22: payload}), Task(ImportKind.ARTIST, 22))

    assert (await artist_by_genius_id(sessionmaker, 22)).real_name == "Richard Roe"


async def test_a_group_brings_its_members_and_their_other_groups_stay_stubs(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(
        artists={
            21: artist_payload(
                21, "Wu-Tang Clan", members=(person(101, "RZA"), person(102, "GZA"))
            ),
            101: artist_payload(101, "RZA", groups=(person(900, "Extra Group"),)),
            900: artist_payload(
                900,
                "Extra Group",
                members=(person(101), person(901, "Other Member")),
            ),
            901: artist_payload(901, "Other Member", groups=(person(902, "Far Group"),)),
            902: artist_payload(902, "Far Group", members=(person(901), person(903, "Farther"))),
            903: artist_payload(903, "Farther"),
            102: artist_payload(102, "GZA", groups=(person(21, "Wu-Tang Clan"),)),
            500: artist_payload(500, "Kendrick Lamar", groups=(person(21),)),
        },
    )

    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 21))

    async with sessionmaker() as db:
        states = {
            a.genius_id: (a.import_state, a.artist_type) for a in await db.scalars(select(Artist))
        }
        links = set((await db.execute(select(ArtistMember.group_id, ArtistMember.member_id))).all())
        ids = {a.genius_id: a.id for a in await db.scalars(select(Artist))}
    assert states[21] == (ImportState.FULL, ArtistType.GROUP)
    assert states[101] == states[102] == (ImportState.FULL, ArtistType.PERSON)
    # The other group of a member is a stub, and nothing behind it is met.
    assert states[900] == (ImportState.STUB, ArtistType.GROUP)
    assert not {901, 902, 903} & set(states)
    assert (ids[900], ids[101]) in links
    assert (ids[21], ids[101]) in links
    # Nobody links back to Wu-Tang from outside the walk: Kendrick Lamar is not met (only the groups it lists are).
    assert 500 not in states
    # 102 lists 21 again: each artist is read once.
    assert sorted(fake.calls) == sorted(f"/artists/{i}" for i in (21, 101, 102))


async def test_the_tracker_shows_who_found_whom_and_what_was_found_again(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(
        artists={
            21: artist_payload(21, "Clan", members=(person(101, "RZA"), person(102, "GZA"))),
            101: artist_payload(101, "RZA", groups=(person(900, "Extra"), person(21, "Clan"))),
            102: artist_payload(102, "GZA"),
            900: artist_payload(900, "Extra", members=(person(101, "RZA"), person(104, "Hand"))),
            104: artist_payload(104, "Hand"),
        },
    )
    seen: list[Progress] = []

    async def on_progress(state: Progress) -> None:
        seen.append(state)

    # 104 is put on the job by hand (a saved group): Genius does not list it in the group
    await run_tasks(
        sessionmaker,
        Context(fake),  # type: ignore[arg-type]
        Task(ImportKind.ARTIST, 21, name="Clan"),
        on_progress,
        extra=[Task(ImportKind.ARTIST, 104, name="Hand")],
    )

    tree = seen[-1].tree
    # a member walks only down: its second group (900) is a stub and not in the tree
    assert [(n.genius_id, n.parent, n.state) for n in tree.values()] == [
        (21, None, NodeState.DONE),
        (101, 21, NodeState.DONE),
        (102, 21, NodeState.DONE),
        (104, 21, NodeState.DONE),  # put on the job by hand: a unit of the group
    ]


async def test_unfollowed_artist_leaves_its_members_as_stubs(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(artists={21: artist_payload(21, members=(person(101),))})

    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 21, follow=Follow.NONE))

    assert fake.calls == ["/artists/21"]
    assert (await artist_by_genius_id(sessionmaker, 101)).import_state == ImportState.STUB


async def test_a_stub_becomes_the_full_artist_in_the_same_row(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(artists={21: artist_payload(21, members=(person(101, "RZA"),))})
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 21, follow=Follow.NONE))
    stub = await artist_by_genius_id(sessionmaker, 101)

    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 101))

    full = await artist_by_genius_id(sessionmaker, 101)
    assert (full.id, full.import_state) == (stub.id, ImportState.FULL)


async def test_importing_unchanged_data_again_writes_nothing(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(
        artists={21: artist_payload(21, alternate_names=["AFX"], members=(person(101),))}
    )
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 21))
    before = await artist_by_genius_id(sessionmaker, 21)

    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 21))

    after = await artist_by_genius_id(sessionmaker, 21)
    assert after.updated_at == before.updated_at
    async with sessionmaker() as db:
        assert (
            len((await db.scalars(select(Revision).where(Revision.entity_id == after.id))).all())
            == 1
        )


async def test_a_real_change_updates_the_row_and_refreshes_the_raw_copy(
    sessionmaker: SessionMaker,
) -> None:
    await import_all(
        sessionmaker, FakeGenius(artists={21: artist_payload(21)}), Task(ImportKind.ARTIST, 21)
    )
    changed = artist_payload(21, followers_count=300, something_we_do_not_store=99)

    await import_all(sessionmaker, FakeGenius(artists={21: changed}), Task(ImportKind.ARTIST, 21))

    artist = await artist_by_genius_id(sessionmaker, 21)
    assert artist.followers_count == 300
    async with sessionmaker() as db:
        latest = await db.scalar(
            select(Revision).where(Revision.entity_id == artist.id).order_by(Revision.id.desc())
        )
        raw = await db.scalar(select(GeniusResponse.raw).where(raw_of("artist", artist.id)))
    assert latest is not None
    assert latest.changes == {"followers_count": [289, 300]}
    assert raw is not None
    assert raw["something_we_do_not_store"] == 99


async def test_a_change_only_in_unstored_data_updates_the_response_and_nothing_else(
    sessionmaker: SessionMaker,
) -> None:
    await import_all(
        sessionmaker, FakeGenius(artists={21: artist_payload(21)}), Task(ImportKind.ARTIST, 21)
    )
    before = await artist_by_genius_id(sessionmaker, 21)
    drifted = artist_payload(21, something_we_do_not_store=99)

    await import_all(sessionmaker, FakeGenius(artists={21: drifted}), Task(ImportKind.ARTIST, 21))

    artist = await artist_by_genius_id(sessionmaker, 21)
    assert artist.updated_at == before.updated_at  # the row and its history are left alone
    async with sessionmaker() as db:
        raw = await db.scalar(select(GeniusResponse.raw).where(raw_of("artist", artist.id)))
        history = len(
            (await db.scalars(select(Revision).where(Revision.entity_id == artist.id))).all()
        )
    assert raw is not None
    assert raw["something_we_do_not_store"] == 99  # but the stored response is the latest one
    assert history == 1  # only the first import


async def test_hand_made_aliases_survive_a_reimport(
    sessionmaker: SessionMaker,
) -> None:
    async with sessionmaker() as db:
        stub = Artist(
            genius_id=21,
            name="Old",
            base_name="Old",
            import_state=ImportState.STUB,
        )
        db.add(stub)
        await db.flush()
        db.add(ArtistAlias(artist_id=stub.id, name="typed by hand"))
        await db.commit()
    payload = artist_payload(21, "New name", alternate_names=["AFX"])

    await import_all(sessionmaker, FakeGenius(artists={21: payload}), Task(ImportKind.ARTIST, 21))

    artist = await artist_by_genius_id(sessionmaker, 21)
    assert (artist.name, artist.import_state) == ("New name", ImportState.FULL)
    async with sessionmaker() as db:
        aliases = await db.scalars(
            select(ArtistAlias.name).where(ArtistAlias.artist_id == artist.id)
        )
        assert sorted(aliases) == ["AFX", "typed by hand"]


async def test_member_of_makes_a_stub_a_group(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(
        artists={
            1: artist_payload(1, members=(person(2, "Maybe a group"),)),
            3: artist_payload(3, groups=(person(2, "Maybe a group"),)),
        }
    )
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 1, follow=Follow.NONE))
    assert (await artist_by_genius_id(sessionmaker, 2)).artist_type is None

    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 3, follow=Follow.NONE))

    stub = await artist_by_genius_id(sessionmaker, 2)
    assert (stub.import_state, stub.artist_type) == (ImportState.STUB, ArtistType.GROUP)


@pytest.mark.parametrize(
    ("limit", "expected_albums", "pages"),
    [(None, [50, 40, 30, 20, 10], 3), (3, [50, 40, 30], 2), (0, [], 0)],
)
async def test_discography_reads_the_artist_then_lists_the_newest_albums_up_to_the_limit(
    sessionmaker: SessionMaker, limit: int | None, expected_albums: list[int], pages: int
) -> None:
    fake = FakeGenius(discographies={604: [50, 40, 30, 20, 10]}, page_size=2)
    fake_client: Any = fake  # FakeGenius stands in for the real client

    async with sessionmaker() as db, db.begin():
        tasks = await handle_discography(
            Context(fake_client), db, Task(ImportKind.DISCOGRAPHY, 604, limit=limit)
        )

    # the artist has no members here, so the units are the albums only
    assert tasks == [Task(ImportKind.ALBUM, i) for i in expected_albums]
    assert fake.calls[0] == "/artists/604"  # first, so the job knows its name at once
    assert len(fake.calls) == 1 + pages
    assert (await artist_by_genius_id(sessionmaker, 604)).import_state == ImportState.FULL


async def test_a_person_brings_its_groups_with_their_members_one_step_up(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(
        artists={
            1: artist_payload(1, "Thom", groups=(person(10, "Atoms for Peace"),)),
            10: artist_payload(
                10,
                "Atoms for Peace",
                members=(person(1), person(2, "Flea"), person(3, "Nigel")),
            ),
            2: artist_payload(2, "Flea", groups=(person(20, "Red Hot"),)),
        }
    )

    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 1))

    async with sessionmaker() as db:
        states = {a.genius_id: a.import_state for a in await db.scalars(select(Artist))}
        members = await db.scalar(
            select(func.count())
            .select_from(ArtistMember)
            .join(Artist, Artist.id == ArtistMember.group_id)
            .where(Artist.genius_id == 10)
        )
    assert states == {
        1: ImportState.FULL,
        10: ImportState.FULL,
        2: ImportState.FULL,
        3: ImportState.FULL,
        20: ImportState.STUB,  # the other group of a member of the group: a stub
    }
    assert members == 3


async def test_a_group_among_the_members_brings_its_own_members(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(
        artists={
            1: artist_payload(1, "Collective", members=(person(50, "Duo"),)),
            50: artist_payload(50, "Duo", members=(person(51), person(52)), groups=(person(60),)),
        }
    )
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 1))

    async with sessionmaker() as db:
        states = {a.genius_id: a.import_state for a in await db.scalars(select(Artist))}
    full = ImportState.FULL
    assert states == {1: full, 50: full, 51: full, 52: full, 60: ImportState.STUB}
