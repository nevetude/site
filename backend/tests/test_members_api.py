import json
from datetime import date
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import DatePrecision, ImportKind
from music_backend.groups import Group, GroupMember, merged
from music_backend.imports.common import Task
from music_backend.imports.group_file import apply_group
from music_backend.models import ArtistMember, ArtistMemberView
from tests.factories import make_album, make_artist
from tests.fakes import FakeGenius, artist_payload, import_all, person

type SessionMaker = async_sessionmaker[AsyncSession]


async def arrange(sessionmaker: SessionMaker) -> dict[str, int]:
    """A group that Genius says has Ann and Bob; Cat is an artist of the library that Genius does not put in it."""
    ids: dict[str, int] = {}
    async with sessionmaker() as db:
        group = await make_artist(db, "TeamSESH", genius_id=1, artist_type="group")
        for name, genius_id in (("Ann", 2), ("Bob", 3), ("Cat", 4)):
            ids[name] = (await make_artist(db, name, genius_id=genius_id)).id
        ids["group"] = group.id
        ids["album"] = (await make_album(db, "Joined on", release_date=date(2013, 5, 1))).id
        db.add_all(
            ArtistMember(group_id=group.id, member_id=ids[n], position=i)
            for i, n in enumerate(("Ann", "Bob"), start=1)
        )
        await db.commit()
    return ids


async def test_the_group_is_as_the_list_says_with_the_time_of_each(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    saved = await api.put(
        f"/api/v1/artists/{ids['group']}/members",
        json=[
            {  # Cat first: not on Genius, joined with a release, still in
                "member_id": ids["Cat"],
                "start": {"album_id": ids["album"]},
            },
            {  # Bob: 2012 to 2014, by years
                "member_id": ids["Bob"],
                "start": {"date": "2012-01-01", "precision": "year"},
                "end": {"date": "2014-01-01", "precision": "year"},
            },
            {"member_id": ids["Ann"], "has_left": True},  # left, nobody knows when
        ],
    )

    assert saved.status_code == 200
    members = saved.json()
    assert [m["artist"]["base_name"] for m in members] == ["Cat", "Bob", "Ann"]
    cat, bob, ann = members
    assert (cat["starts_on"], cat["ends_on"], cat["has_left"]) == ("2013-05-01", None, False)
    assert cat["start"]["name"] == "Joined on"  # the date follows the release
    assert (bob["starts_on"], bob["starts_precision"], bob["ends_on"]) == (
        "2012-01-01",
        "year",
        "2014-01-01",
    )
    assert (ann["starts_on"], ann["ends_on"], ann["has_left"]) == (None, None, True)
    # the page of the group has the same, and the page of a member shows the group with his time in it
    page = (await api.get(f"/api/v1/artists/{ids['group']}")).json()
    assert [m["artist"]["base_name"] for m in page["members"]] == ["Cat", "Bob", "Ann"]
    of_bob = (await api.get(f"/api/v1/artists/{ids['Bob']}")).json()
    assert [(g["artist"]["base_name"], g["starts_on"]) for g in of_bob["groups"]] == [
        ("TeamSESH", "2012-01-01")
    ]


async def test_a_member_taken_out_is_hidden_and_the_import_does_not_bring_him_back(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(
        f"/api/v1/artists/{ids['group']}/members", json=[{"member_id": ids["Ann"]}]
    )  # Bob is out

    page = (await api.get(f"/api/v1/artists/{ids['group']}")).json()
    assert [m["artist"]["base_name"] for m in page["members"]] == ["Ann"]
    # the row of Genius is still there
    async with sessionmaker() as db:
        rows = (
            await db.scalars(
                select(ArtistMember.member_id).where(ArtistMember.group_id == ids["group"])
            )
        ).all()
    assert sorted(rows) == sorted([ids["Ann"], ids["Bob"]])

    # Genius still says Ann and Bob; the import goes over the group again
    fake = FakeGenius(
        artists={1: artist_payload(1, "TeamSESH", members=(person(2, "Ann"), person(3, "Bob")))}
    )
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 1))

    page = (await api.get(f"/api/v1/artists/{ids['group']}")).json()
    assert [m["artist"]["base_name"] for m in page["members"]] == ["Ann"]
    # and he can be put back
    await api.put(
        f"/api/v1/artists/{ids['group']}/members",
        json=[{"member_id": ids["Ann"]}, {"member_id": ids["Bob"]}],
    )
    page = (await api.get(f"/api/v1/artists/{ids['group']}")).json()
    assert [m["artist"]["base_name"] for m in page["members"]] == ["Ann", "Bob"]


