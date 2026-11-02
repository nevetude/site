import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from music_backend.api.deps import EditorDep
from music_backend.groups import Group, list_groups, load_group
from music_backend.imports.artist import related_artists
from music_backend.imports.client import GeniusError

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


class PreviewMember(BaseModel):
    genius_id: int
    name: str
    image_url: str | None  # only for the people Genius lists; one added by hand has none
    source: Literal["genius", "saved"]  # `saved`: Genius does not list this person in the group
    start: str | None = (
        None  # the time in the group, from the file of the group (see `GroupMember`)
    )
    end: str | None = None
    has_left: bool = False


class GroupPreview(BaseModel):
    genius_id: int
    name: str
    members: list[PreviewMember]
    saved: bool  # there is a file of this group: it decides who is in the list
    discographies: bool  # from the file: import the discography of every member


@router.get("")
async def saved_groups(request: Request, _: EditorDep) -> list[Group]:
    return await asyncio.to_thread(list_groups, request.app.state.settings.groups_dir)


@router.get("/{genius_id}")
async def preview_group(genius_id: int, request: Request, _: EditorDep) -> GroupPreview:
    """Who an import of this artist would bring with it: the saved list when there is one, else the members that Genius
    knows. An artist with no members (and no file) is not a group: the list is empty."""
    try:
        raw = (await request.app.state.genius.get(f"/artists/{genius_id}"))["artist"]
    except GeniusError as error:
        raise HTTPException(502, str(error)) from error
    known = {
        member["id"]: PreviewMember(
            genius_id=member["id"],
            name=member["name"],
            image_url=member["image_url"],
            source="genius",
        )
        for member in related_artists(raw, "members")
    }
    group = await asyncio.to_thread(load_group, request.app.state.settings.groups_dir, genius_id)
    members = (
        [
            (
                known.get(m.genius_id)
                or PreviewMember(genius_id=m.genius_id, name=m.name, image_url=None, source="saved")
            ).model_copy(update={"start": m.start, "end": m.end, "has_left": m.has_left})
            for m in group.members
        ]
        if group
        else list(known.values())
    )
    return GroupPreview(
        genius_id=genius_id,
        name=raw["name"],
        members=members,
        saved=group is not None,
        discographies=group.discographies if group else False,
    )
