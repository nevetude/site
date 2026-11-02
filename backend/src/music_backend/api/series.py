"""The series of releases of an artist: groups that the user makes of its albums ("Evil Wayz"). Genius does not know
them, so the import never touches them; an album may be in any number of series, and a series shows its albums in the
order of their dates."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.queries import album_cards, get_or_404, refuse_unknown
from music_backend.api.schemas import ArtistAlbum
from music_backend.editing import log_revision
from music_backend.models import AlbumView, ArtistView, ReleaseSeries, ReleaseSeriesAlbum

router = APIRouter(prefix="/api/v1/artists", tags=["series"])


class SeriesIn(BaseModel):
    name: str
    album_ids: list[int]


class SeriesOut(BaseModel):
    id: int
    name: str
    albums: list[ArtistAlbum]  # the oldest first; the ones with no date last


async def read_series(session: AsyncSession, artist_id: int) -> list[SeriesOut]:
    rows = (
        await session.execute(
            select(ReleaseSeries.id, ReleaseSeries.name, ReleaseSeriesAlbum.album_id)
            .select_from(ReleaseSeries)
            .outerjoin(ReleaseSeriesAlbum, ReleaseSeriesAlbum.series_id == ReleaseSeries.id)
            .outerjoin(AlbumView, AlbumView.id == ReleaseSeriesAlbum.album_id)
            .where(ReleaseSeries.artist_id == artist_id)
            .order_by(
                ReleaseSeries.position, AlbumView.release_date.asc().nulls_last(), AlbumView.id
            )
        )
    ).all()
    cards = await album_cards(session, [album_id for _, _, album_id in rows if album_id])
    series: dict[int, SeriesOut] = {}
    for series_id, name, album_id in rows:
        one = series.setdefault(series_id, SeriesOut(id=series_id, name=name, albums=[]))
        if album_id:
            one.albums.append(cards[album_id])
    return list(series.values())


@router.put("/{artist_id}/series")
async def put_series(
    artist_id: int, body: list[SeriesIn], session: SessionDep, user: EditorDep
) -> list[SeriesOut]:
    """Makes the series of the artist what the list says, in its order. An album that does not exist is a 422."""
    await get_or_404(session, ArtistView, artist_id)
    before = [[s.name, [a.id for a in s.albums]] for s in await read_series(session, artist_id)]
    mine = select(ReleaseSeries.id).where(ReleaseSeries.artist_id == artist_id)
    await session.execute(delete(ReleaseSeriesAlbum).where(ReleaseSeriesAlbum.series_id.in_(mine)))
    await session.execute(delete(ReleaseSeries).where(ReleaseSeries.artist_id == artist_id))
    async with refuse_unknown(session, "An album of a series is not known"):
        for position, item in enumerate(body, start=1):
            row = ReleaseSeries(artist_id=artist_id, name=item.name, position=position)
            session.add(row)
            await session.flush()
            session.add_all(
                ReleaseSeriesAlbum(series_id=row.id, album_id=album_id)
                for album_id in dict.fromkeys(item.album_ids)
            )
        await session.flush()
    series = await read_series(session, artist_id)
    after = [[s.name, [a.id for a in s.albums]] for s in series]
    await log_revision(
        session,
        "artist",
        artist_id,
        user.id,
        {"series": [before, after]} if before != after else {},
    )
    await session.commit()
    return series