async def test_the_start_follows_the_release_when_its_date_is_changed(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(
        f"/api/v1/artists/{ids['group']}/members",
        json=[{"member_id": ids["Cat"], "start": {"album_id": ids["album"]}}],
    )

    await api.patch(f"/api/v1/albums/{ids['album']}", json={"release_date": "2014-02-02"})

    page = (await api.get(f"/api/v1/artists/{ids['group']}")).json()
    assert page["members"][0]["starts_on"] == "2014-02-02"


async def test_an_artist_that_is_not_known_is_refused(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    refused = await api.put(f"/api/v1/artists/{ids['group']}/members", json=[{"member_id": 999999}])

    assert refused.status_code == 422
    page = (await api.get(f"/api/v1/artists/{ids['group']}")).json()
    assert [m["artist"]["base_name"] for m in page["members"]] == ["Ann", "Bob"]


async def test_artists_of_the_library_are_found_by_any_of_their_names(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    await api.put(
        f"/api/v1/artists/{ids['Cat']}/nicknames",
        json=[{"kind": "main", "name": "Cat Soup", "spellings": ["CAT SOUP"]}],
    )

    by_nickname = (await api.get("/api/v1/artists/search?q=soup")).json()
    by_name = (await api.get("/api/v1/artists/search?q=ann")).json()

    assert [a["base_name"] for a in by_nickname] == ["Cat Soup"]
    assert [a["base_name"] for a in by_name] == ["Ann"]


async def test_the_file_of_the_group_follows_the_page(
    api: AsyncClient, sessionmaker: SessionMaker, tmp_path: Path
) -> None:
    ids = await arrange(sessionmaker)

    await api.put(
        f"/api/v1/artists/{ids['group']}/members",
        json=[
            {
                "member_id": ids["Bob"],
                "start": {"date": "2012-01-01", "precision": "year"},
                "end": {"date": "2014-01-01", "precision": "year"},
            },
            {"member_id": ids["Cat"], "start": {"album_id": ids["album"]}, "has_left": True},
        ],
    )

    saved = json.loads((tmp_path / "groups" / "1.json").read_text("utf-8"))
    assert saved["name"] == "TeamSESH"
    assert saved["members"] == [
        {"genius_id": 3, "name": "Bob", "start": "2012", "end": "2014", "has_left": False},
        {"genius_id": 4, "name": "Cat", "start": "2013-05-01", "end": None, "has_left": True},
    ]


async def test_a_file_puts_the_group_in_the_database_with_the_time_of_each(
    session: AsyncSession,
) -> None:
    group = await make_artist(session, "TeamSESH", genius_id=1)
    ann, bob, cat = [
        await make_artist(session, n, genius_id=g) for n, g in (("Ann", 2), ("Bob", 3), ("Cat", 4))
    ]
    session.add(ArtistMember(group_id=group.id, member_id=bob.id, position=1))  # Genius lists Bob
    await session.flush()
    file = Group(
        genius_id=1,
        name="TeamSESH",
        members=[
            GroupMember(genius_id=2, name="Ann", start="2012", end="2014"),
            GroupMember(genius_id=4, name="Cat", start="2013-05", has_left=True),
            GroupMember(genius_id=99, name="Not imported"),  # no such artist: left out
        ],
    )

    await apply_group(session, file)

    rows = (
        await session.scalars(
            select(ArtistMemberView)
            .where(ArtistMemberView.group_id == group.id)
            .order_by(ArtistMemberView.position)
        )
    ).all()
    assert [
        (r.member_id, r.starts_on, r.starts_precision, r.ends_on, r.has_left) for r in rows
    ] == [
        (ann.id, date(2012, 1, 1), DatePrecision.YEAR, date(2014, 1, 1), False),
        (cat.id, date(2013, 5, 1), DatePrecision.MONTH, None, True),
    ]  # Bob is not in the file: he is hidden


def test_the_times_of_a_member_are_kept_when_the_import_form_sends_the_group_again() -> None:
    old = Group(
        genius_id=1,
        name="G",
        members=[GroupMember(genius_id=2, name="Ann", start="2012", end="2014", has_left=True)],
    )
    sent = Group(
        genius_id=1,
        name="G",
        members=[GroupMember(genius_id=2, name="Ann"), GroupMember(genius_id=3, name="New")],
    )

    kept = merged(old, sent)

    assert [(m.name, m.start, m.end, m.has_left) for m in kept.members] == [
        ("Ann", "2012", "2014", True),
        ("New", None, None, False),
    ]
    assert merged(None, sent) == sent
