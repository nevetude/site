"""The dictionaries a page picks from: genres, tags and the roles of credits. What a form needs is the list to pick
from, and a genre to be made when the one wanted is not there (tags and roles are made by the call that uses them)."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from music_backend.api.deps import EditorDep, SessionDep, UserDep
from music_backend.models import CreditRole, Genre, Tag

router = APIRouter(prefix="/api/v1", tags=["dictionaries"])


class Named(BaseModel):
    id: int
    name: str


class NewGenre(BaseModel):
    name: str


@router.get("/genres")
async def list_genres(
    session: SessionDep, _: UserDep, q: str = "", limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> list[Named]:
    rows = await session.execute(
        select(Genre.id, Genre.name)
        .where(Genre.name.ilike(f"%{q}%"))
        .order_by(func.lower(Genre.name))
        .limit(limit)
    )
    return [Named(id=pk, name=name) for pk, name in rows]


@router.post("/genres")
async def make_genre(body: NewGenre, session: SessionDep, _: EditorDep) -> Named:
    """The genre with this name; a new one when there is none (a genre made by hand has no Genius id)."""
    genre = await session.scalar(select(Genre).where(Genre.name == body.name).order_by(Genre.id))
    if genre is None:
        genre = Genre(name=body.name, base_name=body.name)
        session.add(genre)
        await session.commit()
    return Named(id=genre.id, name=genre.name)


@router.get("/tags")
async def list_tags(
    session: SessionDep, _: UserDep, q: str = "", limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> list[Named]:
    rows = await session.execute(
        select(Tag.id, Tag.name)
        .where(Tag.name.ilike(f"%{q}%"))
        .order_by(func.lower(Tag.name))
        .limit(limit)
    )
    return [Named(id=pk, name=name) for pk, name in rows]


@router.get("/credit-roles")
async def list_credit_roles(session: SessionDep, _: UserDep) -> list[Named]:
    rows = await session.execute(select(CreditRole.id, CreditRole.name).order_by(CreditRole.name))
    return [Named(id=pk, name=name) for pk, name in rows]
