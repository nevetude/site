from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import respx
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.config import Settings
from music_backend.enums import ImportState
from music_backend.main import create_app
from music_backend.models import Artist
from tests.conftest import truncate_all_tables, wait_for_job
from tests.fakes import artist_payload, person

GENIUS = "https://genius.com/api"

type SessionMaker = async_sessionmaker[AsyncSession]


@pytest.fixture
async def client(migrated_url: URL, tmp_path: Path) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url=migrated_url.render_as_string(hide_password=False),
        genius_min_interval_s=0,
        genius_retry_backoff_s=0,
        groups_dir=tmp_path / "groups",  # not there yet: the first save makes it
    )
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
        await truncate_all_tables(migrated_url)


def artist(
    mock: respx.MockRouter, genius_id: int, name: str, **links: tuple[dict[str, Any], ...]
) -> None:
    mock.get(f"{GENIUS}/artists/{genius_id}").respond(
        json={"response": {"artist": artist_payload(genius_id, name, **links)}}
    )


def two_members(mock: respx.MockRouter) -> None:
    artist(mock, 10, "Band", members=(person(1, "Ann"), person(2, "Bob")))
    artist(mock, 1, "Ann")
    artist(mock, 2, "Bob")
    artist(mock, 3, "Cat")


async def test_preview_lists_the_members_genius_knows(
    client: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    two_members(respx_mock)

    got = (await client.get("/api/v1/groups/10")).json()

    assert (got["name"], got["saved"]) == ("Band", False)
    assert [(m["genius_id"], m["name"], m["source"]) for m in got["members"]] == [
        (1, "Ann", "genius"),
        (2, "Bob", "genius"),
    ]
    assert (await client.get("/api/v1/groups")).json() == []


async def test_an_artist_with_no_members_is_not_a_group(
    client: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    artist(respx_mock, 7, "Solo")

    assert (await client.get("/api/v1/groups/7")).json()["members"] == []


async def test_the_import_saves_the_list_and_the_list_decides_the_next_preview(
    client: AsyncClient, respx_mock: respx.MockRouter, sessionmaker: SessionMaker, tmp_path: Path
) -> None:
    two_members(respx_mock)
    # Bob is removed, Cat (not in the group on Genius) is added by hand
    group = {
        "name": "Band",
        "members": [{"genius_id": 1, "name": "Ann"}, {"genius_id": 3, "name": "Cat"}],
    }

    created = await client.post(
        "/api/v1/imports", json={"kind": "artist", "genius_id": 10, "group": group}
    )
    job = await wait_for_job(client, created.json()["id"])

    assert job["status"] == "succeeded"
    assert (tmp_path / "groups" / "10.json").exists()
    async with sessionmaker() as db:
        states = {a.genius_id: a.import_state for a in await db.scalars(select(Artist))}
    # Genius lists Bob, so he is imported with the group anyway (the walk follows every link); Cat comes from the list
    assert states[3] == ImportState.FULL
    assert states[1] == ImportState.FULL

    preview = (await client.get("/api/v1/groups/10")).json()
    assert preview["saved"] is True
    assert [(m["genius_id"], m["source"]) for m in preview["members"]] == [
        (1, "genius"),
        (3, "saved"),
    ]
    assert [g["name"] for g in (await client.get("/api/v1/groups")).json()] == ["Band"]


async def test_the_nesting_of_a_job_says_who_found_whom(
    client: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    two_members(respx_mock)
    group = {"name": "Band", "members": [{"genius_id": 3, "name": "Cat"}]}

    created = await client.post(
        "/api/v1/imports", json={"kind": "artist", "genius_id": 10, "group": group}
    )
    job = await wait_for_job(client, created.json()["id"])
    nesting = (await client.get(f"/api/v1/imports/{job['id']}/nesting")).json()

    assert [(n["genius_id"], n["parent_id"], n["state"]) for n in nesting] == [
        (10, None, "done"),
        (1, 10, "done"),
        (2, 10, "done"),
        (3, 10, "done"),
    ]
    assert (await client.get("/api/v1/imports/999/nesting")).json() == []


async def test_with_discographies_every_member_of_the_list_is_read_with_his_albums(
    client: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    two_members(respx_mock)
    albums = {
        i: respx_mock.get(f"{GENIUS}/artists/{i}/albums").respond(
            json={"response": {"albums": [], "next_page": None}}
        )
        for i in (1, 2, 3)
    }
    members = [{"genius_id": 1, "name": "Ann"}, {"genius_id": 3, "name": "Cat"}]
    group = {"name": "Band", "members": members, "discographies": True}

    created = await client.post(
        "/api/v1/imports", json={"kind": "artist", "genius_id": 10, "group": group}
    )
    job = await wait_for_job(client, created.json()["id"])

    assert job["status"] == "succeeded"
    # Ann and Cat are on the list: their albums are asked for. Bob is out of it, he came with the walk (Genius lists
    # him) as an artist only. Nobody is read twice.
    assert [albums[i].call_count for i in (1, 2, 3)] == [1, 0, 1]
    assert respx_mock.calls.call_count == len({str(c.request.url) for c in respx_mock.calls})
    assert (await client.get("/api/v1/groups/10")).json()["discographies"] is True
