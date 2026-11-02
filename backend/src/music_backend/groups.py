"""Groups of artists kept as files outside of the database: `<genius id>.json` with the name of the group and the
people in it. The list is what the user made of it (the members Genius knows, the ones removed, the ones added by
hand through the search), so it is the source of truth for importing the group again."""

import json
from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel

from music_backend.enums import DatePrecision

if TYPE_CHECKING:
    from pathlib import Path


class GroupMember(BaseModel):
    genius_id: int
    name: str
    # The time in the group: a year ("2012"), a month ("2012-05") or a day ("2012-05-03"). No start is unknown, no end
    # is "now"; `has_left` with no end is a member who left at a time nobody knows.
    start: str | None = None
    end: str | None = None
    has_left: bool = False


class Group(BaseModel):
    genius_id: int
    name: str
    members: list[GroupMember]
    # Import the discography of every member (the artist and all their albums), not only the artist.
    discographies: bool = False


def load_group(directory: Path, genius_id: int) -> Group | None:
    path = directory / f"{genius_id}.json"
    return Group.model_validate_json(path.read_text("utf-8")) if path.exists() else None


def save_group(directory: Path, group: Group) -> None:
    directory.mkdir(exist_ok=True)
    text = json.dumps(group.model_dump(), ensure_ascii=False, indent=2)
    (directory / f"{group.genius_id}.json").write_text(text + "\n", "utf-8")


def merged(old: Group | None, new: Group) -> Group:
    """The group the user sends from the import form has no times (the form does not show them): the ones the file has
    are kept for the members that are still in it."""
    known = {m.genius_id: m for m in old.members} if old else {}
    return new.model_copy(
        update={
            "members": [
                m
                if m.start or m.end or m.has_left or m.genius_id not in known
                else m.model_copy(
                    update={
                        "start": known[m.genius_id].start,
                        "end": known[m.genius_id].end,
                        "has_left": known[m.genius_id].has_left,
                    }
                )
                for m in new.members
            ]
        }
    )


def list_groups(directory: Path) -> list[Group]:
    groups = [Group.model_validate_json(p.read_text("utf-8")) for p in directory.glob("*.json")]
    return sorted(groups, key=lambda group: group.name.lower())


def parse_partial_date(text: str) -> tuple[date, DatePrecision]:
    """ "2012" is 1 January 2012 known to the year, like Genius pads its dates."""
    parts = [int(part) for part in text.split("-")]
    precision = (DatePrecision.YEAR, DatePrecision.MONTH, DatePrecision.DAY)[len(parts) - 1]
    return date(
        parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1
    ), precision


def format_partial_date(day: date, precision: DatePrecision | None) -> str:
    match precision:
        case DatePrecision.YEAR:
            return f"{day.year}"
        case DatePrecision.MONTH:
            return f"{day.year}-{day.month:02d}"
        case _:
            return day.isoformat()
