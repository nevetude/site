import httpx
import pytest
import respx

from music_backend.imports.client import GeniusClient, GeniusError, RequestLog

PUBLIC = "https://genius.com/api"
OFFICIAL = "https://api.genius.com"


def client(*, token: bool = True) -> GeniusClient:
    return GeniusClient(
        PUBLIC,
        0,
        official_url=OFFICIAL if token else None,
        user_token="secret" if token else None,
    )


async def test_a_403_that_the_token_cured_is_not_in_the_log(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{PUBLIC}/songs/1").respond(403)
    respx_mock.get(f"{OFFICIAL}/songs/1").respond(json={"response": {"song": {"id": 1}}})
    written: list[RequestLog] = []

    async def record(entry: RequestLog) -> None:
        written.append(entry)

    genius = client()
    with pytest.raises(GeniusError) as refused:
        await genius.get("/songs/1", None, record, hold_403=True)
    answer = await genius.get("/songs/1", None, record, official=True)

    assert answer == {"song": {"id": 1}}
    assert [entry.status_code for entry in written] == [
        200
    ]  # the 403 was held back, for the caller to keep or drop
    held = refused.value.held
    assert held is not None
    assert held.status_code == 403
    assert respx_mock.calls.last.request.headers["authorization"] == "Bearer secret"
    assert (
        "authorization" not in respx_mock.calls[0].request.headers
    )  # the token goes to the official host only
    await genius.aclose()


async def test_without_a_token_the_403_is_logged_at_once(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{PUBLIC}/songs/1").mock(return_value=httpx.Response(403))
    written: list[RequestLog] = []

    async def record(entry: RequestLog) -> None:
        written.append(entry)

    genius = client(token=False)
    with pytest.raises(GeniusError):
        await genius.get("/songs/1", None, record, hold_403=True)

    assert [entry.status_code for entry in written] == [403]
    await genius.aclose()
