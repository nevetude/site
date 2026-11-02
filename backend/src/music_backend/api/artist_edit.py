"""Changing an artist by hand: the fields now, the names and the members in their own calls."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from music_backend.api.artist_page import ArtistDetail, get_artist
from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.queries import get_or_404
from music_backend.editing import override_fields
from music_backend.enums import ArtistType
from music_backend.models import ARTIST_FIELDS, ArtistEdit, ArtistView

router = APIRouter(prefix="/api/v1/artists", tags=["artist edit"])

type ArtistField = Literal["disambiguator", "artist_type", "description", "real_name", "cover_url"]


class ArtistPatch(BaseModel):
    """See `AlbumPatch`."""

    model_config = ConfigDict(extra="forbid")

    disambiguator: str | None = None
    artist_type: ArtistType | None = None
    description: str | None = None
    real_name: str | None = None
    cover_url: str | None = None
    reset: list[ArtistField] = Field(default_factory=list)


@router.patch("/{artist_id}")
async def patch_artist(
    artist_id: int, body: ArtistPatch, session: SessionDep, user: EditorDep
) -> ArtistDetail:
    await get_or_404(session, ArtistView, artist_id)
    await override_fields(
        session,
        entity_type="artist",
        entity_id=artist_id,
        user_id=user.id,
        view=ArtistView,
        edit=ArtistEdit,
        key="artist_id",
        fields=ARTIST_FIELDS,
        values=body.model_dump(exclude_unset=True, exclude={"reset"}),
        reset=body.reset,
    )
    return await get_artist(artist_id, session, user)
