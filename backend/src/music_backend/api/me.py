from fastapi import APIRouter
from pydantic import BaseModel

from music_backend.api.deps import UserDep
from music_backend.enums import UserRole

router = APIRouter(prefix="/api/v1", tags=["me"])


class MeOut(BaseModel):
    id: int
    login: str
    role: UserRole
    can_edit: bool  # the site shows the pencil; the server decides on every write anyway (`require_editor`)


@router.get("/me")
async def get_me(user: UserDep) -> MeOut:
    return MeOut(
        id=user.id,
        login=user.login,
        role=user.role,
        can_edit=user.role in (UserRole.EDITOR, UserRole.ADMIN),
    )
